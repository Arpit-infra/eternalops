"""Health check endpoint for EternalOps backend and connected services."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from app.schemas.common import HealthResponse, ServiceHealthItem
from app.schemas.incidents import IncidentStatus
from app.services.agent_service import AgentService, get_agent_service
from app.services.environment_service import EnvironmentService
from app.services.incident_service import IncidentService, get_incident_service
from app.services.kubernetes_service import KubernetesService, get_kubernetes_service
from app.services.prometheus_service import PrometheusService, get_prometheus_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="System Health Status")
async def get_health(
    prom_service: PrometheusService = Depends(get_prometheus_service),
    k8s_service: KubernetesService = Depends(get_kubernetes_service),
) -> HealthResponse:
    """
    Get overall health status of EternalOps backend and its infrastructure integrations.
    Returns 200 even if an integration is down, reflecting granular availability per subsystem.
    """
    prom_available, prom_err = await prom_service.check_health()
    k8s_status = k8s_service.get_status()
    k8s_available = bool(k8s_status.get("available", False))

    return HealthResponse(
        status="ok",
        service="eternalops-backend",
        prometheus=ServiceHealthItem(
            available=prom_available,
            details={"error": prom_err} if prom_err else None,
        ),
        kubernetes=ServiceHealthItem(
            available=k8s_available,
            details={"cluster_version": k8s_status.get("cluster_version"), "error": k8s_status.get("error")}
            if not k8s_available or k8s_status.get("cluster_version")
            else None,
        ),
    )


@router.get("/health/summary", summary="Cluster and Application Health Summary")
async def get_health_summary(
    prom_service: PrometheusService = Depends(get_prometheus_service),
    k8s_service: KubernetesService = Depends(get_kubernetes_service),
    incidents: IncidentService = Depends(get_incident_service),
    agent_svc: AgentService = Depends(get_agent_service),
) -> Dict[str, Any]:
    """
    Real-time health summary synthesizing K8s, Prometheus, Incidents, and Agent status.
    Answers: What is healthy, unhealthy, recovering, auto-recovered, or escalated.
    """
    prom_available, _ = await prom_service.check_health()
    k8s_status = k8s_service.get_status()
    k8s_available = bool(k8s_status.get("available", False))

    inc_list = incidents.list_incidents(limit=200)
    active_incs = [i for i in inc_list.incidents if i.status in (IncidentStatus.OPEN, IncidentStatus.ANALYZING, IncidentStatus.HEALING, IncidentStatus.VERIFYING)]
    recovering_incs = [i for i in active_incs if i.status in (IncidentStatus.HEALING, IncidentStatus.VERIFYING)]
    escalated_incs = [i for i in inc_list.incidents if i.status in (IncidentStatus.ESCALATED, IncidentStatus.FAILED)]
    resolved_incs = [i for i in inc_list.incidents if i.status == IncidentStatus.RESOLVED]

    # Calculate average recovery time across all resolved incidents
    resolved_with_duration = [i for i in resolved_incs if i.recovery_seconds is not None and i.recovery_seconds > 0]
    if resolved_with_duration:
        avg_seconds = sum(i.recovery_seconds for i in resolved_with_duration) / len(resolved_with_duration)
        if avg_seconds < 60:
            avg_recovery_str = f"{int(avg_seconds)}s"
        else:
            m = int(avg_seconds // 60)
            s = int(avg_seconds % 60)
            avg_recovery_str = f"{m}m {s}s"
    elif resolved_incs and resolved_incs[0].recovery_duration:
        avg_recovery_str = resolved_incs[0].recovery_duration
    else:
        avg_recovery_str = "No recovery data"

    # Agent Health (e.g. for env_agent_demo or any registered edge agent)
    agent_health = agent_svc.get_agent_health("env_agent_demo")
    agent_connected = agent_svc.is_agent_connected("env_agent_demo")

    # Calculate overall health
    if len(active_incs) > 0:
        overall_status = "RECOVERING" if len(recovering_incs) > 0 else "UNHEALTHY"
    elif len(escalated_incs) > 0:
        overall_status = "DEGRADED"
    else:
        overall_status = "HEALTHY"

    return {
        "status": overall_status,
        "kubernetes_connected": k8s_available,
        "prometheus_connected": prom_available,
        "agent_connected": agent_connected,
        "agent_health": agent_health,
        "active_incidents_count": len(active_incs),
        "recovering_count": len(recovering_incs),
        "auto_recovered_count": len(resolved_incs),
        "escalated_count": len(escalated_incs),
        "avg_recovery_time": avg_recovery_str,
        "recovering_incidents": [
            {
                "id": i.id,
                "title": i.title,
                "service": i.service,
                "stage": i.healing_stage.value if i.healing_stage else None,
                "status": i.status.value,
                "environment_id": i.environment_id,
            }
            for i in recovering_incs
        ],
        "escalated_incidents": [
            {
                "id": i.id,
                "title": i.title,
                "service": i.service,
                "reason": i.escalation_reason or i.error,
                "environment_id": i.environment_id,
            }
            for i in escalated_incs
        ],
        "auto_recovered_incidents": [
            {
                "id": i.id,
                "title": i.title,
                "service": i.service,
                "duration": i.recovery_duration,
                "action": i.selected_action,
                "environment_id": i.environment_id,
            }
            for i in resolved_incs[:5]
        ],
    }


@router.get("/health/workloads", summary="Detailed Workload Health States")
async def get_workload_health(
    k8s_service: KubernetesService = Depends(get_kubernetes_service),
    incidents: IncidentService = Depends(get_incident_service),
) -> Dict[str, Any]:
    """
    Evaluates individual workload statuses (HEALTHY, RECOVERING, UNHEALTHY).
    """
    workloads: List[Dict[str, Any]] = []
    k8s_status = k8s_service.get_status()

    # Active incidents mapped by service / deployment
    inc_list = incidents.list_incidents(limit=200)
    active_by_target: Dict[str, Any] = {}
    for inc in inc_list.incidents:
        if inc.status in (IncidentStatus.OPEN, IncidentStatus.ANALYZING, IncidentStatus.HEALING, IncidentStatus.VERIFYING):
            target = inc.service or inc.deployment or inc.pod or "unknown"
            active_by_target[target] = inc

    if k8s_status.get("available"):
        deps = k8s_service.get_deployments()
        for dep in deps.deployments:
            inc = active_by_target.get(dep.name)
            if inc:
                if inc.status in (IncidentStatus.HEALING, IncidentStatus.VERIFYING):
                    health_state = "RECOVERING"
                else:
                    health_state = "UNHEALTHY"
            elif dep.desired_replicas > 0 and dep.available_replicas < dep.desired_replicas:
                health_state = "UNHEALTHY"
            else:
                health_state = "HEALTHY"

            workloads.append({
                "name": dep.name,
                "namespace": dep.namespace,
                "type": "Deployment",
                "health_state": health_state,
                "desired_replicas": dep.desired_replicas,
                "available_replicas": dep.available_replicas,
                "ready_replicas": dep.ready_replicas,
                "active_incident_id": inc.id if inc else None,
            })

    return {
        "total": len(workloads),
        "workloads": workloads,
    }

