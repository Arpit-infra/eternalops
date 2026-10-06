"""Agent Connection Adapter for remote customer clusters connecting via EternalOps Agent."""

from typing import Any, Dict, Optional, Tuple

from app.schemas.agent import AgentActionType, AgentCommand
from app.schemas.kubernetes import (
    ClusterInfoResponse,
    DeploymentItem,
    DeploymentsResponse,
    NamespacesResponse,
    NodesResponse,
    PodItem,
    PodsResponse,
    ServicesResponse,
)
from app.services.connections.base import EnvironmentConnection


class AgentConnection(EnvironmentConnection):
    """
    Adapter communicating with an active edge agent for remote customer environments.
    Translates operations into explicit, allowlisted AgentCommand actions.
    """

    def __init__(
        self,
        environment_id: str,
        agent_connector_service: Any = None,
    ):
        self._environment_id = environment_id
        self._connector = agent_connector_service

    @property
    def environment_id(self) -> str:
        return self._environment_id

    @property
    def connection_type(self) -> str:
        return "agent"

    def _get_connector(self) -> Any:
        if self._connector:
            return self._connector
        from app.services.agent_service import get_agent_service
        return get_agent_service()

    def is_connected(self) -> bool:
        connector = self._get_connector()
        if connector:
            return connector.is_agent_connected(self._environment_id)
        return False

    def health_check(self) -> Dict[str, Any]:
        connector = self._get_connector()
        if connector:
            return connector.get_agent_health(self._environment_id)
        return {
            "available": False,
            "error": "Agent connector service not initialized",
        }

    def get_cluster_info(self) -> ClusterInfoResponse:
        if not self.is_connected():
            return ClusterInfoResponse(
                available=False,
                error=f"Agent for environment '{self._environment_id}' is offline or not registered.",
            )
        connector = self._get_connector()
        if connector:
            meta = connector.get_agent_metadata(self._environment_id)
            return ClusterInfoResponse(
                available=True,
                git_version=meta.get("kubernetes_version", "unknown"),
                platform=meta.get("cluster_name", "remote-agent"),
            )
        return ClusterInfoResponse(available=False, error="No agent connection")

    def list_namespaces(self) -> NamespacesResponse:
        if not self.is_connected():
            return NamespacesResponse(available=False, total=0, namespaces=[], error="Agent offline")
        return NamespacesResponse(available=True, total=0, namespaces=[], error=None)

    def list_nodes(self) -> NodesResponse:
        if not self.is_connected():
            return NodesResponse(available=False, total=0, nodes=[], error="Agent offline")
        return NodesResponse(available=True, total=0, nodes=[], error=None)

    def list_pods(self, namespace: Optional[str] = None) -> PodsResponse:
        if not self.is_connected():
            return PodsResponse(available=False, total=0, pods=[], error="Agent offline")
        
        target_ns = namespace or "eternalops-agent-demo"
        pod_name = "agent-target-workload"
        connector = self._get_connector()
        mock_data = connector.get_mock_workload(self._environment_id, target_ns, pod_name, is_deployment=False) if connector else None
        
        phase = mock_data.get("phase", "Running") if mock_data else "Running"
        ready = mock_data.get("ready", True) if mock_data else True
        restart_count = mock_data.get("restart_count", 0) if mock_data else 0

        from app.schemas.kubernetes import PodContainerStatus
        return PodsResponse(
            available=True,
            total=1,
            pods=[
                PodItem(
                    name=pod_name,
                    namespace=target_ns,
                    phase=phase,
                    ready=ready,
                    restart_count=restart_count,
                    containers=[PodContainerStatus(name="web", ready=ready, restart_count=restart_count, state="running" if ready else "not_ready")],
                )
            ],
            error=None,
        )

    def get_pod(self, namespace: str, name: str) -> Optional[PodItem]:
        if not self.is_connected():
            return None
        connector = self._get_connector()
        mock_data = connector.get_mock_workload(self._environment_id, namespace, name, is_deployment=False) if connector else None
        
        phase = mock_data.get("phase", "Running") if mock_data else "Running"
        ready = mock_data.get("ready", True) if mock_data else True
        restart_count = mock_data.get("restart_count", 0) if mock_data else 0

        from app.schemas.kubernetes import PodContainerStatus
        return PodItem(
            name=name,
            namespace=namespace,
            phase=phase,
            ready=ready,
            restart_count=restart_count,
            containers=[PodContainerStatus(name="web", ready=ready, restart_count=restart_count, state="running" if ready else "not_ready")],
        )


    def list_deployments(self, namespace: Optional[str] = None) -> DeploymentsResponse:
        if not self.is_connected():
            return DeploymentsResponse(available=False, total=0, deployments=[], error="Agent offline")
        
        target_ns = namespace or "eternalops-agent-demo"
        dep_name = "agent-target-workload"
        connector = self._get_connector()
        mock_data = connector.get_mock_workload(self._environment_id, target_ns, dep_name, is_deployment=True) if connector else None
        
        desired = mock_data.get("desired_replicas", 1) if mock_data else 1
        ready = mock_data.get("ready_replicas", 1) if mock_data else 1
        avail = mock_data.get("available_replicas", 1) if mock_data else 1

        return DeploymentsResponse(
            available=True,
            total=1,
            deployments=[
                DeploymentItem(
                    name=dep_name,
                    namespace=target_ns,
                    desired_replicas=desired,
                    ready_replicas=ready,
                    available_replicas=avail,
                    updated_replicas=ready,
                    conditions=["Available", "Progressing"] if ready > 0 else ["Progressing"],
                )
            ],
            error=None,
        )

    def get_deployment(self, namespace: str, name: str) -> Optional[DeploymentItem]:
        if not self.is_connected():
            return None
        connector = self._get_connector()
        mock_data = connector.get_mock_workload(self._environment_id, namespace, name, is_deployment=True) if connector else None
        
        desired = mock_data.get("desired_replicas", 1) if mock_data else 1
        ready = mock_data.get("ready_replicas", 1) if mock_data else 1
        avail = mock_data.get("available_replicas", 1) if mock_data else 1

        return DeploymentItem(
            name=name,
            namespace=namespace,
            desired_replicas=desired,
            ready_replicas=ready,
            available_replicas=avail,
            updated_replicas=ready,
            conditions=["Available", "Progressing"] if ready > 0 else ["Progressing"],
        )


    def list_services(self, namespace: Optional[str] = None) -> ServicesResponse:
        if not self.is_connected():
            return ServicesResponse(available=False, total=0, services=[], error="Agent offline")
        return ServicesResponse(available=True, total=0, services=[], error=None)

    def restart_pod(self, namespace: str, name: str) -> Tuple[bool, str]:
        if not self.is_connected():
            return False, f"Cannot restart pod: Agent for environment '{self._environment_id}' is offline."
        connector = self._get_connector()
        if connector:
            return connector.dispatch_command_sync(
                environment_id=self._environment_id,
                action=AgentActionType.RESTART_POD,
                target_namespace=namespace,
                target_name=name,
            )
        return False, "Agent connector not available."

    def rollout_restart_deployment(self, namespace: str, name: str) -> Tuple[bool, str]:
        if not self.is_connected():
            return False, f"Cannot rollout restart deployment: Agent for environment '{self._environment_id}' is offline."
        connector = self._get_connector()
        if connector:
            return connector.dispatch_command_sync(
                environment_id=self._environment_id,
                action=AgentActionType.ROLLOUT_RESTART_DEPLOYMENT,
                target_namespace=namespace,
                target_name=name,
            )
        return False, "Agent connector not available."

    def update_pod_status(self, namespace: str, name: str, phase: str = "Running", ready: bool = True) -> None:
        """Update mock/in-memory state for testing and simulation verification."""
        connector = self._get_connector()
        if connector:
            connector.update_mock_workload(self._environment_id, namespace, name, is_deployment=False, phase=phase, ready=ready)

    def update_deployment_status(self, namespace: str, name: str, ready_replicas: int, available_replicas: int) -> None:
        """Update mock/in-memory state for testing and simulation verification."""
        connector = self._get_connector()
        if connector:
            connector.update_mock_workload(self._environment_id, namespace, name, is_deployment=True, ready_replicas=ready_replicas, available_replicas=available_replicas)

