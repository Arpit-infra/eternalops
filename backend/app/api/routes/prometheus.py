"""Prometheus metric query and status routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.core.config import Settings, get_settings
from app.schemas.prometheus import PrometheusQueryResponse, PrometheusStatusResponse
from app.services.prometheus_service import PrometheusService, get_prometheus_service
from app.utils.errors import PrometheusQueryError, PrometheusUnavailableError

router = APIRouter(prefix="/prometheus", tags=["Prometheus"])


@router.get(
    "/status",
    response_model=PrometheusStatusResponse,
    summary="Check Prometheus connectivity status",
)
async def get_prometheus_status(
    service: PrometheusService = Depends(get_prometheus_service),
    settings: Settings = Depends(get_settings),
) -> PrometheusStatusResponse:
    """
    Check if the configured Prometheus instance is reachable.
    """
    is_available, error_msg = await service.check_health()
    return PrometheusStatusResponse(
        available=is_available,
        url=settings.PROMETHEUS_URL,
        status="connected" if is_available else "unavailable",
        error=error_msg,
    )


@router.get(
    "/query",
    response_model=PrometheusQueryResponse,
    summary="Execute instant PromQL query",
)
async def execute_instant_query(
    query: str = Query(..., description="PromQL query expression, e.g. 'up' or 'process_cpu_seconds_total'"),
    time: Optional[str] = Query(None, description="Evaluation timestamp (RFC3339 or Unix timestamp)"),
    service: PrometheusService = Depends(get_prometheus_service),
) -> PrometheusQueryResponse:
    """
    Execute an instant PromQL query against the configured Prometheus instance.
    """
    try:
        data = await service.query_instant(query=query, time=time)
        return PrometheusQueryResponse(
            status=data.get("status", "success"),
            data=data.get("data"),
            warnings=data.get("warnings"),
        )
    except PrometheusUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"available": False, "error": exc.message, "details": exc.details},
        )
    except PrometheusQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "error": exc.message, "details": exc.details},
        )


@router.get(
    "/query-range",
    response_model=PrometheusQueryResponse,
    summary="Execute range PromQL query",
)
async def execute_range_query(
    query: str = Query(..., description="PromQL query expression"),
    start: str = Query(..., description="Start timestamp (RFC3339 or Unix timestamp)"),
    end: str = Query(..., description="End timestamp (RFC3339 or Unix timestamp)"),
    step: str = Query(..., description="Query resolution step width (e.g. '15s', '1m')"),
    service: PrometheusService = Depends(get_prometheus_service),
) -> PrometheusQueryResponse:
    """
    Execute a range PromQL query against the configured Prometheus instance over a time interval.
    """
    try:
        data = await service.query_range(query=query, start=start, end=end, step=step)
        return PrometheusQueryResponse(
            status=data.get("status", "success"),
            data=data.get("data"),
            warnings=data.get("warnings"),
        )
    except PrometheusUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"available": False, "error": exc.message, "details": exc.details},
        )
    except PrometheusQueryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"status": "error", "error": exc.message, "details": exc.details},
        )
