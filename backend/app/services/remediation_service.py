"""Kubernetes & Multi-Environment Remediation Service for executing safe healing actions."""

import logging
from typing import Optional, Tuple

from app.schemas.incidents import Incident, RemediationAction
from app.services.audit_service import AuditService, get_audit_service
from app.services.connections.connection_manager import ConnectionManager, get_connection_manager
from app.services.decision_engine import SafetyPolicy

logger = logging.getLogger("eternalops.remediation")


class RemediationService:
    """Orchestrates remediation actions across connected environments with strict safety controls."""

    def __init__(
        self,
        connection_manager: Optional[ConnectionManager] = None,
        audit_service: Optional[AuditService] = None,
        safety_policy: Optional[SafetyPolicy] = None,
    ):
        self.conn_mgr = connection_manager or get_connection_manager()
        self.audit = audit_service or get_audit_service()
        self.safety = safety_policy or SafetyPolicy()

    def execute_remediation(self, incident: Incident) -> Tuple[bool, str]:
        """
        Execute the selected remediation action against the environment specified in the incident.
        Resolves the appropriate EnvironmentConnection via ConnectionManager.
        Returns: (success, message)
        """
        action = incident.recommended_action or RemediationAction.NONE
        target = incident.pod or incident.deployment or incident.service
        namespace = incident.namespace or "default"
        env_id = incident.environment_id or "env_local_dev"
        org_id = incident.organization_id or "org_default"

        logger.info(
            "[Healing] Executing action %s for incident %s on %s/%s in Environment '%s'",
            action.value,
            incident.id,
            namespace,
            target,
            env_id,
        )

        # Safety policy double check
        if self.safety.is_namespace_protected(namespace):
            msg = f"Execution blocked: namespace '{namespace}' is protected."
            self.audit.log(
                action=f"Remediation blocked ({action.value})",
                performed_by="Safety Policy",
                target=target,
                status="Escalated",
                duration="0s",
                incident_id=incident.id,
                organization_id=org_id,
                environment_id=env_id,
                details={"reason": msg},
            )
            return False, msg

        # Resolve Environment Connection via ConnectionManager
        try:
            conn = self.conn_mgr.get_connection(environment_id=env_id)
        except Exception as exc:
            msg = f"Failed to resolve connection for environment '{env_id}': {str(exc)}"
            logger.error("[Healing] %s", msg)
            return False, msg

        if not conn.is_connected():
            msg = f"Target environment '{env_id}' connection is not active or offline."
            logger.warning("[Healing] %s", msg)
            return False, msg

        conn_type = getattr(conn, "connection_type", "unknown")

        if action == RemediationAction.RESTART_POD:
            if not incident.pod:
                # If no specific pod name, find pod matching service name in target connection
                pod_resp = conn.list_pods(namespace=namespace)
                matching = [p for p in pod_resp.pods if incident.service in p.name]
                if matching:
                    pod_to_restart = matching[0].name
                else:
                    return False, f"Cannot find matching pod for service '{incident.service}' in environment '{env_id}'."
            else:
                pod_to_restart = incident.pod

            success, msg = conn.restart_pod(namespace=namespace, name=pod_to_restart)
            self.audit.log(
                action=f"Pod restart ({pod_to_restart})",
                performed_by="Healing Engine",
                target=pod_to_restart,
                status="Success" if success else "Failed",
                duration="2s",
                incident_id=incident.id,
                organization_id=org_id,
                environment_id=env_id,
                connection_type=conn_type,
                details={"namespace": namespace, "result": msg, "environment_id": env_id},
            )
            return success, msg

        elif action == RemediationAction.ROLLOUT_RESTART_DEPLOYMENT:
            dep_name = incident.deployment or incident.service
            success, msg = conn.rollout_restart_deployment(namespace=namespace, name=dep_name)
            self.audit.log(
                action=f"Deployment rollout restart ({dep_name})",
                performed_by="Healing Engine",
                target=dep_name,
                status="Success" if success else "Failed",
                duration="3s",
                incident_id=incident.id,
                organization_id=org_id,
                environment_id=env_id,
                connection_type=conn_type,
                details={"namespace": namespace, "result": msg, "environment_id": env_id},
            )
            return success, msg

        elif action == RemediationAction.NONE:
            return False, "No automated remediation action defined for this incident."

        else:
            return False, f"Unsupported action: {action.value}"


_remediation_service_instance: Optional[RemediationService] = None


def get_remediation_service() -> RemediationService:
    """Dependency provider for RemediationService."""
    global _remediation_service_instance
    if _remediation_service_instance is None:
        _remediation_service_instance = RemediationService()
    return _remediation_service_instance
