"""Self-healing schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.schemas.incidents import Incident, HealingStage


class HealingStepInfo(BaseModel):
    label: str
    desc: str
    status: str  # done, active, pending, failed


class HealingStatusResponse(BaseModel):
    enabled: bool = Field(..., description="Whether self-healing engine is globally active")
    currently_healing: Optional[Incident] = Field(None, description="Active healing incident if any")
    active_stage: Optional[HealingStage] = Field(None, description="Current workflow stage")
    recent_healed: List[Incident] = Field(default_factory=list, description="Recently healed or escalated incidents")
    total_healed_count: int = Field(0, description="Total incidents resolved by engine")
    total_escalated_count: int = Field(0, description="Total incidents escalated to humans")


class HealingRunRequest(BaseModel):
    incident_id: str = Field(..., description="ID of incident to heal")
    force: bool = Field(False, description="Bypass human confirmation check")
