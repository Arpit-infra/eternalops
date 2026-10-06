"""Autonomous Healing Pipeline Orchestrator."""

import asyncio
import logging
from typing import Optional

from app.core.config import Settings, get_settings
from app.schemas.incidents import (
    HealingStage,
    Incident,
    IncidentStatus,
    RemediationAction,
)
from app.services.audit_service import AuditService, get_audit_service
from app.services.decision_engine import BaseDecisionEngine, get_decision_engine
from app.services.incident_service import IncidentService, get_incident_service
from app.services.notification_service import NotificationService, get_notification_service
from app.services.remediation_service import RemediationService, get_remediation_service
from app.services.verification_service import VerificationService, get_verification_service

logger = logging.getLogger("eternalops.healing_orchestrator")


class HealingOrchestrator:
    """Coordinates the autonomous self-healing lifecycle: Detection -> Analysis -> Decision -> Healing -> Verification -> Resolution."""

    def __init__(
        self,
        incident_service: Optional[IncidentService] = None,
        decision_engine: Optional[BaseDecisionEngine] = None,
        remediation_service: Optional[RemediationService] = None,
        verification_service: Optional[VerificationService] = None,
        audit_service: Optional[AuditService] = None,
        notification_service: Optional[NotificationService] = None,
        settings: Optional[Settings] = None,
    ):
        self.incidents = incident_service or get_incident_service()
        self.decision = decision_engine or get_decision_engine()
        self.remediation = remediation_service or get_remediation_service()
        self.verification = verification_service or get_verification_service()
        self.audit = audit_service or get_audit_service()
        self.notif = notification_service or get_notification_service()
        self.settings = settings or get_settings()

    async def run_healing_pipeline(self, incident: Incident) -> Incident:
        """Run the complete end-to-end autonomous healing pipeline for an incident."""
        logger.info("[Pipeline] Starting autonomous healing for %s (%s)", incident.id, incident.title)

        # STAGE 1: AI ANALYSIS
        self.incidents.set_stage(incident.id, HealingStage.ANALYSIS, IncidentStatus.ANALYZING)
        await asyncio.sleep(0.5)  # brief processing delay for smooth state propagation

        # Collect telemetry and model root cause
        decision_res = self.decision.evaluate(incident)

        incident.root_cause = decision_res.root_cause
        incident.confidence = decision_res.confidence
        incident.recommended_action = decision_res.action
        incident.selected_action = decision_res.action_label
        incident.requires_human = decision_res.requires_human
        self.incidents.update_incident(incident)

        self.audit.log(
            action="AI analysis completed: Root cause modeled",
            performed_by="AI Decision Engine",
            target=incident.pod or incident.deployment or incident.service,
            status="Success",
            duration="1s",
            incident_id=incident.id,
            details={"root_cause": decision_res.root_cause, "confidence": f"{decision_res.confidence}%"},
        )

        # STAGE 2: DECISION
        self.incidents.set_stage(incident.id, HealingStage.DECISION, IncidentStatus.ANALYZING)
        await asyncio.sleep(0.5)

        self.audit.log(
            action=f"Remediation selected: {decision_res.action_label}",
            performed_by="AI Decision Engine",
            target=incident.pod or incident.deployment or incident.service,
            status="Success" if decision_res.safe_to_execute else "Escalated",
            duration="0s",
            incident_id=incident.id,
            details={"confidence": f"{decision_res.confidence}%", "safe": decision_res.safe_to_execute},
        )

        # CHECK SAFETY POLICY
        if not decision_res.safe_to_execute or decision_res.action == RemediationAction.NONE:
            reason = decision_res.reason or "Automatic remediation unavailable or blocked by safety policy."
            logger.warning("[Pipeline] %s escalated: %s", incident.id, reason)
            updated = self.incidents.set_stage(
                incident.id,
                HealingStage.ESCALATED,
                IncidentStatus.ESCALATED,
                error=reason,
                escalation_reason=reason,
            )
            self.audit.log(
                action="Incident escalated: Human intervention required",
                performed_by="Safety Policy",
                target=incident.pod or incident.deployment or incident.service,
                status="Escalated",
                duration="0s",
                incident_id=incident.id,
                details={"reason": reason},
            )
            self.notif.notify(
                title=f"Incident Escalated ({incident.id})",
                message=f"{incident.title} — {reason}",
                type_="escalate",
                incident_id=incident.id,
            )
            return updated or incident

        # STAGE 3: HEALING (Execution)
        self.incidents.set_stage(incident.id, HealingStage.HEALING, IncidentStatus.HEALING)
        
        exec_success, exec_msg = self.remediation.execute_remediation(incident)
        if not exec_success:
            err_msg = f"Remediation execution failed: {exec_msg}"
            logger.error("[Pipeline] %s healing execution failed: %s", incident.id, err_msg)
            updated = self.incidents.set_stage(
                incident.id,
                HealingStage.ESCALATED,
                IncidentStatus.ESCALATED,
                error=err_msg,
                escalation_reason=err_msg,
            )
            self.audit.log(
                action="Remediation execution failed: Escalated",
                performed_by="Healing Engine",
                target=incident.pod or incident.deployment or incident.service,
                status="Failed",
                duration="1s",
                incident_id=incident.id,
                details={"error": exec_msg},
            )
            self.notif.notify(
                title=f"Healing Failed ({incident.id})",
                message=err_msg,
                type_="escalate",
                incident_id=incident.id,
            )
            return updated or incident

        # STAGE 4: VERIFICATION
        self.incidents.set_stage(incident.id, HealingStage.VERIFICATION, IncidentStatus.VERIFYING)
        
        verified, verify_msg = await self.verification.verify_remediation(incident)
        incident.verification_status = verify_msg

        if verified:
            # STAGE 5: RESOLVED
            updated = self.incidents.set_stage(incident.id, HealingStage.RESOLVED, IncidentStatus.RESOLVED)
            logger.info("[Pipeline] %s successfully RESOLVED (%s)", incident.id, updated.recovery_duration if updated else "")
            self.audit.log(
                action=f"Incident closed: Recovery verified in {updated.recovery_duration if updated else '—'}",
                performed_by="Healing Engine",
                target=incident.pod or incident.deployment or incident.service,
                status="Success",
                duration=updated.recovery_duration if updated else "—",
                incident_id=incident.id,
                details={"verification": verify_msg},
            )
            self.notif.notify(
                title=f"Incident Resolved ({incident.id})",
                message=f"{incident.title} healed successfully ({updated.recovery_duration if updated else ''})",
                type_="success",
                incident_id=incident.id,
            )
            return updated or incident
        else:
            # Healing action executed but verification failed -> ESCALATED
            fail_reason = f"Verification failed: {verify_msg}"
            logger.warning("[Pipeline] %s verification failed -> ESCALATING", incident.id)
            updated = self.incidents.set_stage(
                incident.id,
                HealingStage.ESCALATED,
                IncidentStatus.ESCALATED,
                error=fail_reason,
                escalation_reason=fail_reason,
            )
            self.audit.log(
                action="Healing failed: Metrics remained unstable — Escalated",
                performed_by="Verification Engine",
                target=incident.pod or incident.deployment or incident.service,
                status="Escalated",
                duration="—",
                incident_id=incident.id,
                details={"reason": fail_reason},
            )
            self.notif.notify(
                title=f"Verification Failed ({incident.id})",
                message=f"Healing attempted but {fail_reason}. Human intervention required.",
                type_="escalate",
                incident_id=incident.id,
            )
            return updated or incident


_healing_orchestrator_instance: Optional[HealingOrchestrator] = None


def get_healing_orchestrator() -> HealingOrchestrator:
    """Dependency provider for HealingOrchestrator."""
    global _healing_orchestrator_instance
    if _healing_orchestrator_instance is None:
        _healing_orchestrator_instance = HealingOrchestrator()
    return _healing_orchestrator_instance
