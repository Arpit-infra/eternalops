"""Central API router registry."""

from fastapi import APIRouter
from app.api.routes import (
    agent,
    ai,
    audit,
    environments,
    healing,
    health,
    incidents,
    kubernetes,
    notifications,
    prometheus,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router)
api_router.include_router(audit.router)
# Backward-compatibility alias for GET /api/audit
audit_alias_router = APIRouter(prefix="/audit", tags=["Audit Logs Alias"])
audit_alias_router.add_api_route("", audit.get_audit_logs, methods=["GET"], response_model=audit.AuditLogsResponse, summary="Query audit logs (alias)")
api_router.include_router(audit_alias_router)
api_router.include_router(environments.router)

api_router.include_router(agent.router)
api_router.include_router(prometheus.router)
api_router.include_router(kubernetes.router)
api_router.include_router(incidents.router)
api_router.include_router(healing.router)
api_router.include_router(audit.router)
api_router.include_router(notifications.router)
api_router.include_router(ai.router)
