"""Audit logging service and in-memory event store."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from app.schemas.audit import AuditLogItem, AuditLogsResponse

logger = logging.getLogger("eternalops.audit")


class AuditService:
    """Thread-safe in-memory audit log repository."""

    def __init__(self, max_entries: int = 500):
        self._logs: List[AuditLogItem] = []
        self._max_entries = max_entries

    def log(
        self,
        action: str,
        performed_by: str,
        target: str,
        status: str = "Success",
        duration: str = "—",
        cluster: str = "docker-desktop",
        incident_id: Optional[str] = None,
        organization_id: str = "org_default",
        environment_id: str = "env_local_dev",
        connection_type: Optional[str] = "local_kubernetes",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLogItem:
        """Create and store an audit log entry."""
        now = datetime.utcnow()
        ts_str = now.strftime("%H:%M:%S")
        entry_id = f"aud-{uuid.uuid4().hex[:8]}"

        item = AuditLogItem(
            id=entry_id,
            ts=ts_str,
            timestamp=now,
            action=action,
            performed_by=performed_by,
            target=target,
            cluster=cluster,
            duration=duration,
            status=status,
            incident_id=incident_id,
            organization_id=organization_id,
            environment_id=environment_id,
            connection_type=connection_type,
            details=details or {},
        )

        # Store most recent first
        self._logs.insert(0, item)
        if len(self._logs) > self._max_entries:
            self._logs.pop()

        logger.info(
            "[Audit] [%s] %s by %s on %s -> %s (%s)",
            ts_str,
            action,
            performed_by,
            target,
            status,
            duration,
        )
        return item

    def get_logs(
        self,
        limit: int = 100,
        status: Optional[str] = None,
        search: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> AuditLogsResponse:
        """Query audit logs with optional filtering."""
        results = list(self._logs)

        if incident_id:
            results = [r for r in results if r.incident_id == incident_id]

        if status and status.lower() != "all":
            results = [r for r in results if r.status.lower() == status.lower()]

        if search:
            query = search.lower().strip()
            results = [
                r
                for r in results
                if query in r.action.lower()
                or query in r.performed_by.lower()
                or query in r.target.lower()
                or query in r.cluster.lower()
                or (r.incident_id and query in r.incident_id.lower())
            ]

        limited = results[:limit]
        return AuditLogsResponse(total=len(results), logs=limited)

    def clear(self) -> None:
        """Clear all audit logs (for test isolation)."""
        self._logs.clear()


_audit_service_instance: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Dependency provider for singleton AuditService."""
    global _audit_service_instance
    if _audit_service_instance is None:
        _audit_service_instance = AuditService()
    return _audit_service_instance
