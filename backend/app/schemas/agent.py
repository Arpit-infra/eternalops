"""Agent contract and protocol schemas for EternalOps edge agent integration."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentActionType(str, Enum):
    RESTART_POD = "RESTART_POD"
    ROLLOUT_RESTART_DEPLOYMENT = "ROLLOUT_RESTART_DEPLOYMENT"
    GET_POD_STATUS = "GET_POD_STATUS"
    GET_DEPLOYMENT_STATUS = "GET_DEPLOYMENT_STATUS"
    VERIFY_WORKLOAD = "VERIFY_WORKLOAD"
    HEALTH_CHECK = "HEALTH_CHECK"


class AgentRegistrationRequest(BaseModel):
    environment_id: str = Field(..., description="Target environment ID to bind with")
    enrollment_token: str = Field(..., description="Secure one-time or bearer enrollment token")
    agent_version: str = Field("0.1.0", description="Version of the installed agent")
    hostname: Optional[str] = Field(None, description="Host/node where agent runs")
    cluster_name: Optional[str] = Field(None, description="Kubernetes cluster identifier")
    kubernetes_version: Optional[str] = Field(None, description="Observed k8s server version")
    capabilities: List[str] = Field(default_factory=list, description="Supported agent capabilities")


class AgentRegistrationResponse(BaseModel):
    success: bool
    session_token: str
    environment_id: str
    heartbeat_interval_seconds: int = 30
    message: str


class AgentHeartbeatRequest(BaseModel):
    environment_id: str = Field(..., description="Environment ID")
    session_token: str = Field(..., description="Agent session authentication token")
    status: str = Field("HEALTHY", description="Agent operational status")
    cluster_reachable: bool = Field(True, description="True if agent can talk to local cluster API")
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Basic host/agent telemetry")


class AgentHeartbeatResponse(BaseModel):
    acknowledged: bool
    pending_commands_count: int = 0
    server_time: datetime = Field(default_factory=datetime.utcnow)


class AgentCommand(BaseModel):
    command_id: str = Field(..., description="Unique command execution ID")
    environment_id: str
    action: AgentActionType
    target_namespace: str = "default"
    target_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class AgentCommandResult(BaseModel):
    command_id: str
    environment_id: str
    action: AgentActionType
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)
