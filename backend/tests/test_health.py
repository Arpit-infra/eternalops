"""Test health and root endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.prometheus_service import PrometheusService, get_prometheus_service
from app.services.kubernetes_service import KubernetesService, get_kubernetes_service

client = TestClient(app)


def test_root_endpoint():
    """Verify root endpoint returns app metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "EternalOps Backend"
    assert "version" in data
    assert data["health_url"] == "/api/health"


def test_health_endpoint_structure():
    """Verify /api/health returns structured status without crashing."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "eternalops-backend"
    assert "prometheus" in data
    assert "available" in data["prometheus"]
    assert "kubernetes" in data
    assert "available" in data["kubernetes"]


def test_health_with_mocked_available_services():
    """Test health endpoint when both services report available."""
    class MockPromService:
        async def check_health(self):
            return True, None

    class MockK8sService:
        def get_status(self):
            return {"available": True, "cluster_version": "v1.30.0", "in_cluster": False, "context": "minikube"}

    app.dependency_overrides[get_prometheus_service] = lambda: MockPromService()
    app.dependency_overrides[get_kubernetes_service] = lambda: MockK8sService()

    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["prometheus"]["available"] is True
        assert data["kubernetes"]["available"] is True
    finally:
        app.dependency_overrides.clear()


def test_health_with_mocked_unavailable_services():
    """Test health endpoint when services are down; API must stay operational (status 200)."""
    class MockPromService:
        async def check_health(self):
            return False, "Connection refused"

    class MockK8sService:
        def get_status(self):
            return {"available": False, "error": "Cluster unreachable", "in_cluster": False, "context": None}

    app.dependency_overrides[get_prometheus_service] = lambda: MockPromService()
    app.dependency_overrides[get_kubernetes_service] = lambda: MockK8sService()

    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["prometheus"]["available"] is False
        assert data["kubernetes"]["available"] is False
    finally:
        app.dependency_overrides.clear()


def test_health_summary_and_workloads_endpoints():
    """Test new GET /api/health/summary and GET /api/health/workloads endpoints."""
    resp = client.get("/api/health/summary")
    assert resp.status_code == 200
    summary = resp.json()
    assert "status" in summary
    assert "kubernetes_connected" in summary
    assert "prometheus_connected" in summary
    assert "active_incidents_count" in summary
    assert "recovering_count" in summary
    assert "auto_recovered_count" in summary
    assert "escalated_count" in summary

    resp_workloads = client.get("/api/health/workloads")
    assert resp_workloads.status_code == 200
    workloads = resp_workloads.json()
    assert "total" in workloads
    assert "workloads" in workloads

