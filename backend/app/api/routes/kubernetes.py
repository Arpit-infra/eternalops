"""Kubernetes read-only inspection routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.schemas.kubernetes import (
    ClusterInfoResponse,
    DeploymentsResponse,
    KubernetesStatusResponse,
    NamespacesResponse,
    NodesResponse,
    PodsResponse,
    ServicesResponse,
)
from app.services.kubernetes_service import KubernetesService, get_kubernetes_service

router = APIRouter(prefix="/kubernetes", tags=["Kubernetes"])


@router.get(
    "/status",
    response_model=KubernetesStatusResponse,
    summary="Check Kubernetes cluster connectivity status",
)
def get_kubernetes_status(
    service: KubernetesService = Depends(get_kubernetes_service),
) -> KubernetesStatusResponse:
    """
    Check if the Kubernetes cluster API is reachable and configured.
    """
    status_info = service.get_status()
    return KubernetesStatusResponse(
        available=status_info["available"],
        in_cluster=status_info["in_cluster"],
        context=status_info.get("context"),
        cluster_version=status_info.get("cluster_version"),
        error=status_info.get("error"),
    )


@router.get(
    "/cluster",
    response_model=ClusterInfoResponse,
    summary="Get Kubernetes cluster server information",
)
def get_cluster_info(
    service: KubernetesService = Depends(get_kubernetes_service),
) -> ClusterInfoResponse:
    """
    Retrieve Kubernetes server version and platform details.
    """
    return service.get_cluster_info()


@router.get(
    "/namespaces",
    response_model=NamespacesResponse,
    summary="List all namespaces",
)
def get_namespaces(
    service: KubernetesService = Depends(get_kubernetes_service),
) -> NamespacesResponse:
    """
    Retrieve list of namespaces in the Kubernetes cluster.
    """
    return service.get_namespaces()


@router.get(
    "/nodes",
    response_model=NodesResponse,
    summary="List cluster nodes and capacity",
)
def get_nodes(
    service: KubernetesService = Depends(get_kubernetes_service),
) -> NodesResponse:
    """
    Retrieve list of nodes, ready status, and compute capacity.
    """
    return service.get_nodes()


@router.get(
    "/pods",
    response_model=PodsResponse,
    summary="List cluster pods",
)
def get_pods(
    namespace: Optional[str] = Query(None, description="Optional namespace to filter pods"),
    service: KubernetesService = Depends(get_kubernetes_service),
) -> PodsResponse:
    """
    Retrieve list of pods, their phase, restart counts, and container statuses.
    """
    return service.get_pods(namespace=namespace)


@router.get(
    "/deployments",
    response_model=DeploymentsResponse,
    summary="List deployments",
)
def get_deployments(
    namespace: Optional[str] = Query(None, description="Optional namespace to filter deployments"),
    service: KubernetesService = Depends(get_kubernetes_service),
) -> DeploymentsResponse:
    """
    Retrieve list of deployments, desired/ready/available replicas.
    """
    return service.get_deployments(namespace=namespace)


@router.get(
    "/services",
    response_model=ServicesResponse,
    summary="List services",
)
def get_services(
    namespace: Optional[str] = Query(None, description="Optional namespace to filter services"),
    service: KubernetesService = Depends(get_kubernetes_service),
) -> ServicesResponse:
    """
    Retrieve list of services, types, cluster IPs, and port configurations.
    """
    return service.get_services(namespace=namespace)
