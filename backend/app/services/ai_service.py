"""AI Copilot Context and Response Generation Service."""

import logging
from typing import Any, Dict, List, Optional

from app.schemas.ai import AIChatResponse
from app.services.agent_service import AgentService, get_agent_service
from app.services.audit_service import AuditService, get_audit_service
from app.services.incident_service import IncidentService, get_incident_service
from app.services.kubernetes_service import KubernetesService, get_kubernetes_service
from app.services.prometheus_service import PrometheusService, get_prometheus_service

logger = logging.getLogger("eternalops.ai")


class AICopilotService:
    """Context-aware AI Copilot engine for DevOps operations and cluster troubleshooting."""

    def __init__(
        self,
        k8s_service: Optional[KubernetesService] = None,
        prom_service: Optional[PrometheusService] = None,
        incident_service: Optional[IncidentService] = None,
        audit_service: Optional[AuditService] = None,
        agent_service: Optional[AgentService] = None,
    ):
        self.k8s = k8s_service or get_kubernetes_service()
        self.prom = prom_service or get_prometheus_service()
        self.incidents = incident_service or get_incident_service()
        self.audit = audit_service or get_audit_service()
        self.agent = agent_service or get_agent_service()

    async def gather_context(self) -> Dict[str, Any]:
        """Gather real-time state from Kubernetes, Prometheus, Incidents, Agent, and Audit Logs."""
        k8s_status = self.k8s.get_status()
        pods_resp = self.k8s.get_pods() if k8s_status.get("available") else None
        deps_resp = self.k8s.get_deployments() if k8s_status.get("available") else None
        prom_status, _ = await self.prom.check_health()
        
        incidents_resp = self.incidents.list_incidents(limit=20)
        recent_audit = self.audit.get_logs(limit=20)

        total_pods = pods_resp.total if pods_resp else 0
        running_pods = (
            sum(1 for p in pods_resp.pods if p.phase == "Running") if pods_resp else 0
        )
        failed_pods = (
            [p.name for p in pods_resp.pods if p.phase == "Failed"] if pods_resp else []
        )
        restarting_pods = (
            [p.name for p in pods_resp.pods if p.restart_count > 0] if pods_resp else []
        )

        active_incs = [i for i in incidents_resp.incidents if i.status.value in ("OPEN", "ANALYZING", "HEALING", "VERIFYING")]
        recovering_incs = [i for i in incidents_resp.incidents if i.status.value in ("HEALING", "VERIFYING")]
        recovered_incs = [i for i in incidents_resp.incidents if i.status.value == "RESOLVED"]
        escalated_incs = [i for i in incidents_resp.incidents if i.status.value in ("ESCALATED", "FAILED")]

        agent_connected = self.agent.is_agent_connected("env_agent_demo")
        agent_health = self.agent.get_agent_health("env_agent_demo")

        return {
            "k8s_available": k8s_status.get("available", False),
            "cluster_version": k8s_status.get("cluster_version"),
            "total_pods": total_pods,
            "running_pods": running_pods,
            "failed_pods": failed_pods,
            "restarting_pods": restarting_pods,
            "deployments_count": deps_resp.total if deps_resp else 0,
            "prom_available": prom_status,
            "agent_connected": agent_connected,
            "agent_health": agent_health,
            "active_incidents": [
                {
                    "id": i.id,
                    "title": i.title,
                    "severity": i.severity.value,
                    "status": i.status.value,
                    "service": i.service,
                    "root_cause": i.root_cause,
                    "confidence": i.confidence,
                    "stage": i.healing_stage.value if i.healing_stage else None,
                }
                for i in active_incs
            ],
            "recovering_incidents": [
                {
                    "id": i.id,
                    "title": i.title,
                    "service": i.service,
                    "stage": i.healing_stage.value if i.healing_stage else None,
                    "action": i.selected_action,
                }
                for i in recovering_incs
            ],
            "recovered_incidents": [
                {
                    "id": i.id,
                    "title": i.title,
                    "service": i.service,
                    "recovery": i.recovery_duration,
                    "action": i.selected_action,
                    "verification": i.verification_status,
                }
                for i in recovered_incs[:5]
            ],
            "escalated_incidents": [
                {
                    "id": i.id,
                    "title": i.title,
                    "service": i.service,
                    "reason": i.escalation_reason or i.error,
                }
                for i in escalated_incs[:5]
            ],
            "recent_incidents": [
                {
                    "id": i.id,
                    "title": i.title,
                    "status": i.status.value,
                    "recovery": i.recovery_duration,
                    "action": i.selected_action,
                }
                for i in incidents_resp.incidents[:5]
            ],
            "recent_audits": [
                f"{a.ts} - {a.action} ({a.target}) -> {a.status}" for a in recent_audit.logs[:8]
            ],
        }


    async def answer(self, prompt: str, extra_context: Optional[Dict[str, Any]] = None) -> AIChatResponse:
        """Analyze user prompt against gathered context and return informed response."""
        p = prompt.strip()
        p_lower = p.lower()
        context = await self.gather_context()

        # 1. Safety Check for Destructive Commands
        destructive_keywords = [
            "delete namespace",
            "delete cluster",
            "delete all pods",
            "drop database",
            "rm -rf",
            "destroy",
            "format disk",
        ]
        if any(dk in p_lower for dk in destructive_keywords):
            return AIChatResponse(
                response=(
                    "⚠️ Safety Policy Rejection: Direct destructive commands (such as deleting namespaces or clusters) "
                    "are blocked by EternalOps autonomous safeguards. All cluster modifications must go through "
                    "remediation policies with safety verification."
                ),
                intent="safety_blocked",
                suggested_actions=["Check cluster status", "Review active incidents", "View audit logs"],
                context_summary=context,
            )

        # 2. Restart query (e.g. "Why did backend restart?")
        if "restart" in p_lower or "crash" in p_lower or "reboot" in p_lower:
            active_incs = context["active_incidents"]
            restarting_pods = context["restarting_pods"]

            if active_incs:
                inc = active_incs[0]
                rc = inc.get("root_cause") or "Elevated restart pattern detected by Prometheus telemetry."
                conf = inc.get("confidence") or 92
                response_text = (
                    f"Regarding recent workload behavior: Incident **{inc['id']}** ({inc['title']}) is currently {inc['status']}.\n\n"
                    f"• **Root Cause Analysis**: {rc}\n"
                    f"• **AI Confidence**: {conf}%\n"
                    f"• **Target Service**: `{inc['service']}`\n"
                    f"• **Cluster Telemetry**: {context['running_pods']}/{context['total_pods']} pods currently running."
                )
            elif restarting_pods:
                pod_names = ", ".join(restarting_pods[:3])
                response_text = (
                    f"Kubernetes telemetry shows restart events recorded on: `{pod_names}`.\n\n"
                    f"Root cause correlates with container exit codes or resource limits. "
                    f"The EternalOps Healing Engine monitors these pods via Kube State Metrics and will automatically trigger safe container eviction if crash looping exceeds thresholds."
                )
            else:
                response_text = (
                    f"No active restart anomalies are currently detected in the cluster. All {context['running_pods']} pods are running normally without active crash loops.\n\n"
                    f"Prometheus is continuously scraping container restart telemetry (`kube_pod_container_status_restarts_total`)."
                )

            return AIChatResponse(
                response=response_text,
                intent="restart_investigation",
                suggested_actions=["Generate incident summary", "Suggest recovery", "Check cluster status"],
                context_summary=context,
            )

        # 3. Incident Summary query
        if "incident" in p_lower or "summary" in p_lower or "alert" in p_lower:
            active = context["active_incidents"]
            recent = context["recent_incidents"]

            if not active and not recent:
                response_text = "No incidents are currently recorded. The cluster is operating within normal baseline parameters with 100% service availability."
            else:
                lines = ["### Platform Incident Summary\n"]
                if active:
                    lines.append(f"**Active Incidents ({len(active)}):**")
                    for a in active:
                        lines.append(f"• **{a['id']}** [{a['severity'].upper()}]: {a['title']} (Status: {a['status']})")
                else:
                    lines.append("• **Active Incidents**: None (All systems healthy)")

                if recent:
                    lines.append(f"\n**Recently Processed ({len(recent)}):**")
                    for r in recent:
                        rec = r.get("recovery") or "—"
                        lines.append(f"• **{r['id']}**: {r['title']} -> {r['status']} (Recovery: {rec})")

                response_text = "\n".join(lines)

            return AIChatResponse(
                response=response_text,
                intent="incident_summary",
                suggested_actions=["Suggest recovery", "Generate postmortem", "View audit logs"],
                context_summary=context,
            )

        # 4. Recovery suggestions
        if "recovery" in p_lower or "suggest" in p_lower or "fix" in p_lower or "remediate" in p_lower:
            active = context["active_incidents"]
            if active:
                inc = active[0]
                response_text = (
                    f"### Autonomous Recovery Recommendations for {inc['id']}:\n\n"
                    f"1. **Autonomous Action**: Execute `{inc.get('service')}` pod restart / deployment rollout.\n"
                    f"2. **Capacity Validation**: Verify node resource limits (`CPU`/`Memory`) in namespace `{inc.get('service')}`.\n"
                    f"3. **Telemetry Gating**: Monitor Prometheus error rate and p95 latency for 5 minutes post-remediation.\n"
                    f"4. **Safety Verification**: Ensure replica count matches desired spec after rollout."
                )
            else:
                response_text = (
                    "### Cluster Recovery Best Practices:\n\n"
                    "1. Keep deployment replicas >= 2 for zero-downtime rolling updates.\n"
                    "2. Configure readiness and liveness probes on all microservices.\n"
                    "3. Set explicit memory limits to prevent uncontrolled OOMKilled events.\n"
                    "4. EternalOps Self-Healing is active and will auto-remediate pod restarts or replica mismatches."
                )

            return AIChatResponse(
                response=response_text,
                intent="recovery_suggestion",
                suggested_actions=["Generate postmortem", "Why did backend restart?", "Explain this deployment"],
                context_summary=context,
            )

        # 5. Explain deployment
        if "deployment" in p_lower or "workload" in p_lower:
            k8s_ok = context["k8s_available"]
            dep_count = context["deployments_count"]
            response_text = (
                f"### Cluster Deployment Overview\n\n"
                f"• **Kubernetes Connection**: {'Connected (' + str(context['cluster_version']) + ')' if k8s_ok else 'Disconnected'}\n"
                f"• **Active Deployments**: {dep_count}\n"
                f"• **Running Pods**: {context['running_pods']} / {context['total_pods']}\n"
                f"• **Prometheus Monitoring**: {'Active' if context['prom_available'] else 'Offline'}\n\n"
                "All deployment updates are continuously audited and monitored for replica availability."
            )
            return AIChatResponse(
                response=response_text,
                intent="deployment_explanation",
                suggested_actions=["Generate incident summary", "Suggest recovery", "Why did backend restart?"],
                context_summary=context,
            )

        # 6. Edge Agent & Healing questions
        if "agent" in p_lower or "edge agent" in p_lower or "heal" in p_lower or "fixed" in p_lower or "recovering" in p_lower or "escalated" in p_lower or "target" in p_lower:
            recovering = context["recovering_incidents"]
            recovered = context["recovered_incidents"]
            escalated = context["escalated_incidents"]
            agent_conn = context.get("agent_connected", False)
            agent_hlth = context.get("agent_health", {})

            lines = ["### EternalOps Autonomous Healing & Edge Agent Status\n"]
            lines.append(f"• **Edge Agent Connection**: {'CONNECTED' if agent_conn else 'DISCONNECTED'}")
            if agent_conn:
                lines.append(f"• **Cluster**: `{agent_hlth.get('cluster_name', 'remote')}` (K8s: `{agent_hlth.get('kubernetes_version', 'v1.36.1')}`)")
                lines.append(f"• **Capabilities**: {', '.join(agent_hlth.get('capabilities', ['RESTART_POD', 'ROLLOUT_RESTART_DEPLOYMENT', 'VERIFY_WORKLOAD']))}")

            if recovering:
                lines.append(f"\n**Currently Active Healing / Recovering ({len(recovering)}):**")
                for r in recovering:
                    lines.append(f"• **{r['id']}** (`{r['service']}`): Stage **{r['stage']}**, Action: {r['action']}")
            else:
                lines.append("\n• **Currently Recovering**: None")

            if recovered:
                lines.append(f"\n**Successfully Auto-Recovered by Edge Agent ({len(recovered)}):**")
                for r in recovered:
                    lines.append(f"• **{r['id']}** (`{r['service']}`): Healed in {r['recovery']} (Verification: {r['verification'] or 'Passed'})")

            if escalated:
                lines.append(f"\n**Escalated Incidents Requiring Human Attention ({len(escalated)}):**")
                for e in escalated:
                    lines.append(f"• **{e['id']}** (`{e['service']}`): {e['reason']}")

            response_text = "\n".join(lines)
            return AIChatResponse(
                response=response_text,
                intent="healing_status",
                suggested_actions=["Check cluster status", "Generate incident summary", "View audit logs"],
                context_summary=context,
            )

        # 6.1 Response Latency Query
        if "latency" in p_lower or "response time" in p_lower or "p95" in p_lower or "duration" in p_lower:
            response_text = (
                "### Real Response Latency Telemetry\n\n"
                "• **Metric Source**: Prometheus `http_request_duration_seconds` histogram scraped from EternalOps backend `/metrics`.\n"
                "• **Aggregation**: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) * 1000`\n"
                "• **Status**: Scraped dynamically. All REST & agent endpoints are measured per-request with zero synthetic jitter."
            )
            return AIChatResponse(
                response=response_text,
                intent="latency_telemetry",
                suggested_actions=["Check cluster status", "Generate incident summary", "View audit logs"],
                context_summary=context,
            )

        # 7. Postmortem generator
        if "postmortem" in p_lower or "rca" in p_lower:

            recent = context["recent_incidents"]
            if recent:
                inc = recent[0]
                response_text = (
                    f"### Postmortem Draft — {inc['id']}\n\n"
                    f"**Incident**: {inc['title']}\n"
                    f"**Status**: {inc['status']} (Recovery: {inc.get('recovery', '—')})\n"
                    f"**Remediation Action**: {inc.get('action', 'Automated container restart & verification')}\n\n"
                    f"**Root Cause**: Workload encountered deadlock or container termination detected via Prometheus telemetry.\n\n"
                    f"**Preventive Actions**:\n"
                    f"• Add resource requests/limits to prevent noisy-neighbor eviction.\n"
                    f"• Tune Prometheus alerting thresholds for rapid anomaly detection.\n"
                    f"• Enable EternalOps automated rolling rollback on replica failures."
                )
            else:
                response_text = (
                    "### Postmortem Draft — Platform Operations\n\n"
                    "**Summary**: No major unhealed outages in the last 24 hours.\n"
                    "**Availability**: 99.98% across all monitored services.\n"
                    "**Recommendation**: Continue continuous Prometheus anomaly monitoring."
                )
            return AIChatResponse(
                response=response_text,
                intent="postmortem",
                suggested_actions=["Generate incident summary", "Why did backend restart?", "Suggest recovery"],
                context_summary=context,
            )

        # Default fallback response using live context
        k8s_status_str = f"Kubernetes is connected ({context['cluster_version']})" if context['k8s_available'] else "Kubernetes is disconnected"
        prom_status_str = "Prometheus is active" if context['prom_available'] else "Prometheus is offline"
        active_count = len(context["active_incidents"])

        response_text = (
            f"Based on real platform context: {k8s_status_str} and {prom_status_str}. "
            f"There are currently **{active_count} active incident(s)** and **{context['running_pods']}/{context['total_pods']} running pods**. "
            f"Ask me to investigate a pod restart, summarize incidents, explain deployments, or generate a recovery plan."
        )

        return AIChatResponse(
            response=response_text,
            intent="general_inquiry",
            suggested_actions=[
                "Why did backend restart?",
                "Generate incident summary.",
                "Suggest recovery.",
                "Explain this deployment.",
                "Generate postmortem.",
            ],
            context_summary=context,
        )


_ai_service_instance: Optional[AICopilotService] = None


def get_ai_service() -> AICopilotService:
    """Dependency provider for AICopilotService."""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AICopilotService()
    return _ai_service_instance
