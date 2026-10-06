"""Decision Engine and Safety Policy for Autonomous Remediation."""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.schemas.incidents import Incident, RemediationAction

logger = logging.getLogger("eternalops.decision_engine")


class TelemetryFeatures(BaseModel):
    """Normalized telemetry features for decision analysis."""
    pod_name: Optional[str] = None
    deployment_name: Optional[str] = None
    namespace: str = "default"
    pod_phase: Optional[str] = None
    pod_restart_count: Optional[int] = None
    deployment_desired: Optional[int] = None
    deployment_available: Optional[int] = None
    deployment_ready: Optional[int] = None
    error_rate: Optional[float] = None
    latency_ms: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    is_protected_namespace: bool = False


class DecisionResult(BaseModel):
    """Output from the decision engine."""
    action: RemediationAction
    action_label: str
    confidence: int  # 0 - 100
    root_cause: str
    safe_to_execute: bool
    requires_human: bool
    reason: str
    features: TelemetryFeatures


class BaseDecisionEngine(ABC):
    """Abstract interface for EternalOps decision engines (Rule-based or ML)."""

    @abstractmethod
    def evaluate(self, incident: Incident, telemetry: Optional[Dict[str, Any]] = None) -> DecisionResult:
        """Evaluate an incident and return recommended remediation action."""
        pass


