"""Test Audit logs, in-app notifications, and APIs."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.audit_service import get_audit_service
from app.services.notification_service import get_notification_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_stores():
    get_audit_service().clear()
    get_notification_service().clear()
    yield
    get_audit_service().clear()
    get_notification_service().clear()


def test_audit_logs_creation_and_filtering():
    """Verify audit log entry creation and query API."""
    audit_svc = get_audit_service()
    audit_svc.log("Pod restart", "Healing Engine", "auth-svc", status="Success", incident_id="INC-1001")
    audit_svc.log("Incident escalated", "Safety Policy", "coredns", status="Escalated", incident_id="INC-1002")

    resp = client.get("/api/audit-logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2

    # Filter by status
    resp_filtered = client.get("/api/audit-logs?status=Escalated")
    assert resp_filtered.status_code == 200
    assert resp_filtered.json()["total"] == 1
    assert resp_filtered.json()["logs"][0]["target"] == "coredns"


def test_notifications_creation_and_mark_read():
    """Verify notification flow and mark read endpoints."""
    notif_svc = get_notification_service()
    n1 = notif_svc.notify("Incident Triggered", "High restart on pod", type_="critical")
    n2 = notif_svc.notify("Healing Succeeded", "Pod recovered", type_="success")

    resp = client.get("/api/notifications")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2
    assert resp.json()["unread_count"] == 2

    # Mark n1 read
    resp_read = client.post(f"/api/notifications/{n1.id}/read")
    assert resp_read.status_code == 200

    resp_after = client.get("/api/notifications")
    assert resp_after.json()["unread_count"] == 1
