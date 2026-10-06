"""Self-Healing API endpoints."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.schemas.incidents import Incident, IncidentActionResponse, IncidentStatus
from app.schemas.healing import HealingStatusResponse
from app.services.healing_orchestrator import HealingOrchestrator, get_healing_orchestrator
from app.services.incident_service import IncidentService, get_incident_service

logger = logging.getLogger("eternalops.api.healing")

router = APIRouter(prefix="/healing", tags=["Self-Healing Engine"])


@router.get("/status", response_model=HealingStatusResponse, summary="Get healing engine status")
def get_healing_status(
    incidents: IncidentService = Depends(get_incident_service),
    settings: Settings = Depends(get_settings),
) -> HealingStatusResponse:
    """Return status of self-healing engine, active operations, and recent healing history."""
    current = incidents.get_currently_healing()
    recent = incidents.get_recent_healed(limit=6)
    
    all_incs = incidents.list_incidents(limit=500)
    total_healed = all_incs.resolved_count
    total_escalated = all_incs.escalated_count

    return HealingStatusResponse(
        enabled=settings.HEALING_ENABLED,
        currently_healing=current,
        active_stage=current.healing_stage if current else None,
        recent_healed=recent,
        total_healed_count=total_healed,
        total_escalated_count=total_escalated,
    )


@router.get("/current", response_model=Optional[Incident], summary="Get currently healing incident")
def get_current_healing(
    incidents: IncidentService = Depends(get_incident_service),
) -> Optional[Incident]:
    """Return the active incident currently going through healing/verification."""
    return incidents.get_currently_healing()


@router.get("/history", response_model=List[Incident], summary="Get recent healing history")
def get_healing_history(
    limit: int = 10,
    incidents: IncidentService = Depends(get_incident_service),
) -> List[Incident]:
    """Return recently healed or escalated incidents."""
    return incidents.get_recent_healed(limit=limit)


@router.post("/run/{incident_id}", response_model=IncidentActionResponse, summary="Execute healing on an incident")
async def run_healing(
    incident_id: str,
    incidents: IncidentService = Depends(get_incident_service),
    orchestrator: HealingOrchestrator = Depends(get_healing_orchestrator),
) -> IncidentActionResponse:
    """Trigger the autonomous self-healing pipeline for a specific incident."""
    inc = incidents.get_by_id(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")

    updated = await orchestrator.run_healing_pipeline(inc)
    return IncidentActionResponse(
        success=updated.status == IncidentStatus.RESOLVED,
        incident=updated,
        message=f"Healing executed: status is {updated.status.value}",
    )
