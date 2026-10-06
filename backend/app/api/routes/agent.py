"""Agent Communication API Routes."""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.schemas.agent import (
    AgentCommand,
    AgentCommandResult,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
)
from app.services.agent_service import AgentService, get_agent_service

logger = logging.getLogger("eternalops.api.agent")

router = APIRouter(prefix="/agent", tags=["Edge Agent Protocol"])


@router.post("/register", response_model=AgentRegistrationResponse, summary="Register Edge Agent")
def register_agent(
    req: AgentRegistrationRequest,
    service: AgentService = Depends(get_agent_service),
):
    """
    Called by remote EternalOps edge agent during initial bootstrap.
    Validates enrollment token and returns a secure session token.
    """
    res = service.register_agent(req)
    if not res.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=res.message,
        )
    return res


@router.post("/heartbeat", response_model=AgentHeartbeatResponse, summary="Agent Heartbeat")
def agent_heartbeat(
    req: AgentHeartbeatRequest,
    service: AgentService = Depends(get_agent_service),
):
    """
    Periodic heartbeat from edge agent reporting operational status and cluster connectivity.
    """
    res = service.process_heartbeat(req)
    if not res.acknowledged:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent heartbeat rejected: invalid session or environment.",
        )
    return res


@router.get("/commands", response_model=List[AgentCommand], summary="Poll pending commands")
def poll_commands(
    environment_id: str,
    authorization: Optional[str] = Header(None),
    service: AgentService = Depends(get_agent_service),
):
    """
    Agent polls for pending allowlisted commands (e.g. restart pod).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Bearer token.")

    token = authorization.split(" ")[1]
    return service.poll_commands(environment_id=environment_id, session_token=token)


@router.post("/commands/{command_id}/result", summary="Submit command execution result")
def submit_command_result(
    command_id: str,
    result: AgentCommandResult,
    service: AgentService = Depends(get_agent_service),
):
    """
    Agent reports output and status of an executed allowlisted command.
    """
    if result.command_id != command_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Command ID mismatch.")

    success = service.record_command_result(result)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown environment or command.")
    return {"acknowledged": True}
