"""Environment & Organization API routes for Control Plane."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.environments import (
    Environment,
    EnvironmentCreate,
    EnvironmentEnrollmentToken,
    EnvironmentHealthResponse,
    EnvironmentUpdate,
    EnvironmentsListResponse,
)
from app.schemas.organizations import (
    Organization,
    OrganizationCreate,
    OrganizationsListResponse,
)
from app.services.agent_service import AgentService, get_agent_service
from app.services.environment_service import EnvironmentService, get_environment_service

logger = logging.getLogger("eternalops.api.environments")

router = APIRouter(prefix="/environments", tags=["Environments & Organizations"])


@router.get("", response_model=EnvironmentsListResponse, summary="List all registered environments")
def list_environments(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    provider: Optional[str] = Query(None, description="Filter by provider (e.g. docker-desktop)"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by connectivity status"),
    service: EnvironmentService = Depends(get_environment_service),
):
    """Retrieve all managed infrastructure environments."""
    return service.list_environments(organization_id=organization_id, provider=provider, status=status_filter)


@router.post("", response_model=Environment, status_code=status.HTTP_201_CREATED, summary="Register a new environment")
def create_environment(
    data: EnvironmentCreate,
    service: EnvironmentService = Depends(get_environment_service),
):
    """Register a new customer or development environment in the control plane."""
    return service.create_environment(data)


@router.get("/organizations", response_model=OrganizationsListResponse, summary="List organizations")
def list_organizations(
    service: EnvironmentService = Depends(get_environment_service),
):
    """List all organizations / tenants."""
    return service.list_organizations()


@router.post("/organizations", response_model=Organization, status_code=status.HTTP_201_CREATED, summary="Create an organization")
def create_organization(
    data: OrganizationCreate,
    service: EnvironmentService = Depends(get_environment_service),
):
    """Create a new tenant organization."""
    return service.create_organization(data)


@router.get("/{environment_id}", response_model=Environment, summary="Get environment details")
def get_environment(
    environment_id: str,
    service: EnvironmentService = Depends(get_environment_service),
):
    """Retrieve details and capabilities of a specific environment."""
    env = service.get_environment(environment_id)
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Environment '{environment_id}' not found.")
    return env


@router.patch("/{environment_id}", response_model=Environment, summary="Update environment metadata")
def update_environment(
    environment_id: str,
    data: EnvironmentUpdate,
    service: EnvironmentService = Depends(get_environment_service),
):
    """Update settings or metadata for an environment."""
    env = service.update_environment(environment_id, data)
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Environment '{environment_id}' not found.")
    return env


@router.delete("/{environment_id}", summary="Delete an environment")
def delete_environment(
    environment_id: str,
    service: EnvironmentService = Depends(get_environment_service),
):
    """Unregister an environment."""
    success = service.delete_environment(environment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete environment '{environment_id}' (default local dev environment is protected or ID is invalid).",
        )
    return {"success": True, "message": f"Environment '{environment_id}' deleted."}


@router.get("/{environment_id}/status", response_model=Environment, summary="Get current environment status")
def get_environment_status(
    environment_id: str,
    service: EnvironmentService = Depends(get_environment_service),
):
    """Get live connectivity status for an environment."""
    env = service.get_environment(environment_id)
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Environment '{environment_id}' not found.")
    return env


@router.get("/{environment_id}/health", response_model=EnvironmentHealthResponse, summary="Probe environment health")
def get_environment_health(
    environment_id: str,
    service: EnvironmentService = Depends(get_environment_service),
):
    """Execute active health probe on an environment's connection adapter."""
    return service.get_environment_health(environment_id)


@router.post("/{environment_id}/token", response_model=EnvironmentEnrollmentToken, summary="Generate agent enrollment token")
def generate_agent_token(
    environment_id: str,
    env_service: EnvironmentService = Depends(get_environment_service),
    agent_service: AgentService = Depends(get_agent_service),
):
    """Generate a secure one-time enrollment token for connecting an EternalOps Edge Agent."""
    env = env_service.get_environment(environment_id)
    if not env:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Environment '{environment_id}' not found.")

    token = agent_service.generate_enrollment_token(environment_id)
    return EnvironmentEnrollmentToken(
        environment_id=environment_id,
        enrollment_token=token,
        expires_at=agent_service._enrollment_tokens[token]["expires_at"],
        instructions="Deploy EternalOps agent in target cluster with this enrollment token to establish outbound connection.",
    )
