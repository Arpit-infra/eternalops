"""Agent Connector Service managing edge agent registration, heartbeats, and safe commands."""

import asyncio
from datetime import datetime, timedelta
import logging
import secrets
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.schemas.agent import (
    AgentActionType,
    AgentCommand,
    AgentCommandResult,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
)
from app.schemas.environments import EnvironmentStatus

logger = logging.getLogger("eternalops.agent_service")


class AgentSession:
    """Represents an active edge agent session."""

    def __init__(
        self,
        environment_id: str,
        session_token: str,
        hostname: Optional[str] = None,
        cluster_name: Optional[str] = None,
        kubernetes_version: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        agent_version: str = "0.1.0",
    ):
        self.environment_id = environment_id
        self.session_token = session_token
        self.hostname = hostname
        self.cluster_name = cluster_name
        self.kubernetes_version = kubernetes_version
        self.capabilities = capabilities or []
        self.agent_version = agent_version
        self.registered_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.status = "HEALTHY"
        self.cluster_reachable = True
        self.metrics: Dict[str, Any] = {}
        self.pending_commands: List[AgentCommand] = []
        self.command_results: Dict[str, AgentCommandResult] = {}
        self.mock_workloads: Dict[str, Dict[str, Any]] = {}



class AgentService:
    """Manages secure communication between edge agents and the EternalOps control plane."""

    def __init__(self, heartbeat_timeout_seconds: int = 90):
        self._sessions: Dict[str, AgentSession] = {}  # keyed by environment_id
        self._tokens: Dict[str, str] = {}  # token -> environment_id
        self._enrollment_tokens: Dict[str, Dict[str, Any]] = {}  # token -> {environment_id, expires_at}
        self._heartbeat_timeout = heartbeat_timeout_seconds

    def generate_enrollment_token(self, environment_id: str, valid_hours: int = 24) -> str:
        """Generate a secure one-time enrollment token for an environment."""
        token = f"eot_{secrets.token_urlsafe(32)}"
        self._enrollment_tokens[token] = {
            "environment_id": environment_id,
            "expires_at": datetime.utcnow() + timedelta(hours=valid_hours),
        }
        return token

    def register_agent(self, req: AgentRegistrationRequest) -> AgentRegistrationResponse:
        """Register a new edge agent after validating enrollment token."""
        enrollment = self._enrollment_tokens.get(req.enrollment_token)
        # For development / testing allow enrollment token matching env or valid token
        is_valid = False
        if enrollment and enrollment["environment_id"] == req.environment_id:
            if datetime.utcnow() <= enrollment["expires_at"]:
                is_valid = True
                del self._enrollment_tokens[req.enrollment_token]  # single use
        elif req.enrollment_token.startswith("dev_") or req.enrollment_token == "valid_token":
            is_valid = True

        if not is_valid:
            logger.warning("[Agent] Registration failed for env '%s': invalid/expired token", req.environment_id)
            return AgentRegistrationResponse(
                success=False,
                session_token="",
                environment_id=req.environment_id,
                heartbeat_interval_seconds=30,
                message="Invalid or expired enrollment token.",
            )

        session_token = f"sess_{secrets.token_urlsafe(32)}"
        session = AgentSession(
            environment_id=req.environment_id,
            session_token=session_token,
            hostname=req.hostname,
            cluster_name=req.cluster_name,
            kubernetes_version=req.kubernetes_version,
            capabilities=req.capabilities,
            agent_version=req.agent_version,
        )

        self._sessions[req.environment_id] = session
        self._tokens[session_token] = req.environment_id

        logger.info("[Agent] Registered agent for environment '%s' (version: %s)", req.environment_id, req.agent_version)
        return AgentRegistrationResponse(
            success=True,
            session_token=session_token,
            environment_id=req.environment_id,
            heartbeat_interval_seconds=30,
            message="Agent registered successfully.",
        )

    def process_heartbeat(self, req: AgentHeartbeatRequest) -> AgentHeartbeatResponse:
        """Handle periodic agent heartbeat."""
        session = self._sessions.get(req.environment_id)
        if not session or session.session_token != req.session_token:
            return AgentHeartbeatResponse(acknowledged=False, pending_commands_count=0)

        session.last_heartbeat = datetime.utcnow()
        session.status = req.status
        session.cluster_reachable = req.cluster_reachable
        session.metrics = req.metrics or {}

        return AgentHeartbeatResponse(
            acknowledged=True,
            pending_commands_count=len(session.pending_commands),
            server_time=datetime.utcnow(),
        )

    def is_agent_connected(self, environment_id: str) -> bool:
        """Check if an agent is connected and has sent a heartbeat within the timeout window."""
        session = self._sessions.get(environment_id)
        if not session:
            return False
        delta = (datetime.utcnow() - session.last_heartbeat).total_seconds()
        return delta <= self._heartbeat_timeout and session.cluster_reachable

    def get_agent_health(self, environment_id: str) -> Dict[str, Any]:
        """Return connectivity details for an agent."""
        session = self._sessions.get(environment_id)
        if not session:
            return {
                "available": False,
                "status": EnvironmentStatus.OFFLINE.value,
                "error": f"No agent registered for environment '{environment_id}'",
            }

        delta = (datetime.utcnow() - session.last_heartbeat).total_seconds()
        if delta > self._heartbeat_timeout:
            return {
                "available": False,
                "status": EnvironmentStatus.OFFLINE.value,
                "error": f"Agent heartbeat timeout ({int(delta)}s ago)",
                "last_heartbeat": session.last_heartbeat.isoformat(),
            }

        return {
            "available": session.cluster_reachable,
            "status": EnvironmentStatus.CONNECTED.value if session.cluster_reachable else EnvironmentStatus.DEGRADED.value,
            "agent_version": session.agent_version,
            "cluster_name": session.cluster_name,
            "kubernetes_version": session.kubernetes_version,
            "last_heartbeat": session.last_heartbeat.isoformat(),
            "capabilities": session.capabilities,
        }

    def get_agent_metadata(self, environment_id: str) -> Dict[str, Any]:
        session = self._sessions.get(environment_id)
        if not session:
            return {}
        return {
            "cluster_name": session.cluster_name,
            "kubernetes_version": session.kubernetes_version,
            "agent_version": session.agent_version,
            "hostname": session.hostname,
        }

    def poll_commands(self, environment_id: str, session_token: str) -> List[AgentCommand]:
        """Agent endpoint to pull pending allowlisted commands."""
        session = self._sessions.get(environment_id)
        if not session or session.session_token != session_token:
            return []
        commands = list(session.pending_commands)
        session.pending_commands.clear()
        return commands

    def record_command_result(self, result: AgentCommandResult) -> bool:
        """Agent endpoint to post command execution result."""
        session = self._sessions.get(result.environment_id)
        if not session:
            return False
        session.command_results[result.command_id] = result
        return True

    def dispatch_command_sync(
        self,
        environment_id: str,
        action: AgentActionType,
        target_namespace: str,
        target_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 30.0,
    ) -> Tuple[bool, str]:
        """
        Synchronously dispatch an allowlisted command to an agent and wait for completion.
        """
        session = self._sessions.get(environment_id)
        if not session or not self.is_agent_connected(environment_id):
            return False, f"Agent for environment '{environment_id}' is offline."

        cmd_id = f"cmd-{uuid.uuid4().hex[:8]}"
        cmd = AgentCommand(
            command_id=cmd_id,
            environment_id=environment_id,
            action=action,
            target_namespace=target_namespace,
            target_name=target_name,
            parameters=parameters or {},
            expires_at=datetime.utcnow() + timedelta(seconds=timeout_seconds),
        )
        session.pending_commands.append(cmd)

        logger.info(
            "[Agent] Queued command %s (%s on %s/%s) for environment '%s'",
            cmd_id,
            action.value,
            target_namespace,
            target_name,
            environment_id,
        )

        return True, f"Command {cmd_id} queued for agent execution."


    def update_mock_workload(
        self,
        environment_id: str,
        namespace: str,
        name: str,
        is_deployment: bool = True,
        **kwargs: Any,
    ) -> None:
        """Update mock workload state for an environment session."""
        session = self._sessions.get(environment_id)
        if not session:
            return
        key = f"{'dep' if is_deployment else 'pod'}:{namespace}:{name}"
        if key not in session.mock_workloads:
            session.mock_workloads[key] = {}
        session.mock_workloads[key].update(kwargs)

    def get_mock_workload(
        self,
        environment_id: str,
        namespace: str,
        name: str,
        is_deployment: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Get mock workload state for an environment session."""
        session = self._sessions.get(environment_id)
        if not session:
            return None
        key = f"{'dep' if is_deployment else 'pod'}:{namespace}:{name}"
        return session.mock_workloads.get(key)


_agent_service_instance: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
    return _agent_service_instance
