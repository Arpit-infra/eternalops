"""Organization domain models and schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    name: str = Field(..., description="Organization or tenant name")
    slug: str = Field(..., description="URL and identifier safe slug")
    description: Optional[str] = Field(None, description="Organization description")


class OrganizationCreate(OrganizationBase):
    pass


class Organization(OrganizationBase):
    id: str = Field(..., description="Unique organization identifier, e.g. org_default")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last updated timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata / config tags")


class OrganizationsListResponse(BaseModel):
    total: int = Field(..., description="Total organizations")
    organizations: List[Organization] = Field(..., description="List of organizations")
