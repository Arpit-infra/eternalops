"""Environment domain models and schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EnvironmentProvider(str, Enum):
    DOCKER_DESKTOP = "docker-desktop"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    ON_PREM = "on-prem"
    CUSTOM = "custom"


class EnvironmentPlatform(str, Enum):
    KUBERNETES = "kubernetes"
    EKS = "eks"
    GKE = "gke"
    AKS = "aks"
    K3S = "k3s"
    MINIKUBE = "minikube"
    CUSTOM = "custom"


class ConnectionType(str, Enum):
    LOCAL_KUBERNETES = "local_kubernetes"
    AGENT = "agent"
    DIRECT_KUBE_API = "direct_kube_api"


class EnvironmentStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


class EnvironmentCapabilities(BaseModel):
    can_read_kubernetes: bool = Field(True, description="Can query cluster state, namespaces, pods, deployments")
    can_read_metrics: bool = Field(True, description="Can query Prometheus / metrics")
    can_restart_pod: bool = Field(True, description="Allowed to delete/restart pods")
    can_restart_deployment: bool = Field(True, description="Allowed to trigger rollout restarts")
    can_scale_deployment: bool = Field(False, description="Allowed to scale replicas")
    can_verify_workload: bool = Field(True, description="Can verify post-remediation health")


class EnvironmentBase(BaseModel):
    name: str = Field(..., description="Human-readable environment name, e.g. 'Local Development'")
    description: Optional[str] = Field(None, description="Environment description")
    provider: EnvironmentProvider = Field(EnvironmentProvider.DOCKER_DESKTOP, description="Infrastructure provider")
    platform: EnvironmentPlatform = Field(EnvironmentPlatform.KUBERNETES, description="Runtime platform")
    connection_type: ConnectionType = Field(ConnectionType.LOCAL_KUBERNETES, description="Connection mechanism")
    organization_id: str = Field("org_default", description="Associated organization ID")


class EnvironmentCreate(EnvironmentBase):
    capabilities: Optional[EnvironmentCapabilities] = Field(default_factory=EnvironmentCapabilities)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    provider: Optional[EnvironmentProvider] = None
    platform: Optional[EnvironmentPlatform] = None
    connection_type: Optional[ConnectionType] = None
    capabilities: Optional[EnvironmentCapabilities] = None
    metadata: Optional[Dict[str, Any]] = None


class Environment(EnvironmentBase):
    id: str = Field(..., description="Unique environment ID, e.g. 'env_local_dev'")
    status: EnvironmentStatus = Field(EnvironmentStatus.CONNECTED, description="Current connectivity state")
    last_seen: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Last communication timestamp")
    last_heartbeat: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Last recorded heartbeat")
    capabilities: EnvironmentCapabilities = Field(default_factory=EnvironmentCapabilities, description="Allowed actions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata and connection configuration")
    error_message: Optional[str] = Field(None, description="Current connection error if any")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")


class EnvironmentHealthResponse(BaseModel):
    environment_id: str
    status: EnvironmentStatus
    connected: bool
    last_heartbeat: Optional[datetime]
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class EnvironmentsListResponse(BaseModel):
    total: int = Field(..., description="Total registered environments")
    environments: List[Environment] = Field(..., description="List of environments")


class EnvironmentEnrollmentToken(BaseModel):
    environment_id: str
    enrollment_token: str
    expires_at: datetime
    instructions: str
