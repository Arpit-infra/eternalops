"""Test Prometheus endpoints and error handling."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.prometheus_service import PrometheusService, get_prometheus_service
from app.utils.errors import PrometheusQueryError, PrometheusUnavailableError

client = TestClient(app)


def test_prometheus_status_connected():
    """Test prometheus status endpoint when available."""
    class MockService:
        async def check_health(self):
            return True, None

    app.dependency_overrides[get_prometheus_service] = lambda: MockService()
    try:
        response = client.get("/api/prometheus/status")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["status"] == "connected"
        assert data["error"] is None
    finally:
        app.dependency_overrides.clear()


def test_prometheus_status_unavailable():
    """Test prometheus status endpoint when unreachable."""
    class MockService:
        async def check_health(self):
            return False, "Connection refused at http://localhost:9090"

    app.dependency_overrides[get_prometheus_service] = lambda: MockService()
    try:
        response = client.get("/api/prometheus/status")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert data["status"] == "unavailable"
        assert "Connection refused" in data["error"]
    finally:
        app.dependency_overrides.clear()


def test_prometheus_instant_query_success():
    """Test successful instant query routing."""
    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {"metric": {"__name__": "up", "instance": "localhost:9090", "job": "prometheus"}, "value": [1700000000, "1"]}
            ],
        },
    }

    class MockService:
        async def query_instant(self, query: str, time=None):
            return mock_payload

    app.dependency_overrides[get_prometheus_service] = lambda: MockService()
    try:
        response = client.get("/api/prometheus/query?query=up")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["resultType"] == "vector"
        assert len(data["data"]["result"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_prometheus_instant_query_unavailable():
    """Test instant query when Prometheus service is unavailable."""
    class MockService:
        async def query_instant(self, query: str, time=None):
            raise PrometheusUnavailableError("Prometheus server unavailable at http://localhost:9090")

    app.dependency_overrides[get_prometheus_service] = lambda: MockService()
    try:
        response = client.get("/api/prometheus/query?query=up")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["available"] is False
    finally:
        app.dependency_overrides.clear()


def test_prometheus_range_query_success():
    """Test successful range query routing."""
    mock_payload = {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {"__name__": "up"},
                    "values": [[1700000000, "1"], [1700000060, "1"]],
                }
            ],
        },
    }

    class MockService:
        async def query_range(self, query: str, start: str, end: str, step: str):
            return mock_payload

    app.dependency_overrides[get_prometheus_service] = lambda: MockService()
    try:
        response = client.get(
            "/api/prometheus/query-range?query=up&start=1700000000&end=1700000060&step=60s"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["resultType"] == "matrix"
    finally:
        app.dependency_overrides.clear()
