"""Test Decision Engine rules, safety policies, and feature extraction."""

import pytest
from app.core.config import Settings
from app.schemas.incidents import Incident, IncidentSeverity, IncidentStatus, RemediationAction
from app.services.decision_engine import RuleBasedDecisionEngine, SafetyPolicy


def test_decision_engine_pod_restart_rule():
    """Verify pod restart anomaly triggers RESTART_POD decision."""
    engine = RuleBasedDecisionEngine()
    incident = Incident(
        id="INC-1001",
        fingerprint="default:pod_restart:auth-svc-123",
        title="Elevated restart count on auth-svc-123",
        severity=IncidentSeverity.CRITICAL,
        service="auth-svc",
        namespace="default",
        pod="auth-svc-123",
    )
    telemetry = {"pod_restart_count": 3, "pod_phase": "Running"}
    decision = engine.evaluate(incident, telemetry)

    assert decision.action == RemediationAction.RESTART_POD
    assert decision.confidence >= 80
    assert decision.safe_to_execute is True
    assert decision.requires_human is False


def test_decision_engine_deployment_unavailable_rule():
    """Verify deployment replica mismatch triggers ROLLOUT_RESTART_DEPLOYMENT."""
    engine = RuleBasedDecisionEngine()
    incident = Incident(
        id="INC-1002",
        fingerprint="default:deployment:web-svc",
        title="Deployment replica mismatch on web-svc",
        severity=IncidentSeverity.CRITICAL,
        service="web-svc",
        namespace="default",
        deployment="web-svc",
    )
    telemetry = {"deployment_desired": 3, "deployment_available": 1}
    decision = engine.evaluate(incident, telemetry)

    assert decision.action == RemediationAction.ROLLOUT_RESTART_DEPLOYMENT
    assert decision.confidence >= 80
    assert decision.safe_to_execute is True


def test_decision_engine_protected_namespace_blocks_execution():
    """Verify safety policy prevents automatic mutation of kube-system resources."""
    engine = RuleBasedDecisionEngine()
    incident = Incident(
        id="INC-1003",
        fingerprint="kube-system:pod_restart:coredns-123",
        title="CoreDNS restarting in kube-system",
        severity=IncidentSeverity.CRITICAL,
        service="coredns",
        namespace="kube-system",
        pod="coredns-123",
    )
    decision = engine.evaluate(incident)

    assert decision.safe_to_execute is False
    assert decision.requires_human is True
    assert "protected" in decision.reason.lower()


def test_safety_policy_killswitch():
    """Verify safety policy blocks execution when HEALING_ENABLED is false."""
    settings = Settings(HEALING_ENABLED=False)
    policy = SafetyPolicy(settings=settings)
    incident = Incident(
        id="INC-1004",
        fingerprint="default:pod:test",
        title="Test incident",
        severity=IncidentSeverity.WARNING,
        service="test-svc",
        namespace="default",
        pod="test-pod",
    )
    is_safe, reason = policy.check_safety(incident, RemediationAction.RESTART_POD, confidence=90)
    assert is_safe is False
    assert "disabled" in reason.lower()
