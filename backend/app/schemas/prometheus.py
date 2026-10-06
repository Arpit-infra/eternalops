"""Prometheus response and request schemas."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class PrometheusStatusResponse(BaseModel):
    """Status response for Prometheus connectivity."""

    available: bool = Field(..., description="Whether Prometheus is reachable")
    url: str = Field(..., description="Configured Prometheus base URL")
    status: str = Field(..., description="Connection status message")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")


class PrometheusQueryResponse(BaseModel):
    """Raw response proxy from Prometheus query API."""

    status: str = Field(..., description="Prometheus status ('success' or 'error')")
    data: Optional[Any] = Field(default=None, description="Prometheus query result payload")
    errorType: Optional[str] = Field(default=None, description="Error type if query failed")
    error: Optional[str] = Field(default=None, description="Error description if query failed")
    warnings: Optional[List[str]] = Field(default=None, description="Any query warnings")
