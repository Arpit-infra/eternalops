"""Test complete healing orchestrator pipeline and escalation flows."""

import pytest
from app.schemas.incidents import (
    HealingStage,
    IncidentCreate,
    IncidentSeverity,
    IncidentStatus,
    RemediationAction,
)
from app.services.audit_service import AuditService
from app.services.decision_engine import RuleBasedDecisionEngine
from app.services.healing_orchestrator import HealingOrchestrator
from app.services.incident_service import IncidentService
from app.services.notification_service import NotificationService
from app.services.remediation_service import RemediationService
from app.services.verification_service import VerificationService


class MockSuccessfulRemediationService:
    def execute_remediation(self, incident):
        return True, "Mock pod restarted successfully."


class MockSuccessfulVerificationService:
    async def verify_remediation(self, incident, timeout_seconds=None, poll_interval=None):
        return True, "Mock verification: 1/1 pods running and ready."


class MockFailingVerificationService:
    async def verify_remediation(self, incident, timeout_seconds=None, poll_interval=None):
        return False, "Pod remained in CrashLoopBackOff after 60s timeout."


@pytest.mark.asyncio
async def test_full_healing_pipeline_success():
    """Verify end-to-end detection -> analysis -> decision -> healing -> verification -> resolution."""
    audit_svc = AuditService()
    notif_svc = NotificationService()
    inc_svc = IncidentService(audit_service=audit_svc, notification_service=notif_svc)
    dec_engine = RuleBasedDecisionEngine()

    orchestrator = HealingOrchestrator(
        incident_service=inc_svc,
        decision_engine=dec_engine,
        remediation_service=MockSuccessfulRemediationService(),
        verification_service=MockSuccessfulVerificationService(),
        audit_service=audit_svc,
        notification_service=notif_svc,
    )

    inc = inc_svc.create_incident(
        IncidentCreate(
            title="Elevated restarts on checkout-svc",
            service="checkout-svc",
            namespace="default",
            pod="checkout-svc-xyz",
            severity=IncidentSeverity.CRITICAL,
        )
    )

    result = await orchestrator.run_healing_pipeline(inc)
    assert result.status == IncidentStatus.RESOLVED
    assert result.healing_stage == HealingStage.RESOLVED
    assert result.recovery_duration is not None
    assert result.escalated is False

    # Check that audit logs were generated
    logs = audit_svc.get_logs(incident_id=inc.id)
    assert logs.total >= 4  # detected, analysis, decision, healing/verification, resolved


@pytest.mark.asyncio
async def test_healing_pipeline_escalation_on_verification_failure():
    """Verify that when verification fails, the incident transitions to ESCALATED with proper reason."""
    audit_svc = AuditService()
    notif_svc = NotificationService()
    inc_svc = IncidentService(audit_service=audit_svc, notification_service=notif_svc)
    dec_engine = RuleBasedDecisionEngine()

    orchestrator = HealingOrchestrator(
        incident_service=inc_svc,
        decision_engine=dec_engine,
        remediation_service=MockSuccessfulRemediationService(),
        verification_service=MockFailingVerificationService(),
        audit_service=audit_svc,
        notification_service=notif_svc,
    )

    inc = inc_svc.create_incident(
        IncidentCreate(
            title="Deadlock on order-svc",
            service="order-svc",
            namespace="default",
            pod="order-svc-abc",
            severity=IncidentSeverity.CRITICAL,
        )
    )

    result = await orchestrator.run_healing_pipeline(inc)
    assert result.status == IncidentStatus.ESCALATED
    assert result.healing_stage == HealingStage.ESCALATED
    assert result.escalated is True
    assert "CrashLoopBackOff" in result.escalation_reason

    # Notifications should include escalation
    notifs = notif_svc.get_notifications()
    assert any(n.type == "escalate" for n in notifs.notifications)
