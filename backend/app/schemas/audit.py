"""Audit log domain models and schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditLogItem(BaseModel):
    id: str = Field(..., description="Unique audit event ID")
    ts: str = Field(..., description="Formatted timestamp HH:MM:SS")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="ISO timestamp")
    action: str = Field(..., description="Action performed, e.g. 'Pod restarted'")
    performed_by: str = Field(..., description="Actor, e.g. 'Healing Engine', 'Detection Engine'")
    target: str = Field(..., description="Target workload or resource, e.g. 'auth-svc-7f9c'")
    cluster: str = Field("docker-desktop", description="Target cluster context")
    duration: str = Field("—", description="Action duration e.g. '12s'")
    status: str = Field("Success", description="Outcome status: Success, Failed, Escalated, Info")
    incident_id: Optional[str] = Field(None, description="Linked incident ID if any")
    organization_id: str = Field("org_default", description="Associated organization ID")
    environment_id: str = Field("env_local_dev", description="Associated environment ID")
    connection_type: Optional[str] = Field("local_kubernetes", description="Connection type used for the action")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Extra metadata")


class AuditLogsResponse(BaseModel):
    total: int = Field(..., description="Total audit log entries")
    logs: List[AuditLogItem] = Field(..., description="List of audit logs")
