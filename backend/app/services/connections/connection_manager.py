"""Connection Manager resolving organization + environment into active EnvironmentConnection."""

import logging
from typing import Dict, Optional

from app.core.config import Settings, get_settings
from app.schemas.environments import ConnectionType, Environment
from app.services.connections.base import EnvironmentConnection
from app.services.connections.local_kubernetes import LocalKubernetesConnection
from app.services.kubernetes_service import KubernetesService, get_kubernetes_service

logger = logging.getLogger("eternalops.connection_manager")


class ConnectionManager:
    """
    Resolves environment IDs into live EnvironmentConnection instances.
    Provides centralized routing so the healing engine and APIs never hardcode cluster targets.
    """

    def __init__(
        self,
        k8s_service: Optional[KubernetesService] = None,
        settings: Optional[Settings] = None,
        agent_service: Optional[object] = None,
    ):
        self._k8s = k8s_service or get_kubernetes_service()
        self._settings = settings or get_settings()
        self._connections: Dict[str, EnvironmentConnection] = {}
        if agent_service is not None:
            self._agent_connector = agent_service
        else:
            from app.services.agent_service import get_agent_service
            self._agent_connector = get_agent_service()

    def register_agent_connector(self, connector: object) -> None:
        """Register the agent connector service instance."""
        self._agent_connector = connector

    def get_connection(self, environment_id: str, environment_meta: Optional[Environment] = None) -> EnvironmentConnection:
        """
        Resolve an environment ID to its corresponding EnvironmentConnection instance.
        """
        # Return cached instance if available
        if environment_id in self._connections:
            return self._connections[environment_id]

        conn_type = None
        if environment_meta:
            conn_type = environment_meta.connection_type

        # Default local dev environment
        if environment_id == self._settings.DEFAULT_ENVIRONMENT_ID or conn_type == ConnectionType.LOCAL_KUBERNETES:
            conn = LocalKubernetesConnection(environment_id=environment_id, k8s_service=self._k8s)
            self._connections[environment_id] = conn
            return conn

        # Remote agent environment
        if conn_type == ConnectionType.AGENT or conn_type == "agent":
            from app.services.connections.agent_connection import AgentConnection
            conn = AgentConnection(environment_id=environment_id, agent_connector_service=self._agent_connector)
            self._connections[environment_id] = conn
            return conn

        # Explicit check if this is an agent or unknown environment
        from app.services.connections.agent_connection import AgentConnection
        conn = AgentConnection(environment_id=environment_id, agent_connector_service=self._agent_connector)
        self._connections[environment_id] = conn
        return conn

    def set_connection(self, environment_id: str, connection: EnvironmentConnection) -> None:
        """Explicitly inject or override connection for an environment (useful in testing/mocking)."""
        self._connections[environment_id] = connection

    def remove_connection(self, environment_id: str) -> None:
        """Remove connection on environment deletion."""
        self._connections.pop(environment_id, None)


_connection_manager_instance: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Dependency provider for singleton ConnectionManager."""
    global _connection_manager_instance
    if _connection_manager_instance is None:
        _connection_manager_instance = ConnectionManager()
    return _connection_manager_instance
