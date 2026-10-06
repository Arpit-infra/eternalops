"""Verification Service for confirming post-remediation health across connected environments."""

import asyncio
import logging
from typing import Optional, Tuple

from app.core.config import Settings, get_settings
from app.schemas.incidents import Incident, RemediationAction
from app.services.audit_service import AuditService, get_audit_service
from app.services.connections.connection_manager import ConnectionManager, get_connection_manager

logger = logging.getLogger("eternalops.verification")


class VerificationService:
    """Verifies that remediated workloads reach a healthy, stable state in their target environment."""

    def __init__(
        self,
        connection_manager: Optional[ConnectionManager] = None,
        audit_service: Optional[AuditService] = None,
        settings: Optional[Settings] = None,
    ):
        self.conn_mgr = connection_manager or get_connection_manager()
        self.audit = audit_service or get_audit_service()
        self.settings = settings or get_settings()

    async def verify_remediation(
        self,
        incident: Incident,
        timeout_seconds: Optional[float] = None,
        poll_interval: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Poll target environment connection to verify workload recovery after healing action.
        Returns: (verified, message)
        """
        timeout = timeout_seconds or self.settings.VERIFICATION_TIMEOUT_SECONDS
        interval = poll_interval or self.settings.VERIFICATION_POLL_INTERVAL_SECONDS
        action = incident.recommended_action
        target = incident.pod or incident.deployment or incident.service
        namespace = incident.namespace or "default"
        env_id = incident.environment_id or "env_local_dev"
        org_id = incident.organization_id or "org_default"

        logger.info(
            "[Verification] Starting verification for %s (%s/%s) in Environment '%s' - timeout %ss",
            incident.id,
            namespace,
            target,
            env_id,
            timeout,
        )

        try:
            conn = self.conn_mgr.get_connection(environment_id=env_id)
        except Exception as exc:
            msg = f"Cannot verify: Failed to resolve connection for environment '{env_id}': {str(exc)}"
            return False, msg

        elapsed = 0.0

        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval

            try:
                if action == RemediationAction.ROLLOUT_RESTART_DEPLOYMENT or incident.deployment:
                    dep_name = incident.deployment or incident.service
                    dep = conn.get_deployment(namespace=namespace, name=dep_name)
                    if dep:
                        desired = dep.desired_replicas
                        avail = dep.available_replicas
                        ready = dep.ready_replicas
                        if desired > 0 and avail >= desired and ready >= desired:
                            msg = f"Deployment {dep_name} verified: {avail}/{desired} replicas available and ready."
                            logger.info("[Verification] SUCCESS for %s: %s", incident.id, msg)
                            self.audit.log(
                                action="Verification completed: Metrics confirmed stable",
                                performed_by="Verification Engine",
                                target=dep_name,
                                status="Success",
                                duration=f"{int(elapsed)}s",
                                incident_id=incident.id,
                                organization_id=org_id,
                                environment_id=env_id,
                                connection_type=getattr(conn, "connection_type", "unknown"),
                                details={"replicas": f"{avail}/{desired}", "elapsed_seconds": elapsed},
                            )
                            return True, msg

                # Check pod or general service pods
                pods_resp = conn.list_pods(namespace=namespace)
                if pods_resp.available and pods_resp.pods:
                    matching = [
                        p
                        for p in pods_resp.pods
                        if (incident.pod and p.name == incident.pod)
                        or (incident.service and incident.service in p.name)
                        or (incident.deployment and incident.deployment in p.name)
                    ]

                    if matching:
                        all_healthy = True
                        for p in matching:
                            if p.phase != "Running":
                                all_healthy = False
                                break
                            # Check container readiness
                            if p.containers and not all(c.ready for c in p.containers):
                                all_healthy = False
                                break

                        if all_healthy:
                            msg = f"All {len(matching)} target pod(s) running and containers ready."
                            logger.info("[Verification] SUCCESS for %s: %s", incident.id, msg)
                            self.audit.log(
                                action="Verification completed: Metrics confirmed stable",
                                performed_by="Verification Engine",
                                target=target,
                                status="Success",
                                duration=f"{int(elapsed)}s",
                                incident_id=incident.id,
                                organization_id=org_id,
                                environment_id=env_id,
                                connection_type=getattr(conn, "connection_type", "unknown"),
                                details={"healthy_pods": len(matching), "elapsed_seconds": elapsed},
                            )
                            return True, msg

            except Exception as exc:
                logger.warning("[Verification] Error querying status for %s: %s", incident.id, str(exc))

        # Timeout reached without confirmation
        fail_msg = f"Workload {namespace}/{target} did not reach ready status within {int(timeout)}s."
        logger.warning("[Verification] FAILED for %s: %s", incident.id, fail_msg)
        self.audit.log(
            action="Verification failed: Metrics remained unstable",
            performed_by="Verification Engine",
            target=target,
            status="Failed",
            duration=f"{int(timeout)}s",
            incident_id=incident.id,
            organization_id=org_id,
            environment_id=env_id,
            connection_type=getattr(conn, "connection_type", "unknown"),
            details={"reason": fail_msg},
        )
        return False, fail_msg


_verification_service_instance: Optional[VerificationService] = None


def get_verification_service() -> VerificationService:
    """Dependency provider for VerificationService."""
    global _verification_service_instance
    if _verification_service_instance is None:
        _verification_service_instance = VerificationService()
    return _verification_service_instance
