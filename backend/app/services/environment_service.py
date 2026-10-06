"""Environment Service & Registry for Managing Multi-Tenant Infrastructure Environments."""

from datetime import datetime
import logging
from typing import Dict, List, Optional
import threading
import uuid

from app.core.config import Settings, get_settings
from app.schemas.environments import (
    ConnectionType,
    Environment,
    EnvironmentCapabilities,
    EnvironmentCreate,
    EnvironmentHealthResponse,
    EnvironmentPlatform,
    EnvironmentProvider,
    EnvironmentStatus,
    EnvironmentUpdate,
    EnvironmentsListResponse,
)
from app.schemas.organizations import Organization, OrganizationCreate, OrganizationsListResponse
from app.services.agent_service import AgentService, get_agent_service
from app.services.connections.connection_manager import ConnectionManager, get_connection_manager

logger = logging.getLogger("eternalops.environment_service")


class EnvironmentService:
    """
    Manages registration, lifecycle, status, and health checks across all customer & local environments.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        connection_manager: Optional[ConnectionManager] = None,
        agent_service: Optional[AgentService] = None,
    ):
        self._settings = settings or get_settings()
        self._conn_mgr = connection_manager or get_connection_manager()
        self._agent_svc = agent_service or get_agent_service()
        self._conn_mgr.register_agent_connector(self._agent_svc)

        self._lock = threading.Lock()
        self._organizations: Dict[str, Organization] = {}
        self._environments: Dict[str, Environment] = {}

        self._seed_defaults()

    def _seed_defaults(self) -> None:
        """Initialize the default Organization and Local Development Environment."""
        default_org_id = self._settings.DEFAULT_ORGANIZATION_ID
        default_org_name = self._settings.DEFAULT_ORGANIZATION_NAME
        default_env_id = self._settings.DEFAULT_ENVIRONMENT_ID
        default_env_name = self._settings.DEFAULT_ENVIRONMENT_NAME

        now = datetime.utcnow()

        # Seed Default Organization
        org = Organization(
            id=default_org_id,
            name=default_org_name,
            slug="eternalops-dev",
            description="Primary organization for EternalOps local development and verification",
            created_at=now,
            updated_at=now,
            metadata={"tier": "developer", "managed": True},
        )
        self._organizations[default_org_id] = org

        # Seed Default Local Environment (Docker Desktop Kubernetes)
        env = Environment(
            id=default_env_id,
            name=default_env_name,
            description="Local Docker Desktop Kubernetes cluster",
            provider=EnvironmentProvider.DOCKER_DESKTOP,
            platform=EnvironmentPlatform.KUBERNETES,
            connection_type=ConnectionType.LOCAL_KUBERNETES,
            organization_id=default_org_id,
            status=EnvironmentStatus.CONNECTED,
            last_seen=now,
            last_heartbeat=now,
            capabilities=EnvironmentCapabilities(
                can_read_kubernetes=True,
                can_read_metrics=True,
                can_restart_pod=True,
                can_restart_deployment=True,
                can_scale_deployment=True,
                can_verify_workload=True,
            ),
            metadata={
                "cluster_context": self._settings.KUBERNETES_CONTEXT or "docker-desktop",
                "prometheus_url": self._settings.PROMETHEUS_URL,
                "is_default": True,
            },
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        self._environments[default_env_id] = env
        logger.info("[EnvironmentService] Initialized default organization '%s' and environment '%s'", default_org_id, default_env_id)

        # Seed Default Agent Demo Environment
        agent_env_id = "env_agent_demo"
        agent_env = Environment(
            id=agent_env_id,
            name="Agent Demo Environment",
            description="Edge agent managed Kubernetes demo cluster",
            provider=EnvironmentProvider.CUSTOM,
            platform=EnvironmentPlatform.KUBERNETES,
            connection_type=ConnectionType.AGENT,
            organization_id=default_org_id,
            status=EnvironmentStatus.OFFLINE,
            last_seen=None,
            last_heartbeat=None,
            capabilities=EnvironmentCapabilities(
                can_read_kubernetes=True,
                can_read_metrics=False,
                can_restart_pod=True,
                can_restart_deployment=True,
                can_scale_deployment=False,
                can_verify_workload=True,
            ),
            metadata={
                "cluster_name": "docker-desktop-agent-cluster",
                "namespace": "eternalops-agent-demo",
            },
            error_message="Target connection unreachable",
            created_at=now,
            updated_at=now,
        )
        self._environments[agent_env_id] = agent_env
        logger.info("[EnvironmentService] Initialized agent demo environment '%s'", agent_env_id)

    # ---------------- Organization Operations ---------------- #

    def list_organizations(self) -> OrganizationsListResponse:
        orgs = list(self._organizations.values())
        return OrganizationsListResponse(total=len(orgs), organizations=orgs)

    def get_organization(self, org_id: str) -> Optional[Organization]:
        return self._organizations.get(org_id)

    def create_organization(self, data: OrganizationCreate) -> Organization:
        with self._lock:
            org_id = f"org_{uuid.uuid4().hex[:8]}"
            now = datetime.utcnow()
            org = Organization(
                id=org_id,
                name=data.name,
                slug=data.slug,
                description=data.description,
                created_at=now,
                updated_at=now,
                metadata={},
            )
            self._organizations[org_id] = org
            return org

    # ---------------- Environment Operations ---------------- #

    def list_environments(
        self,
        organization_id: Optional[str] = None,
        provider: Optional[str] = None,
        status: Optional[str] = None,
    ) -> EnvironmentsListResponse:
        """List registered environments with dynamic health evaluation."""
        with self._lock:
            envs = list(self._environments.values())

        # Update dynamic statuses before returning
        for env in envs:
            self._refresh_environment_status(env)

        if organization_id:
            envs = [e for e in envs if e.organization_id == organization_id]
        if provider:
            envs = [e for e in envs if e.provider.value == provider]
        if status:
            envs = [e for e in envs if e.status.value == status]

        return EnvironmentsListResponse(total=len(envs), environments=envs)

    def get_environment(self, environment_id: str) -> Optional[Environment]:
        """Fetch environment by ID and refresh health."""
        env = self._environments.get(environment_id)
        if env:
            self._refresh_environment_status(env)
        return env

    def create_environment(self, data: EnvironmentCreate) -> Environment:
        """Register a new customer or development environment."""
        with self._lock:
            env_id = f"env_{uuid.uuid4().hex[:8]}"
            now = datetime.utcnow()
            env = Environment(
                id=env_id,
                name=data.name,
                description=data.description,
                provider=data.provider,
                platform=data.platform,
                connection_type=data.connection_type,
                organization_id=data.organization_id or self._settings.DEFAULT_ORGANIZATION_ID,
                status=EnvironmentStatus.CONNECTED if data.connection_type == ConnectionType.LOCAL_KUBERNETES else EnvironmentStatus.UNKNOWN,
                last_seen=now,
                last_heartbeat=now,
                capabilities=data.capabilities or EnvironmentCapabilities(),
                metadata=data.metadata or {},
                error_message=None,
                created_at=now,
                updated_at=now,
            )
            self._environments[env_id] = env
            logger.info("[EnvironmentService] Registered new environment %s (%s)", env_id, env.name)
            return env

    def update_environment(self, environment_id: str, data: EnvironmentUpdate) -> Optional[Environment]:
        """Update mutable configuration on an environment."""
        with self._lock:
            env = self._environments.get(environment_id)
            if not env:
                return None

            if data.name is not None:
                env.name = data.name
            if data.description is not None:
                env.description = data.description
            if data.provider is not None:
                env.provider = data.provider
            if data.platform is not None:
                env.platform = data.platform
            if data.connection_type is not None:
                env.connection_type = data.connection_type
            if data.capabilities is not None:
                env.capabilities = data.capabilities
            if data.metadata is not None:
                env.metadata.update(data.metadata)

            env.updated_at = datetime.utcnow()
            self._environments[environment_id] = env
            return env

    def delete_environment(self, environment_id: str) -> bool:
        """Delete an environment (protecting the default local development environment)."""
        if environment_id == self._settings.DEFAULT_ENVIRONMENT_ID:
            logger.warning("[EnvironmentService] Cannot delete default environment '%s'", environment_id)
            return False

        with self._lock:
            if environment_id in self._environments:
                del self._environments[environment_id]
                self._conn_mgr.remove_connection(environment_id)
                logger.info("[EnvironmentService] Deleted environment '%s'", environment_id)
                return True
            return False

    def get_environment_health(self, environment_id: str) -> EnvironmentHealthResponse:
        """Probe real connection health for an environment."""
        env = self.get_environment(environment_id)
        if not env:
            return EnvironmentHealthResponse(
                environment_id=environment_id,
                status=EnvironmentStatus.OFFLINE,
                connected=False,
                last_heartbeat=None,
                error="Environment not found.",
            )

        conn = self._conn_mgr.get_connection(environment_id=env.id, environment_meta=env)
        health_info = conn.health_check()
        is_connected = conn.is_connected()

        status = EnvironmentStatus.CONNECTED if is_connected else EnvironmentStatus.OFFLINE

        return EnvironmentHealthResponse(
            environment_id=env.id,
            status=status,
            connected=is_connected,
            last_heartbeat=env.last_heartbeat,
            latency_ms=health_info.get("latency_ms"),
            details=health_info,
            error=health_info.get("error"),
        )

    def _refresh_environment_status(self, env: Environment) -> None:
        """Evaluate real status of an environment using its connection abstraction."""
        try:
            conn = self._conn_mgr.get_connection(environment_id=env.id, environment_meta=env)
            if conn.is_connected():
                env.status = EnvironmentStatus.CONNECTED
                env.error_message = None
                env.last_seen = datetime.utcnow()
            else:
                env.status = EnvironmentStatus.OFFLINE
                health = conn.health_check()
                env.error_message = health.get("error", "Target connection unreachable")
        except Exception as exc:
            env.status = EnvironmentStatus.OFFLINE
            env.error_message = str(exc)


_environment_service_instance: Optional[EnvironmentService] = None


def get_environment_service() -> EnvironmentService:
    global _environment_service_instance
    if _environment_service_instance is None:
        _environment_service_instance = EnvironmentService()
    return _environment_service_instance