class SafetyPolicy:
    """Safety policy checks ensuring safe autonomous operations."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def is_namespace_protected(self, namespace: str) -> bool:
        """Check if target namespace is protected from automated mutation."""
        if not namespace:
            return True
        protected = [ns.lower() for ns in self.settings.PROTECTED_NAMESPACES]
        return namespace.lower() in protected

    def check_safety(
        self,
        incident: Incident,
        action: RemediationAction,
        confidence: int,
    ) -> (bool, str):
        """
        Validate whether the proposed action is safe to execute automatically.
        Returns: (is_safe, failure_reason)
        """
        # 1. Global healing killswitch
        if not self.settings.HEALING_ENABLED:
            return False, "Self-healing is globally disabled in configuration."

        # 2. Namespace safety check
        if self.is_namespace_protected(incident.namespace):
            return (
                False,
                f"Namespace '{incident.namespace}' is protected. Automated mutation is blocked; human approval required.",
            )

        # 3. Action allowlist check
        if action not in (RemediationAction.RESTART_POD, RemediationAction.ROLLOUT_RESTART_DEPLOYMENT):
            return False, f"Action '{action.value}' is not in the safe autonomous allowlist."

        # 4. Confidence threshold check
        min_conf = int(self.settings.AUTO_HEAL_CONFIDENCE_THRESHOLD * 100)
        if confidence < min_conf:
            return (
                False,
                f"Action confidence ({confidence}%) is below safe auto-heal threshold ({min_conf}%).",
            )

        # 5. Missing target check
        if action == RemediationAction.RESTART_POD and not incident.pod:
            return False, "Cannot restart pod: target pod name is missing."
        if action == RemediationAction.ROLLOUT_RESTART_DEPLOYMENT and not incident.deployment:
            return False, "Cannot rollout restart deployment: target deployment name is missing."

        return True, "Safety policy checks passed."


class RuleBasedDecisionEngine(BaseDecisionEngine):
    """
    Deterministic rule-based decision engine.
    Extracts telemetry features, models root cause, and enforces safety bounds.
    """

    def __init__(self, safety_policy: Optional[SafetyPolicy] = None):
        self.safety = safety_policy or SafetyPolicy()

    def extract_features(self, incident: Incident, telemetry: Optional[Dict[str, Any]] = None) -> TelemetryFeatures:
        """Extract and normalize telemetry features from incident and telemetry dict."""
        t = telemetry or incident.raw_telemetry or {}

        namespace = incident.namespace or t.get("namespace", "default")
        pod_name = incident.pod or t.get("pod_name")
        deployment_name = incident.deployment or t.get("deployment_name")

        pod_phase = t.get("pod_phase")
        pod_restart_count = t.get("pod_restart_count")
        deployment_desired = t.get("deployment_desired")
        deployment_available = t.get("deployment_available")
        deployment_ready = t.get("deployment_ready")
        error_rate = t.get("error_rate")
        latency_ms = t.get("latency_ms")
        cpu_usage = t.get("cpu_usage")
        memory_usage = t.get("memory_usage")

        is_prot = self.safety.is_namespace_protected(namespace)

        return TelemetryFeatures(
            pod_name=pod_name,
            deployment_name=deployment_name,
            namespace=namespace,
            pod_phase=pod_phase,
            pod_restart_count=pod_restart_count,
            deployment_desired=deployment_desired,
            deployment_available=deployment_available,
            deployment_ready=deployment_ready,
            error_rate=error_rate,
            latency_ms=latency_ms,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            is_protected_namespace=is_prot,
        )

    def evaluate(self, incident: Incident, telemetry: Optional[Dict[str, Any]] = None) -> DecisionResult:
        """Evaluate incident telemetry and select remediation action."""
        features = self.extract_features(incident, telemetry)
        title_lower = incident.title.lower()

        # Check for protected namespace first
        if features.is_protected_namespace:
            return DecisionResult(
                action=RemediationAction.NONE,
                action_label="Human Intervention Required",
                confidence=40,
                root_cause=f"Anomaly detected in protected system namespace '{features.namespace}'.",
                safe_to_execute=False,
                requires_human=True,
                reason=f"Namespace '{features.namespace}' is protected. Automated remediation blocked.",
                features=features,
            )

        # Rule 1: Pod restart anomaly or crash loop
        if (
            (features.pod_restart_count is not None and features.pod_restart_count > 0)
            or "restart" in title_lower
            or "crash" in title_lower
            or features.pod_phase == "Failed"
            or (features.pod_name and "unhealthy" in title_lower)
        ):
            action = RemediationAction.RESTART_POD
            action_label = f"Safe eviction and recreate pod {features.pod_name or incident.service}"
            confidence = 92
            root_cause = (
                f"Pod '{features.pod_name or incident.service}' container experienced repeated failures "
                f"or non-zero exit codes. Deadlock or memory exhaustion suspected."
            )
            is_safe, reason = self.safety.check_safety(incident, action, confidence)
            return DecisionResult(
                action=action,
                action_label=action_label,
                confidence=confidence,
                root_cause=root_cause,
                safe_to_execute=is_safe,
                requires_human=not is_safe,
                reason=reason,
                features=features,
            )

        # Rule 2: Deployment unavailable replicas
        if (
            (
                features.deployment_desired is not None
                and features.deployment_available is not None
                and features.deployment_available < features.deployment_desired
            )
            or "unavailable" in title_lower
            or "deployment" in title_lower
            or incident.deployment is not None
        ):
            action = RemediationAction.ROLLOUT_RESTART_DEPLOYMENT
            dep_name = features.deployment_name or incident.deployment or incident.service
            action_label = f"Rollout restart deployment {dep_name}"
            confidence = 88
            root_cause = (
                f"Deployment '{dep_name}' has unavailable replicas. "
                "Rollout stalled or pods stuck in non-ready state."
            )
            is_safe, reason = self.safety.check_safety(incident, action, confidence)
            return DecisionResult(
                action=action,
                action_label=action_label,
                confidence=confidence,
                root_cause=root_cause,
                safe_to_execute=is_safe,
                requires_human=not is_safe,
                reason=reason,
                features=features,
            )

        # Rule 3: Pod in Pending state / Unscheduled
        if features.pod_phase == "Pending" or "pending" in title_lower:
            return DecisionResult(
                action=RemediationAction.NONE,
                action_label="Escalate to cluster administrator",
                confidence=35,
                root_cause="Pod stuck in Pending state due to node resource constraints or scheduling affinity.",
                safe_to_execute=False,
                requires_human=True,
                reason="Automatic remediation unavailable: pod scheduling requires cluster capacity or node intervention.",
                features=features,
            )

        # Rule 4: High error rate or latency on service with known pod
        if features.pod_name:
            action = RemediationAction.RESTART_POD
            action_label = f"Restart pod {features.pod_name}"
            confidence = 82
            root_cause = "Elevated telemetry anomaly correlated with active service workload."
            is_safe, reason = self.safety.check_safety(incident, action, confidence)
            return DecisionResult(
                action=action,
                action_label=action_label,
                confidence=confidence,
                root_cause=root_cause,
                safe_to_execute=is_safe,
                requires_human=not is_safe,
                reason=reason,
                features=features,
            )

        # Fallback: Unknown condition -> Safe escalation
        return DecisionResult(
            action=RemediationAction.NONE,
            action_label="Escalate to on-call engineer",
            confidence=30,
            root_cause="Telemetry pattern does not match safe autonomous remediation heuristics.",
            safe_to_execute=False,
            requires_human=True,
            reason="Unrecognized anomaly pattern. Human intervention required.",
            features=features,
        )


_decision_engine_instance: Optional[BaseDecisionEngine] = None


def get_decision_engine() -> BaseDecisionEngine:
    """Dependency provider for Decision Engine."""
    global _decision_engine_instance
    if _decision_engine_instance is None:
        _decision_engine_instance = RuleBasedDecisionEngine()
    return _decision_engine_instance
