"""Incident management service and in-memory store."""

from datetime import datetime
import logging
from typing import Dict, List, Optional
import threading

from app.schemas.incidents import (
    HealingStage,
    Incident,
    IncidentCreate,
    IncidentSeverity,
    IncidentStatus,
    IncidentsListResponse,
    RemediationAction,
)
from app.services.audit_service import AuditService, get_audit_service
from app.services.notification_service import NotificationService, get_notification_service

logger = logging.getLogger("eternalops.incidents")


def format_duration(seconds: float) -> str:
    """Format seconds into readable string (e.g. 45s, 3m 12s)."""
    secs = int(round(seconds))
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    rem = secs % 60
    if rem == 0:
        return f"{mins}m"
    return f"{mins}m {rem}s"


class IncidentService:
    """Thread-safe in-memory incident repository and lifecycle manager."""

    def __init__(
        self,
        audit_service: Optional[AuditService] = None,
        notification_service: Optional[NotificationService] = None,
    ):
        self._incidents: Dict[str, Incident] = {}
        self._counter = 1000
        self._lock = threading.Lock()
        self._audit = audit_service or get_audit_service()
        self._notif = notification_service or get_notification_service()

    def _next_id(self) -> str:
        self._counter += 1
        return f"INC-{self._counter}"

    def create_incident(self, data: IncidentCreate) -> Incident:
        """Create a new incident and trigger initial audit log."""
        with self._lock:
            inc_id = self._next_id()
            fingerprint = data.fingerprint or f"{data.namespace}:{data.service}:{data.title}"
            now = datetime.utcnow()

            incident = Incident(
                id=inc_id,
                fingerprint=fingerprint,
                title=data.title,
                description=data.description,
                severity=data.severity,
                service=data.service,
                namespace=data.namespace,
                pod=data.pod,
                deployment=data.deployment,
                detection_source=data.detection_source,
                organization_id=data.organization_id or "org_default",
                environment_id=data.environment_id or "env_local_dev",
                status=IncidentStatus.OPEN,
                healing_stage=HealingStage.DETECTION,
                detected_at=now,
                updated_at=now,
                metrics=data.metrics,
                logs=data.logs,
                root_cause=None,
                confidence=None,
                recommended_action=None,
                selected_action=None,
                verification_status=None,
                error=None,
                escalated=False,
                escalation_reason=None,
            )
            self._incidents[inc_id] = incident

        target = data.pod or data.deployment or data.service
        logger.info("[Incident] Created %s: %s (Target: %s/%s) [Env: %s]", inc_id, data.title, data.namespace, target, incident.environment_id)

        self._audit.log(
            action=f"Incident detected: {data.title}",
            performed_by=f"Detection Engine ({data.detection_source})",
            target=target,
            status="Info",
            duration="—",
            incident_id=inc_id,
            organization_id=incident.organization_id,
            environment_id=incident.environment_id,
            details={"severity": data.severity.value, "namespace": data.namespace},
        )

        notif_type = "critical" if data.severity == IncidentSeverity.CRITICAL else "warning"
        self._notif.notify(
            title=f"Incident Detected ({inc_id})",
            message=f"[{incident.environment_id}] {data.title} in {data.namespace}",
            type_=notif_type,
            incident_id=inc_id,
            organization_id=incident.organization_id,
            environment_id=incident.environment_id,
        )

        return incident

    def get_by_id(self, incident_id: str) -> Optional[Incident]:
        """Fetch incident by unique ID."""
        return self._incidents.get(incident_id)

    def get_by_fingerprint(self, fingerprint: str) -> Optional[Incident]:
        """Find an active (non-resolved) incident matching an anomaly fingerprint."""
        for inc in self._incidents.values():
            if inc.fingerprint == fingerprint and inc.status not in (IncidentStatus.RESOLVED, IncidentStatus.FAILED):
                return inc
        return None

    def update_incident(self, incident: Incident) -> Incident:
        """Save updated incident object."""
        incident.updated_at = datetime.utcnow()
        self._incidents[incident.id] = incident
        return incident

    def set_stage(
        self,
        incident_id: str,
        stage: HealingStage,
        status: Optional[IncidentStatus] = None,
        error: Optional[str] = None,
        escalation_reason: Optional[str] = None,
    ) -> Optional[Incident]:
        """Transition an incident through healing stages and record lifecycle events."""
        with self._lock:
            inc = self._incidents.get(incident_id)
            if not inc:
                return None

            now = datetime.utcnow()
            inc.healing_stage = stage
            inc.updated_at = now

            if status:
                inc.status = status

            if stage == HealingStage.HEALING and inc.started_at is None:
                inc.started_at = now

            if stage == HealingStage.RESOLVED:
                inc.status = IncidentStatus.RESOLVED
                inc.resolved_at = now
                inc.error = None
                inc.escalated = False
                if inc.detected_at:
                    delta_sec = (now - inc.detected_at).total_seconds()
                    inc.recovery_seconds = round(delta_sec, 1)
                    inc.recovery_duration = format_duration(delta_sec)
                else:
                    inc.recovery_duration = "—"

            elif stage == HealingStage.ESCALATED:
                inc.status = IncidentStatus.ESCALATED
                inc.escalated = True
                inc.escalation_reason = escalation_reason or error or "Automatic remediation unavailable"
                if error:
                    inc.error = error

            if error:
                inc.error = error

            self._incidents[incident_id] = inc

        return inc

    def list_incidents(
        self,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> IncidentsListResponse:
        """List and filter incidents."""
        items = list(self._incidents.values())
        # Sort by detected_at descending (newest first)
        items.sort(key=lambda x: x.detected_at, reverse=True)

        if severity and severity.lower() != "all":
            items = [i for i in items if i.severity.value.lower() == severity.lower()]

        if status and status.lower() != "all":
            items = [i for i in items if i.status.value.lower() == status.lower()]

        if search:
            q = search.lower().strip()
            items = [
                i
                for i in items
                if q in i.id.lower()
                or q in i.title.lower()
                or q in i.service.lower()
                or (i.pod and q in i.pod.lower())
                or (i.deployment and q in i.deployment.lower())
                or (i.root_cause and q in i.root_cause.lower())
            ]

        all_items = list(self._incidents.values())
        active_count = sum(1 for i in all_items if i.status in (IncidentStatus.OPEN, IncidentStatus.ANALYZING, IncidentStatus.HEALING, IncidentStatus.VERIFYING))
        resolved_count = sum(1 for i in all_items if i.status == IncidentStatus.RESOLVED)
        escalated_count = sum(1 for i in all_items if i.status in (IncidentStatus.ESCALATED, IncidentStatus.FAILED))

        return IncidentsListResponse(
            total=len(items),
            active_count=active_count,
            resolved_count=resolved_count,
            escalated_count=escalated_count,
            incidents=items[:limit],
        )

    def get_currently_healing(self) -> Optional[Incident]:
        """Return the active incident currently in HEALING or VERIFYING stage."""
        for inc in self._incidents.values():
            if inc.status in (IncidentStatus.ANALYZING, IncidentStatus.HEALING, IncidentStatus.VERIFYING):
                return inc
        # Or an OPEN incident in progress
        for inc in self._incidents.values():
            if inc.status == IncidentStatus.OPEN:
                return inc
        return None

    def get_recent_healed(self, limit: int = 6) -> List[Incident]:
        """Return recently resolved or escalated incidents."""
        completed = [
            i
            for i in self._incidents.values()
            if i.status in (IncidentStatus.RESOLVED, IncidentStatus.ESCALATED, IncidentStatus.FAILED)
        ]
        completed.sort(key=lambda x: x.updated_at, reverse=True)
        return completed[:limit]

    def clear(self) -> None:
        """Reset incidents (for tests)."""
        with self._lock:
            self._incidents.clear()
            self._counter = 1000


_incident_service_instance: Optional[IncidentService] = None


def get_incident_service() -> IncidentService:
    """Dependency provider for singleton IncidentService."""
    global _incident_service_instance
    if _incident_service_instance is None:
        _incident_service_instance = IncidentService()
    return _incident_service_instance
