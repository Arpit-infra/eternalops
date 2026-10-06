"""Base Environment Connection interface and contracts."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

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


class EnvironmentConnection(ABC):
    """Abstract interface defining required infrastructure interactions for any connected environment."""

    @property
    @abstractmethod
    def environment_id(self) -> str:
        """The environment ID this connection is bound to."""
        pass

    @property
    @abstractmethod
    def connection_type(self) -> str:
        """Type of connection (local_kubernetes, agent, etc.)."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is currently active and reachable."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform a connection health check returning status and metadata."""
        pass

    @abstractmethod
    def get_cluster_info(self) -> ClusterInfoResponse:
        """Retrieve cluster version and platform details."""
        pass

    @abstractmethod
    def list_namespaces(self) -> NamespacesResponse:
        """List namespaces in the environment."""
        pass

    @abstractmethod
    def list_nodes(self) -> NodesResponse:
        """List cluster nodes and node health."""
        pass

    @abstractmethod
    def list_pods(self, namespace: Optional[str] = None) -> PodsResponse:
        """List pods in a given namespace or all namespaces."""
        pass

    @abstractmethod
    def get_pod(self, namespace: str, name: str) -> Optional[PodItem]:
        """Retrieve single pod details."""
        pass

    @abstractmethod
    def list_deployments(self, namespace: Optional[str] = None) -> DeploymentsResponse:
        """List deployments in a given namespace or all namespaces."""
        pass

    @abstractmethod
    def get_deployment(self, namespace: str, name: str) -> Optional[DeploymentItem]:
        """Retrieve single deployment details."""
        pass

    @abstractmethod
    def list_services(self, namespace: Optional[str] = None) -> ServicesResponse:
        """List services in a given namespace or all namespaces."""
        pass

    @abstractmethod
    def restart_pod(self, namespace: str, name: str) -> Tuple[bool, str]:
        """Execute pod deletion / restart remediation action."""
        pass

    @abstractmethod
    def rollout_restart_deployment(self, namespace: str, name: str) -> Tuple[bool, str]:
        """Execute deployment rolling restart remediation action."""
        pass
