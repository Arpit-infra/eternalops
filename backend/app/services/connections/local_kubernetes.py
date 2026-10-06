"""Local Kubernetes Connection Adapter."""

from typing import Any, Dict, Optional, Tuple

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
from app.services.kubernetes_service import KubernetesService, get_kubernetes_service


class LocalKubernetesConnection(EnvironmentConnection):
    """Adapter wrapping KubernetesService for local Docker Desktop / local clusters."""

    def __init__(
        self,
        environment_id: str = "env_local_dev",
        k8s_service: Optional[KubernetesService] = None,
    ):
        self._environment_id = environment_id
        self._k8s = k8s_service or get_kubernetes_service()

    @property
    def environment_id(self) -> str:
        return self._environment_id

    @property
    def connection_type(self) -> str:
        return "local_kubernetes"

    def is_connected(self) -> bool:
        status = self._k8s.get_status()
        return bool(status.get("available", False))

    def health_check(self) -> Dict[str, Any]:
        return self._k8s.get_status()

    def get_cluster_info(self) -> ClusterInfoResponse:
        return self._k8s.get_cluster_info()

    def list_namespaces(self) -> NamespacesResponse:
        return self._k8s.get_namespaces()

    def list_nodes(self) -> NodesResponse:
        return self._k8s.get_nodes()

    def list_pods(self, namespace: Optional[str] = None) -> PodsResponse:
        return self._k8s.get_pods(namespace=namespace)

    def get_pod(self, namespace: str, name: str) -> Optional[PodItem]:
        return self._k8s.get_pod(namespace=namespace, name=name)

    def list_deployments(self, namespace: Optional[str] = None) -> DeploymentsResponse:
        return self._k8s.get_deployments(namespace=namespace)

    def get_deployment(self, namespace: str, name: str) -> Optional[DeploymentItem]:
        return self._k8s.get_deployment(namespace=namespace, name=name)

    def list_services(self, namespace: Optional[str] = None) -> ServicesResponse:
        return self._k8s.get_services(namespace=namespace)

    def restart_pod(self, namespace: str, name: str) -> Tuple[bool, str]:
        return self._k8s.restart_pod(namespace=namespace, name=name)

    def rollout_restart_deployment(self, namespace: str, name: str) -> Tuple[bool, str]:
        return self._k8s.rollout_restart_deployment(namespace=namespace, name=name)
