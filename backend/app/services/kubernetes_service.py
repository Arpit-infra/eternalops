"""Kubernetes Client Integration Service (Read-Only)."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException

from app.core.config import Settings, get_settings
from app.schemas.kubernetes import (
    ClusterInfoResponse,
    DeploymentItem,
    DeploymentsResponse,
    NamespaceItem,
    NamespacesResponse,
    NodeItem,
    NodesResponse,
    PodContainerStatus,
    PodItem,
    PodsResponse,
    ServiceItem,
    ServicePortItem,
    ServicesResponse,
)
from app.utils.errors import KubernetesUnavailableError

logger = logging.getLogger("eternalops.kubernetes")


class KubernetesService:
    """Service for interacting with Kubernetes cluster API (Read-Only)."""

    def __init__(
        self,
        in_cluster: Optional[bool] = None,
        context: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        settings: Settings = get_settings()
        self.in_cluster = in_cluster if in_cluster is not None else settings.KUBERNETES_IN_CLUSTER
        raw_context = context if context is not None else settings.KUBERNETES_CONTEXT
        self.context = raw_context.strip() if isinstance(raw_context, str) and raw_context.strip() else None
        self.timeout = timeout if timeout is not None else settings.KUBERNETES_TIMEOUT_SECONDS
        self._is_configured = False
        self._config_error: Optional[str] = None
        self._active_context: Optional[str] = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialize Kubernetes API client configuration."""
        try:
            if self.in_cluster:
                config.load_incluster_config()
                self._is_configured = True
                self._active_context = "in-cluster"
                self._config_error = None
                logger.info("Loaded in-cluster Kubernetes configuration")
            else:
                if self.context:
                    config.load_kube_config(context=self.context)
                else:
                    config.load_kube_config()
                self._is_configured = True
                self._config_error = None

                try:
                    contexts, active_context = config.list_kube_config_contexts()
                    if active_context and isinstance(active_context, dict):
                        self._active_context = active_context.get("name")
                    elif active_context:
                        self._active_context = getattr(active_context, "name", None)
                    else:
                        self._active_context = self.context
                except Exception:
                    self._active_context = self.context

                logger.info("Loaded local kubeconfig configuration (context: %s)", self._active_context or "default")
        except ConfigException as exc:
            self._is_configured = False
            self._active_context = None
            self._config_error = f"Kubernetes configuration error: {str(exc)}"
            logger.warning("Kubernetes config initialization failed: %s", str(exc))
        except FileNotFoundError as exc:
            self._is_configured = False
            self._active_context = None
            self._config_error = f"Kubeconfig file not found: {str(exc)}"
            logger.warning("Kubeconfig not found: %s", str(exc))
        except Exception as exc:
            self._is_configured = False
            self._active_context = None
            self._config_error = f"Failed to initialize Kubernetes client: {str(exc)}"
            logger.warning("Unexpected error loading Kubernetes config: %s", str(exc))

    def _get_api_client(self) -> client.ApiClient:
        """Create and return configured ApiClient."""
        if not self._is_configured:
            # Retry initializing in case configuration changed
            self._init_client()
        if not self._is_configured:
            raise KubernetesUnavailableError(
                message=self._config_error or "Kubernetes configuration not initialized"
            )
        api_client = client.ApiClient()
        return api_client

    def get_status(self) -> Dict[str, Any]:
        """
        Check if the Kubernetes API server is reachable and responsive.
        """
        if not self._is_configured:
            self._init_client()

        if not self._is_configured:
            return {
                "available": False,
                "in_cluster": self.in_cluster,
                "context": self._active_context or self.context,
                "cluster_version": None,
                "error": self._config_error or "Kubernetes configuration not initialized",
            }

        try:
            api_client = self._get_api_client()
            version_api = client.VersionApi(api_client)
            version_info = version_api.get_code()
            git_version = getattr(version_info, "git_version", "unknown")
            return {
                "available": True,
                "in_cluster": self.in_cluster,
                "context": self._active_context or self.context,
                "cluster_version": git_version,
                "error": None,
            }
        except Exception as exc:
            logger.warning("Kubernetes cluster status check failed: %s", str(exc))
            return {
                "available": False,
                "in_cluster": self.in_cluster,
                "context": self._active_context or self.context,
                "cluster_version": None,
                "error": f"Cluster unreachable: {str(exc)}",
            }

    def get_cluster_info(self) -> ClusterInfoResponse:
        """Get Kubernetes cluster server version information."""
        try:
            api_client = self._get_api_client()
            version_api = client.VersionApi(api_client)
            info = version_api.get_code()
            return ClusterInfoResponse(
                available=True,
                git_version=getattr(info, "git_version", None),
                major=getattr(info, "major", None),
                minor=getattr(info, "minor", None),
                platform=getattr(info, "platform", None),
                error=None,
            )
        except Exception as exc:
            logger.warning("Failed to get cluster info: %s", str(exc))
            return ClusterInfoResponse(
                available=False,
                error=str(exc),
            )

    def get_namespaces(self) -> NamespacesResponse:
        """List all namespaces in the cluster."""
        try:
            api_client = self._get_api_client()
            v1 = client.CoreV1Api(api_client)
            ns_list = v1.list_namespace(timeout_seconds=int(self.timeout))

            namespaces: List[NamespaceItem] = []
            for item in ns_list.items:
                metadata = item.metadata
                status = item.status
                name = metadata.name if metadata else "unknown"
                phase = status.phase if status and status.phase else "Active"
                creation = (
                    metadata.creation_timestamp.isoformat()
                    if metadata and metadata.creation_timestamp
                    else None
                )
                namespaces.append(
                    NamespaceItem(name=name, status=phase, creation_timestamp=creation)
                )

            return NamespacesResponse(
                available=True,
                total=len(namespaces),
                namespaces=namespaces,
                error=None,
            )
        except Exception as exc:
            logger.warning("Failed to list namespaces: %s", str(exc))
            return NamespacesResponse(
                available=False,
                total=0,
                namespaces=[],
                error=str(exc),
            )

    def get_nodes(self) -> NodesResponse:
        """List all nodes in the cluster with status and capacities."""
        try:
            api_client = self._get_api_client()
            v1 = client.CoreV1Api(api_client)
            node_list = v1.list_node(timeout_seconds=int(self.timeout))

            nodes: List[NodeItem] = []
            for item in node_list.items:
                metadata = item.metadata
                status = item.status
                node_name = metadata.name if metadata else "unknown"

                # Determine Ready status
                ready_status = "NotReady"
                if status and status.conditions:
                    for cond in status.conditions:
                        if cond.type == "Ready" and cond.status == "True":
                            ready_status = "Ready"
                            break

                capacity = status.capacity if status and status.capacity else {}
                node_info = status.node_info if status else None

                cpu_cap = str(capacity.get("cpu", "N/A"))
                mem_cap = str(capacity.get("memory", "N/A"))
                os_image = getattr(node_info, "os_image", "unknown") if node_info else "unknown"
                kubelet_ver = getattr(node_info, "kubelet_version", "unknown") if node_info else "unknown"
                arch = getattr(node_info, "architecture", "unknown") if node_info else "unknown"

                nodes.append(
                    NodeItem(
                        name=node_name,
                        status=ready_status,
                        cpu_capacity=cpu_cap,
                        memory_capacity=mem_cap,
                        os_image=os_image,
                        kubelet_version=kubelet_ver,
                        architecture=arch,
                    )
                )

            return NodesResponse(
                available=True,
                total=len(nodes),
                nodes=nodes,
                error=None,
            )
        except Exception as exc:
            logger.warning("Failed to list nodes: %s", str(exc))
            return NodesResponse(
                available=False,
                total=0,
                nodes=[],
                error=str(exc),
            )

    def get_pods(self, namespace: Optional[str] = None) -> PodsResponse:
        """List pods across all namespaces or a specific namespace."""
        try:
            api_client = self._get_api_client()
            v1 = client.CoreV1Api(api_client)

            if namespace:
                pod_list = v1.list_namespaced_pod(
                    namespace=namespace, timeout_seconds=int(self.timeout)
                )
            else:
                pod_list = v1.list_pod_for_all_namespaces(timeout_seconds=int(self.timeout))

            pods: List[PodItem] = []
            for item in pod_list.items:
                metadata = item.metadata
                spec = item.spec
                status = item.status

                pod_ns = metadata.namespace if metadata and metadata.namespace else "default"
                pod_name = metadata.name if metadata else "unknown"
                phase = status.phase if status and status.phase else "Unknown"
                node_name = spec.node_name if spec else None
                start_time = (
                    status.start_time.isoformat()
                    if status and status.start_time
                    else None
                )

                containers: List[PodContainerStatus] = []
                total_restarts = 0

                if status and status.container_statuses:
                    for cs in status.container_statuses:
                        c_name = cs.name
                        c_ready = bool(cs.ready)
                        c_restarts = int(cs.restart_count or 0)
                        total_restarts += c_restarts

                        # Determine state
                        c_state = "unknown"
                        if cs.state:
                            if cs.state.running:
                                c_state = "running"
                            elif cs.state.waiting:
                                c_state = f"waiting ({cs.state.waiting.reason or 'unknown'})"
                            elif cs.state.terminated:
                                c_state = f"terminated ({cs.state.terminated.reason or 'unknown'})"

                        containers.append(
                            PodContainerStatus(
                                name=c_name,
                                ready=c_ready,
                                restart_count=c_restarts,
                                state=c_state,
                            )
                        )

                pods.append(
                    PodItem(
                        namespace=pod_ns,
                        name=pod_name,
                        phase=phase,
                        node_name=node_name,
                        restart_count=total_restarts,
                        containers=containers,
                        start_time=start_time,
                    )
                )

            return PodsResponse(
                available=True,
                total=len(pods),
                pods=pods,
                error=None,
            )
        except Exception as exc:
            logger.warning("Failed to list pods: %s", str(exc))
            return PodsResponse(
                available=False,
                total=0,
                pods=[],
                error=str(exc),
            )

    def get_deployments(self, namespace: Optional[str] = None) -> DeploymentsResponse:
        """List deployments across all namespaces or a specific namespace."""
        try:
            api_client = self._get_api_client()
            apps_v1 = client.AppsV1Api(api_client)

            if namespace:
                dep_list = apps_v1.list_namespaced_deployment(
                    namespace=namespace, timeout_seconds=int(self.timeout)
                )
            else:
                dep_list = apps_v1.list_deployment_for_all_namespaces(
                    timeout_seconds=int(self.timeout)
                )

            deployments: List[DeploymentItem] = []
            for item in dep_list.items:
                metadata = item.metadata
                spec = item.spec
                status = item.status

                dep_ns = metadata.namespace if metadata and metadata.namespace else "default"
                dep_name = metadata.name if metadata else "unknown"

                desired = spec.replicas if spec and spec.replicas is not None else 0
                ready = status.ready_replicas if status and status.ready_replicas is not None else 0
                avail = status.available_replicas if status and status.available_replicas is not None else 0
                updated = status.updated_replicas if status and status.updated_replicas is not None else 0

                deployments.append(
                    DeploymentItem(
                        namespace=dep_ns,
                        name=dep_name,
                        desired_replicas=desired,
                        ready_replicas=ready,
                        available_replicas=avail,
                        updated_replicas=updated,
                    )
                )

            return DeploymentsResponse(
                available=True,
                total=len(deployments),
                deployments=deployments,
                error=None,
            )
        except Exception as exc:
            logger.warning("Failed to list deployments: %s", str(exc))
            return DeploymentsResponse(
                available=False,
                total=0,
                deployments=[],
                error=str(exc),
            )

    def get_services(self, namespace: Optional[str] = None) -> ServicesResponse:
        """List services across all namespaces or a specific namespace."""
        try:
            api_client = self._get_api_client()
            v1 = client.CoreV1Api(api_client)

            if namespace:
                svc_list = v1.list_namespaced_service(
                    namespace=namespace, timeout_seconds=int(self.timeout)
                )
            else:
                svc_list = v1.list_service_for_all_namespaces(
                    timeout_seconds=int(self.timeout)
                )

            services: List[ServiceItem] = []
            for item in svc_list.items:
                metadata = item.metadata
                spec = item.spec

                svc_ns = metadata.namespace if metadata and metadata.namespace else "default"
                svc_name = metadata.name if metadata else "unknown"
                svc_type = spec.type if spec and spec.type else "ClusterIP"
                cluster_ip = spec.cluster_ip if spec and spec.cluster_ip else None

                ports: List[ServicePortItem] = []
                if spec and spec.ports:
                    for p in spec.ports:
                        ports.append(
                            ServicePortItem(
                                name=p.name,
                                port=p.port,
                                target_port=str(p.target_port) if p.target_port is not None else None,
                                protocol=p.protocol or "TCP",
                            )
                        )

                services.append(
                    ServiceItem(
                        namespace=svc_ns,
                        name=svc_name,
                        type=svc_type,
                        cluster_ip=cluster_ip,
                        ports=ports,
                    )
                )

            return ServicesResponse(
                available=True,
                total=len(services),
                services=services,
                error=None,
            )
        except Exception as exc:
            logger.warning("Failed to list services: %s", str(exc))
            return ServicesResponse(
                available=False,
                total=0,
                services=[],
                error=str(exc),
            )

    def get_pod(self, namespace: str, name: str) -> Optional[PodItem]:
        """Fetch single pod by namespace and name."""
        try:
            api_client = self._get_api_client()
            v1 = client.CoreV1Api(api_client)
            item = v1.read_namespaced_pod(name=name, namespace=namespace)
            metadata = item.metadata
            spec = item.spec
            status = item.status

            pod_ns = metadata.namespace if metadata and metadata.namespace else namespace
            pod_name = metadata.name if metadata else name
            phase = status.phase if status and status.phase else "Unknown"
            node_name = spec.node_name if spec else None
            start_time = status.start_time.isoformat() if status and status.start_time else None

            containers: List[PodContainerStatus] = []
            total_restarts = 0
            if status and status.container_statuses:
                for cs in status.container_statuses:
                    c_name = cs.name
                    c_ready = bool(cs.ready)
                    c_restarts = int(cs.restart_count or 0)
                    total_restarts += c_restarts
                    c_state = "unknown"
                    if cs.state:
                        if cs.state.running:
                            c_state = "running"
                        elif cs.state.waiting:
                            c_state = f"waiting ({cs.state.waiting.reason or 'unknown'})"
                        elif cs.state.terminated:
                            c_state = f"terminated ({cs.state.terminated.reason or 'unknown'})"

                    containers.append(
                        PodContainerStatus(
                            name=c_name,
                            ready=c_ready,
                            restart_count=c_restarts,
                            state=c_state,
                        )
                    )

            return PodItem(
                namespace=pod_ns,
                name=pod_name,
                phase=phase,
                node_name=node_name,
                restart_count=total_restarts,
                containers=containers,
                start_time=start_time,
            )
        except Exception as exc:
            logger.warning("Failed to get pod %s/%s: %s", namespace, name, str(exc))
            return None

    def get_deployment(self, namespace: str, name: str) -> Optional[DeploymentItem]:
        """Fetch single deployment by namespace and name."""
        try:
            api_client = self._get_api_client()
            apps_v1 = client.AppsV1Api(api_client)
            item = apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
            metadata = item.metadata
            spec = item.spec
            status = item.status

            desired = spec.replicas if spec and spec.replicas is not None else 0
            ready = status.ready_replicas if status and status.ready_replicas is not None else 0
            avail = status.available_replicas if status and status.available_replicas is not None else 0
            updated = status.updated_replicas if status and status.updated_replicas is not None else 0

            return DeploymentItem(
                namespace=metadata.namespace if metadata else namespace,
                name=metadata.name if metadata else name,
                desired_replicas=desired,
                ready_replicas=ready,
                available_replicas=avail,
                updated_replicas=updated,
            )
        except Exception as exc:
            logger.warning("Failed to get deployment %s/%s: %s", namespace, name, str(exc))
            return None

    def restart_pod(self, namespace: str, name: str) -> Tuple[bool, str]:
        """Safely delete a pod to trigger recreation by its controller."""
        try:
            api_client = self._get_api_client()
            v1 = client.CoreV1Api(api_client)
            v1.delete_namespaced_pod(
                name=name,
                namespace=namespace,
                body=client.V1DeleteOptions(grace_period_seconds=0),
            )
            logger.info("Successfully deleted pod %s/%s for restart", namespace, name)
            return True, f"Pod {namespace}/{name} deleted successfully for controller recreation."
        except ApiException as exc:
            if exc.status == 404:
                return True, f"Pod {namespace}/{name} was already deleted or not found."
            logger.error("Kubernetes API error restarting pod %s/%s: %s", namespace, name, str(exc))
            return False, f"Kubernetes API error: {exc.reason or str(exc)}"
        except Exception as exc:
            logger.error("Failed to restart pod %s/%s: %s", namespace, name, str(exc))
            return False, f"Unexpected error restarting pod: {str(exc)}"

    def rollout_restart_deployment(self, namespace: str, name: str) -> Tuple[bool, str]:
        """Trigger a rolling restart on a deployment via timestamp annotation update."""
        from datetime import datetime
        try:
            api_client = self._get_api_client()
            apps_v1 = client.AppsV1Api(api_client)
            patch = {
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "kubectl.kubernetes.io/restartedAt": datetime.utcnow().isoformat()
                            }
                        }
                    }
                }
            }
            apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=patch)
            logger.info("Successfully initiated rollout restart for deployment %s/%s", namespace, name)
            return True, f"Rollout restart initiated for deployment {namespace}/{name}."
        except ApiException as exc:
            logger.error("Kubernetes API error restarting deployment %s/%s: %s", namespace, name, str(exc))
            return False, f"Kubernetes API error: {exc.reason or str(exc)}"
        except Exception as exc:
            logger.error("Failed to rollout restart deployment %s/%s: %s", namespace, name, str(exc))
            return False, f"Unexpected error: {str(exc)}"


def get_kubernetes_service() -> KubernetesService:
    """Dependency provider for KubernetesService."""
    return KubernetesService()
