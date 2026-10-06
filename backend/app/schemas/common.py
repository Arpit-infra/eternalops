"""Common API schemas."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ServiceHealthItem(BaseModel):
    """Health item status for a service integration."""

    available: bool = Field(..., description="Whether the integration is currently reachable")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional status details")


class HealthResponse(BaseModel):
    """Overall backend health check response schema."""

    status: str = Field(default="ok", description="Overall service status")
    service: str = Field(default="eternalops-backend", description="Service identifier")
    prometheus: ServiceHealthItem = Field(..., description="Prometheus integration status")
    kubernetes: ServiceHealthItem = Field(..., description="Kubernetes integration status")


class RootResponse(BaseModel):
    """Root endpoint response schema."""

    name: str
    version: str
    docs_url: str = "/docs"
    health_url: str = "/api/health"
