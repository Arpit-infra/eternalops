"""Test Incident creation, lifecycle transitions, and API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.incidents import HealingStage, IncidentCreate, IncidentSeverity, IncidentStatus
from app.services.incident_service import IncidentService, get_incident_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_incidents():
    """Reset in-memory incidents before each test."""
    service = get_incident_service()
    service.clear()
    yield
    service.clear()


def test_create_and_get_incident():
    """Verify incident creation and retrieval."""
    service = get_incident_service()
    data = IncidentCreate(
        title="High restart count on auth-svc",
        description="Container restarted 3 times",
        severity=IncidentSeverity.CRITICAL,
        service="auth-svc",
        namespace="default",
        pod="auth-svc-789a",
        fingerprint="default:pod_restart:auth-svc-789a",
    )
    inc = service.create_incident(data)
    assert inc.id.startswith("INC-")
    assert inc.status == IncidentStatus.OPEN
    assert inc.healing_stage == HealingStage.DETECTION

    fetched = service.get_by_id(inc.id)
    assert fetched is not None
    assert fetched.title == data.title
    assert fetched.service == "auth-svc"


def test_incident_deduplication_by_fingerprint():
    """Verify active incidents are deduplicated by fingerprint."""
    service = get_incident_service()
    fp = "default:deployment_unavailable:payment-svc"
    data = IncidentCreate(
        title="Deployment replica mismatch",
        service="payment-svc",
        fingerprint=fp,
    )
    inc1 = service.create_incident(data)
    existing = service.get_by_fingerprint(fp)
    assert existing is not None
    assert existing.id == inc1.id

    # Resolve incident
    service.set_stage(inc1.id, HealingStage.RESOLVED, IncidentStatus.RESOLVED)
    # Once resolved, fingerprint should not match active incident
    assert service.get_by_fingerprint(fp) is None


def test_list_incidents_api():
    """Test GET /api/incidents endpoint with filters."""
    service = get_incident_service()
    service.create_incident(
        IncidentCreate(title="Warning incident", severity=IncidentSeverity.WARNING, service="svc-1")
    )
    service.create_incident(
        IncidentCreate(title="Critical incident", severity=IncidentSeverity.CRITICAL, service="svc-2")
    )

    resp = client.get("/api/incidents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["active_count"] == 2

    # Filter by severity
    resp_crit = client.get("/api/incidents?severity=critical")
    assert resp_crit.status_code == 200
    assert resp_crit.json()["total"] == 1
    assert resp_crit.json()["incidents"][0]["severity"] == "critical"


def test_test_incident_creation_endpoint():
    """Test POST /api/incidents/test endpoint."""
    resp = client.post("/api/incidents/test", json={"service": "test-microservice", "simulate_escalation": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"].startswith("INC-")
    assert "test-microservice" in data["title"]
