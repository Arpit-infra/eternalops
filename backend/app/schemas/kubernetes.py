"""Kubernetes response models and resource representations."""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


class KubernetesStatusResponse(BaseModel):
    """Status response for Kubernetes API connectivity."""

    available: bool = Field(..., description="Whether Kubernetes cluster is reachable")
    in_cluster: bool = Field(..., description="Whether running with in-cluster configuration")
    context: Optional[str] = Field(default=None, description="Active kubeconfig context name")
    cluster_version: Optional[str] = Field(default=None, description="Kubernetes server Git version")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")


class ClusterInfoResponse(BaseModel):
    """Cluster version and server information."""

    available: bool = Field(..., description="Whether cluster information was successfully retrieved")
    git_version: Optional[str] = Field(default=None, description="Git version of the cluster API server")
    major: Optional[str] = Field(default=None, description="Major version number")
    minor: Optional[str] = Field(default=None, description="Minor version number")
    platform: Optional[str] = Field(default=None, description="Server build platform")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")


class NamespaceItem(BaseModel):
    """Kubernetes Namespace model."""

    name: str = Field(..., description="Namespace name")
    status: str = Field(..., description="Status phase, e.g. Active or Terminating")
    creation_timestamp: Optional[str] = Field(default=None, description="Creation ISO timestamp")


class NamespacesResponse(BaseModel):
    """List of Kubernetes namespaces."""

    available: bool = Field(..., description="Whether the cluster was reachable")
    total: int = Field(default=0, description="Total namespaces count")
    namespaces: List[NamespaceItem] = Field(default_factory=list, description="List of namespaces")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")


class NodeItem(BaseModel):
    """Kubernetes Node information model."""

    name: str = Field(..., description="Node name")
    status: str = Field(..., description="Ready or NotReady")
    cpu_capacity: str = Field(..., description="Total CPU capacity (e.g. '8')")
    memory_capacity: str = Field(..., description="Total memory capacity (e.g. '16384Ki')")
    os_image: str = Field(..., description="Node operating system image")
    kubelet_version: str = Field(..., description="Kubelet version")
    architecture: Optional[str] = Field(default=None, description="Architecture (e.g. amd64)")


class NodesResponse(BaseModel):
    """List of Kubernetes cluster nodes."""

    available: bool = Field(..., description="Whether the cluster was reachable")
    total: int = Field(default=0, description="Total nodes count")
    nodes: List[NodeItem] = Field(default_factory=list, description="List of nodes")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")


class PodContainerStatus(BaseModel):
    """Container status inside a pod."""

    name: str = Field(..., description="Container name")
    ready: bool = Field(..., description="Container readiness")
    restart_count: int = Field(..., description="Total restarts for this container")
    state: str = Field(..., description="Container state (running, waiting, terminated)")


class PodItem(BaseModel):
    """Kubernetes Pod information model."""

    namespace: str = Field(..., description="Pod namespace")
    name: str = Field(..., description="Pod name")
    phase: str = Field(..., description="Pod phase (Running, Pending, Succeeded, Failed, Unknown)")
    node_name: Optional[str] = Field(default=None, description="Node running this pod")
    restart_count: int = Field(..., description="Cumulative container restart count")
    containers: List[PodContainerStatus] = Field(default_factory=list, description="Container states")
    start_time: Optional[str] = Field(default=None, description="Pod start timestamp")


class PodsResponse(BaseModel):
    """List of Kubernetes pods."""

    available: bool = Field(..., description="Whether the cluster was reachable")
    total: int = Field(default=0, description="Total pods count")
    pods: List[PodItem] = Field(default_factory=list, description="List of pods")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")


class DeploymentItem(BaseModel):
    """Kubernetes Deployment information model."""

    namespace: str = Field(..., description="Deployment namespace")
    name: str = Field(..., description="Deployment name")
    desired_replicas: int = Field(..., description="Desired replica count")
    ready_replicas: int = Field(..., description="Ready replica count")
    available_replicas: int = Field(..., description="Available replica count")
    updated_replicas: int = Field(..., description="Updated replica count")


class DeploymentsResponse(BaseModel):
    """List of Kubernetes deployments."""

    available: bool = Field(..., description="Whether the cluster was reachable")
    total: int = Field(default=0, description="Total deployments count")
    deployments: List[DeploymentItem] = Field(default_factory=list, description="List of deployments")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")


class ServicePortItem(BaseModel):
    """Kubernetes Service port model."""

    name: Optional[str] = Field(default=None, description="Port name")
    port: int = Field(..., description="Port number exposed by the service")
    target_port: Optional[Any] = Field(default=None, description="Target port number or name")
    protocol: str = Field(default="TCP", description="Protocol (TCP, UDP, SCTP)")


class ServiceItem(BaseModel):
    """Kubernetes Service model."""

    namespace: str = Field(..., description="Service namespace")
    name: str = Field(..., description="Service name")
    type: str = Field(..., description="Service type (ClusterIP, NodePort, LoadBalancer, ExternalName)")
    cluster_ip: Optional[str] = Field(default=None, description="Assigned Cluster IP")
    ports: List[ServicePortItem] = Field(default_factory=list, description="Port mappings")


class ServicesResponse(BaseModel):
    """List of Kubernetes services."""

    available: bool = Field(..., description="Whether the cluster was reachable")
    total: int = Field(default=0, description="Total services count")
    services: List[ServiceItem] = Field(default_factory=list, description="List of services")
    error: Optional[str] = Field(default=None, description="Error message if unavailable")
