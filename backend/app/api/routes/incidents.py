"""Incident management API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.incidents import (
    HealingStage,
    Incident,
    IncidentActionResponse,
    IncidentCreate,
    IncidentSeverity,
    IncidentStatus,
    IncidentTestRequest,
    IncidentsListResponse,
    RemediationAction,
)
from app.services.healing_orchestrator import HealingOrchestrator, get_healing_orchestrator
from app.services.incident_service import IncidentService, get_incident_service

logger = logging.getLogger("eternalops.api.incidents")

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=IncidentsListResponse, summary="List incidents")
def list_incidents(
    severity: Optional[str] = Query(None, description="Filter by severity: all, critical, warning, info"),
    status: Optional[str] = Query(None, description="Filter by status: all, OPEN, HEALING, RESOLVED, ESCALATED"),
    search: Optional[str] = Query(None, description="Search term across id, title, service"),
    limit: int = Query(100, ge=1, le=500),
    service: IncidentService = Depends(get_incident_service),
) -> IncidentsListResponse:
    """Retrieve incidents with optional filtering and search."""
    return service.list_incidents(severity=severity, status=status, search=search, limit=limit)


@router.get("/{incident_id}", response_model=Incident, summary="Get incident details")
def get_incident(
    incident_id: str,
    service: IncidentService = Depends(get_incident_service),
) -> Incident:
    """Retrieve details for a single incident."""
    inc = service.get_by_id(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return inc


@router.post("/test", response_model=Incident, summary="Trigger a safe test incident")
async def trigger_test_incident(
    payload: Optional[IncidentTestRequest] = None,
    incidents: IncidentService = Depends(get_incident_service),
    orchestrator: HealingOrchestrator = Depends(get_healing_orchestrator),
) -> Incident:
    """Create a controlled test incident and run through the healing pipeline."""
    req = payload or IncidentTestRequest()
    
    if req.simulate_escalation:
        # Scenario: Unhealable incident on a protected namespace or unsupported action
        anomaly = IncidentCreate(
            title=f"Critical storage corruption on {req.service}",
            description="Persistent volume mount failed. Automatic remediation unavailable for disk corruption.",
            severity=IncidentSeverity.CRITICAL,
            service=req.service,
            namespace="kube-system" if req.namespace == "default" else req.namespace,
            detection_source="Prometheus (Simulated Storage Probe)",
            fingerprint=f"test:escalation:{req.service}",
            organization_id=req.organization_id or "org_default",
            environment_id=req.environment_id or "env_local_dev",
            metrics="I/O Error: Read-only file system · Inodes exhausted",
            logs="EXT4-fs error (device sda1): ext4_lookup: deleted inode referenced",
        )
    else:
        # Scenario: Normal healable pod restart
        anomaly = IncidentCreate(
            title=f"Elevated restart anomaly on {req.service}",
            description=f"Prometheus flagged abnormal restarts on container {req.service}.",
            severity=req.severity or IncidentSeverity.WARNING,
            service=req.service,
            namespace=req.namespace or "default",
            pod=req.pod or f"{req.service}-pod-test",
            deployment=req.deployment,
            detection_source="Prometheus (Simulated)",
            fingerprint=f"test:healable:{req.service}",
            organization_id=req.organization_id or "org_default",
            environment_id=req.environment_id or "env_local_dev",
            metrics="Restarts: 4 · Memory: 88% · CPU: 72%",
            logs="WARN  heap usage critical — container terminated with exit code 137 (OOMKilled)",
        )

    incident = incidents.create_incident(anomaly)
    # Run through orchestrator asynchronously
    import asyncio
    asyncio.create_task(orchestrator.run_healing_pipeline(incident))
    return incident


@router.post("/{incident_id}/heal", response_model=IncidentActionResponse, summary="Trigger manual healing")
async def heal_incident(
    incident_id: str,
    incidents: IncidentService = Depends(get_incident_service),
    orchestrator: HealingOrchestrator = Depends(get_healing_orchestrator),
) -> IncidentActionResponse:
    """Trigger the autonomous self-healing pipeline for a specific incident."""
    inc = incidents.get_by_id(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    if inc.status == IncidentStatus.RESOLVED:
        return IncidentActionResponse(
            success=True,
            incident=inc,
            message=f"Incident {incident_id} is already resolved.",
        )

    updated = await orchestrator.run_healing_pipeline(inc)
    return IncidentActionResponse(
        success=updated.status == IncidentStatus.RESOLVED,
        incident=updated,
        message=f"Healing completed with status: {updated.status.value}",
    )


@router.post("/{incident_id}/resolve", response_model=IncidentActionResponse, summary="Mark incident resolved")
def resolve_incident(
    incident_id: str,
    incidents: IncidentService = Depends(get_incident_service),
) -> IncidentActionResponse:
    """Manually mark an incident as resolved."""
    inc = incidents.set_stage(incident_id, HealingStage.RESOLVED, IncidentStatus.RESOLVED)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return IncidentActionResponse(
        success=True,
        incident=inc,
        message=f"Incident {incident_id} marked as RESOLVED.",
    )


@router.post("/{incident_id}/escalate", response_model=IncidentActionResponse, summary="Escalate incident")
def escalate_incident(
    incident_id: str,
    reason: Optional[str] = Query("Manual engineer escalation", description="Reason for escalation"),
    incidents: IncidentService = Depends(get_incident_service),
) -> IncidentActionResponse:
    """Manually escalate an incident for human intervention."""
    inc = incidents.set_stage(
        incident_id,
        HealingStage.ESCALATED,
        IncidentStatus.ESCALATED,
        escalation_reason=reason,
    )
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return IncidentActionResponse(
        success=True,
        incident=inc,
        message=f"Incident {incident_id} escalated for human intervention.",
    )
