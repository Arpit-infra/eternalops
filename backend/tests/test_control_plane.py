"""Tests for Environment & Organization Control Plane Architecture."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.environments import ConnectionType, EnvironmentCreate, EnvironmentPlatform, EnvironmentProvider
from app.schemas.incidents import Incident, IncidentStatus, RemediationAction
from app.services.connections.base import EnvironmentConnection
from app.services.connections.connection_manager import get_connection_manager
from app.services.environment_service import get_environment_service
from app.services.remediation_service import get_remediation_service
from app.services.verification_service import get_verification_service


@pytest.fixture
def client():
    return TestClient(app)


def test_list_environments_and_default_seed(client):
    """Verify default organization and local development environment are seeded."""
    resp = client.get("/api/environments")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    
    local_dev = next((e for e in data["environments"] if e["id"] == "env_local_dev"), None)
    assert local_dev is not None
    assert local_dev["name"] == "Local Development"
    assert local_dev["provider"] == "docker-desktop"
    assert local_dev["platform"] == "kubernetes"
    assert local_dev["connection_type"] == "local_kubernetes"
    assert local_dev["organization_id"] == "org_default"


def test_create_and_get_environment(client):
    """Test registering and retrieving a new environment."""
    payload = {
        "name": "Staging Customer Cluster",
        "description": "Customer managed EKS cluster",
        "provider": "aws",
        "platform": "eks",
        "connection_type": "agent",
        "organization_id": "org_default",
    }
    create_resp = client.post("/api/environments", json=payload)
    assert create_resp.status_code == 201
    env_data = create_resp.json()
    env_id = env_data["id"]
    assert env_data["name"] == "Staging Customer Cluster"

    # Get by ID
    get_resp = client.get(f"/api/environments/{env_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == env_id


def test_environment_enrollment_token(client):
    """Test generating edge agent enrollment token for an environment."""
    resp = client.post("/api/environments/env_local_dev/token")
    assert resp.status_code == 200
    data = resp.json()
    assert "enrollment_token" in data
    assert data["environment_id"] == "env_local_dev"


def test_agent_registration_and_heartbeat(client):
    """Test agent registration and heartbeat API."""
    # Generate token
    tok_resp = client.post("/api/environments/env_local_dev/token")
    token = tok_resp.json()["enrollment_token"]

    # Register Agent
    reg_resp = client.post(
        "/api/agent/register",
        json={
            "environment_id": "env_local_dev",
            "enrollment_token": token,
            "agent_version": "0.1.0",
            "cluster_name": "remote-cluster",
            "kubernetes_version": "v1.28.0",
        },
    )
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert reg_data["success"] is True
    session_token = reg_data["session_token"]

    # Heartbeat
    hb_resp = client.post(
        "/api/agent/heartbeat",
        json={
            "environment_id": "env_local_dev",
            "session_token": session_token,
            "status": "HEALTHY",
            "cluster_reachable": True,
        },
    )
    assert hb_resp.status_code == 200
    assert hb_resp.json()["acknowledged"] is True


def test_connection_resolution_and_protection():
    """Test ConnectionManager resolution and wrong/unavailable environment safety."""
    conn_mgr = get_connection_manager()
    remediation_svc = get_remediation_service()

    # 1. Local environment resolves to LocalKubernetesConnection
    local_conn = conn_mgr.get_connection("env_local_dev")
    assert local_conn.environment_id == "env_local_dev"
    assert local_conn.connection_type == "local_kubernetes"

    # 2. Mock / custom connection for testing
    class MockFailingConnection(EnvironmentConnection):
        @property
        def environment_id(self):
            return "env_unreachable"

        @property
        def connection_type(self):
            return "agent"

        def is_connected(self):
            return False

        def health_check(self):
            return {"available": False, "error": "Node unreachable"}

        def get_cluster_info(self):
            return None

        def list_namespaces(self):
            return None

        def list_nodes(self):
            return None

        def list_pods(self, namespace=None):
            return None

        def get_pod(self, namespace, name):
            return None

        def list_deployments(self, namespace=None):
            return None

        def get_deployment(self, namespace, name):
            return None

        def list_services(self, namespace=None):
            return None

        def restart_pod(self, namespace, name):
            return False, "Failed"

        def rollout_restart_deployment(self, namespace, name):
            return False, "Failed"

    conn_mgr.set_connection("env_unreachable", MockFailingConnection())

    # Create incident targeting offline environment
    incident = Incident(
        id="INC-9999",
        fingerprint="test:unreachable",
        title="Test Offline Env",
        severity="warning",
        service="payment-service",
        namespace="default",
        pod="payment-service-1234",
        detection_source="Test",
        environment_id="env_unreachable",
        organization_id="org_default",
        recommended_action=RemediationAction.RESTART_POD,
    )

    # Remediation MUST fail safely and not touch Docker Desktop
    success, msg = remediation_svc.execute_remediation(incident)
    assert success is False
    assert "offline" in msg or "not active" in msg


def test_agent_command_dispatch_and_execution_flow(client):
    """Test full command lifecycle: queue on CP -> poll by agent -> result reported to CP."""
    tok_resp = client.post("/api/environments/env_agent_demo/token")
    token = tok_resp.json()["enrollment_token"]

    reg_resp = client.post(
        "/api/agent/register",
        json={
            "environment_id": "env_agent_demo",
            "enrollment_token": token,
            "agent_version": "0.1.0",
            "cluster_name": "customer-prod",
            "kubernetes_version": "v1.28.2",
            "capabilities": ["RESTART_POD", "ROLLOUT_RESTART_DEPLOYMENT", "VERIFY_WORKLOAD"],
        },
    )
    assert reg_resp.status_code == 200
    session_token = reg_resp.json()["session_token"]

    # Send heartbeat
    hb_resp = client.post(
        "/api/agent/heartbeat",
        json={
            "environment_id": "env_agent_demo",
            "session_token": session_token,
            "status": "HEALTHY",
            "cluster_reachable": True,
        },
    )
    assert hb_resp.status_code == 200

    # Queue an approved remediation command via ConnectionManager
    conn_mgr = get_connection_manager()
    agent_conn = conn_mgr.get_connection("env_agent_demo")
    assert agent_conn.is_connected() is True

    # Check cluster info retrieval from agent metadata
    info = agent_conn.get_cluster_info()
    assert info.available is True
    assert info.platform == "customer-prod"

    # Dispatch restart_pod via agent connection
    ok, msg = agent_conn.restart_pod(namespace="eternalops-agent-demo", name="agent-target-workload")
    assert ok is True
    assert "queued" in msg

    # Agent polls for commands
    poll_resp = client.get(
        "/api/agent/commands?environment_id=env_agent_demo",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert poll_resp.status_code == 200
    cmds = poll_resp.json()
    assert len(cmds) == 1
    assert cmds[0]["action"] == "RESTART_POD"
    assert cmds[0]["target_name"] == "agent-target-workload"
    cmd_id = cmds[0]["command_id"]

    # Agent submits result
    res_resp = client.post(
        f"/api/agent/commands/{cmd_id}/result",
        json={
            "command_id": cmd_id,
            "environment_id": "env_agent_demo",
            "action": "RESTART_POD",
            "success": True,
            "output": "Pod deleted and recreated by replica set controller.",
            "duration_seconds": 0.42,
        },
    )
    assert res_resp.status_code == 200
    assert res_resp.json()["acknowledged"] is True

