"""Test Kubernetes endpoints and error handling."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.kubernetes import (
    ClusterInfoResponse,
    DeploymentItem,
    DeploymentsResponse,
    NamespaceItem,
    NamespacesResponse,
    NodeItem,
    NodesResponse,
    PodContainerStatus,
    PodItem,
    PodsResponse,
    ServiceItem,
    ServicesResponse,
)
from app.services.kubernetes_service import KubernetesService, get_kubernetes_service

client = TestClient(app)


def test_kubernetes_status_endpoint_unavailable():
    """Test Kubernetes status when cluster is down."""
    class MockService:
        def get_status(self):
            return {
                "available": False,
                "in_cluster": False,
                "context": None,
                "cluster_version": None,
                "error": "Kubernetes cluster is unavailable",
            }

    app.dependency_overrides[get_kubernetes_service] = lambda: MockService()
    try:
        response = client.get("/api/kubernetes/status")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False
        assert "Kubernetes cluster is unavailable" in data["error"]
    finally:
        app.dependency_overrides.clear()


def test_kubernetes_cluster_info():
    """Test /api/kubernetes/cluster response."""
    class MockService:
        def get_cluster_info(self):
            return ClusterInfoResponse(
                available=True,
                git_version="v1.30.0",
                major="1",
                minor="30",
                platform="linux/amd64",
                error=None,
            )

    app.dependency_overrides[get_kubernetes_service] = lambda: MockService()
    try:
        response = client.get("/api/kubernetes/cluster")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["git_version"] == "v1.30.0"
    finally:
        app.dependency_overrides.clear()


def test_kubernetes_namespaces():
    """Test /api/kubernetes/namespaces."""
    class MockService:
        def get_namespaces(self):
            return NamespacesResponse(
                available=True,
                total=2,
                namespaces=[
                    NamespaceItem(name="default", status="Active"),
                    NamespaceItem(name="kube-system", status="Active"),
                ],
            )

    app.dependency_overrides[get_kubernetes_service] = lambda: MockService()
    try:
        response = client.get("/api/kubernetes/namespaces")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["total"] == 2
        assert data["namespaces"][0]["name"] == "default"
    finally:
        app.dependency_overrides.clear()


def test_kubernetes_nodes():
    """Test /api/kubernetes/nodes."""
    class MockService:
        def get_nodes(self):
            return NodesResponse(
                available=True,
                total=1,
                nodes=[
                    NodeItem(
                        name="minikube",
                        status="Ready",
                        cpu_capacity="8",
                        memory_capacity="16384Ki",
                        os_image="Ubuntu 22.04",
                        kubelet_version="v1.30.0",
                        architecture="amd64",
                    )
                ],
            )

    app.dependency_overrides[get_kubernetes_service] = lambda: MockService()
    try:
        response = client.get("/api/kubernetes/nodes")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["total"] == 1
        assert data["nodes"][0]["name"] == "minikube"
        assert data["nodes"][0]["status"] == "Ready"
    finally:
        app.dependency_overrides.clear()


def test_kubernetes_pods():
    """Test /api/kubernetes/pods."""
    class MockService:
        def get_pods(self, namespace=None):
            return PodsResponse(
                available=True,
                total=1,
                pods=[
                    PodItem(
                        namespace="default",
                        name="auth-service-7f89d",
                        phase="Running",
                        node_name="node-1",
                        restart_count=0,
                        containers=[
                            PodContainerStatus(
                                name="auth-container",
                                ready=True,
                                restart_count=0,
                                state="running",
                            )
                        ],
                    )
                ],
            )

    app.dependency_overrides[get_kubernetes_service] = lambda: MockService()
    try:
        response = client.get("/api/kubernetes/pods")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["total"] == 1
        assert data["pods"][0]["name"] == "auth-service-7f89d"
    finally:
        app.dependency_overrides.clear()


def test_kubernetes_deployments():
    """Test /api/kubernetes/deployments."""
    class MockService:
        def get_deployments(self, namespace=None):
            return DeploymentsResponse(
                available=True,
                total=1,
                deployments=[
                    DeploymentItem(
                        namespace="default",
                        name="payment-svc",
                        desired_replicas=3,
                        ready_replicas=3,
                        available_replicas=3,
                        updated_replicas=3,
                    )
                ],
            )

    app.dependency_overrides[get_kubernetes_service] = lambda: MockService()
    try:
        response = client.get("/api/kubernetes/deployments")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["total"] == 1
        assert data["deployments"][0]["name"] == "payment-svc"
    finally:
        app.dependency_overrides.clear()


def test_kubernetes_services():
    """Test /api/kubernetes/services."""
    class MockService:
        def get_services(self, namespace=None):
            return ServicesResponse(
                available=True,
                total=1,
                services=[
                    ServiceItem(
                        namespace="default",
                        name="api-gateway",
                        type="LoadBalancer",
                        cluster_ip="10.96.0.1",
                        ports=[],
                    )
                ],
            )

    app.dependency_overrides[get_kubernetes_service] = lambda: MockService()
    try:
        response = client.get("/api/kubernetes/services")
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["total"] == 1
        assert data["services"][0]["name"] == "api-gateway"
    finally:
        app.dependency_overrides.clear()


def test_kubernetes_service_initialization_with_empty_context(monkeypatch):
    """Test that empty string context is treated as None and calls load_kube_config without context."""
    from unittest.mock import MagicMock
    from kubernetes import config

    mock_load_kube_config = MagicMock()
    mock_list_contexts = MagicMock(return_value=([{"name": "docker-desktop"}], {"name": "docker-desktop"}))

    monkeypatch.setattr(config, "load_kube_config", mock_load_kube_config)
    monkeypatch.setattr(config, "list_kube_config_contexts", mock_list_contexts)

    svc = KubernetesService(in_cluster=False, context="")
    assert svc.context is None
    assert svc._is_configured is True
    assert svc._active_context == "docker-desktop"
    mock_load_kube_config.assert_called_once_with()

