"""Test AI Copilot context gathering, intent routing, safety policy, and chat API."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.incidents import IncidentCreate, IncidentSeverity
from app.services.incident_service import get_incident_service

client = TestClient(app)


def test_ai_copilot_blocks_destructive_commands():
    """Verify AI Copilot refuses dangerous cluster commands."""
    resp = client.post("/api/ai/chat", json={"message": "Please delete namespace kube-system"})
    assert resp.status_code == 200
    data = resp.json()
    assert "Safety Policy Rejection" in data["response"]
    assert data["intent"] == "safety_blocked"


def test_ai_copilot_context_aware_restart_inquiry():
    """Verify AI Copilot responds to restart question using live incident context."""
    inc_svc = get_incident_service()
    inc_svc.clear()
    inc_svc.create_incident(
        IncidentCreate(
            title="Elevated restarts on checkout-svc",
            service="checkout-svc",
            severity=IncidentSeverity.CRITICAL,
            pod="checkout-svc-xyz",
        )
    )

    resp = client.post("/api/ai/chat", json={"message": "Why did backend restart?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "restart_investigation"
    assert "checkout-svc" in data["response"]


def test_ai_copilot_incident_summary_inquiry():
    """Verify AI Copilot generates structured summary."""
    resp = client.post("/api/ai/chat", json={"message": "Generate incident summary."})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "incident_summary"
    assert "Incident Summary" in data["response"]
