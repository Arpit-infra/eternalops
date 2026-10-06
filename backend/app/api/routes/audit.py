"""Audit log API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.schemas.audit import AuditLogsResponse
from app.services.audit_service import AuditService, get_audit_service

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditLogsResponse, summary="Query audit logs")
def get_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, description="Filter by status: all, Success, Failed, Escalated"),
    search: Optional[str] = Query(None, description="Search keyword"),
    incident_id: Optional[str] = Query(None, description="Filter by linked incident ID"),
    service: AuditService = Depends(get_audit_service),
) -> AuditLogsResponse:
    """Retrieve audit log records."""
    return service.get_logs(limit=limit, status=status, search=search, incident_id=incident_id)
