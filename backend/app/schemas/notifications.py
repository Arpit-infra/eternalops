"""Notification schemas."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    id: str = Field(..., description="Unique notification ID")
    title: str = Field(..., description="Short notification title")
    message: str = Field(..., description="Notification detail message")
    type: str = Field("info", description="Severity / category: info, warning, critical, success, heal, escalate")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp created")
    time_str: str = Field(..., description="Formatted time string")
    read: bool = Field(False, description="Read state")
    incident_id: Optional[str] = Field(None, description="Linked incident ID")
    organization_id: str = Field("org_default", description="Associated organization ID")
    environment_id: str = Field("env_local_dev", description="Associated environment ID")


class NotificationsResponse(BaseModel):
    total: int
    unread_count: int
    notifications: List[NotificationItem]
