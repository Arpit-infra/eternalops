"""EternalOps FastAPI Backend Main Entrypoint."""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from app.api.router import api_router
from app.core.config import get_settings
from app.schemas.common import RootResponse
from app.services.detection_service import get_detection_service
from app.utils.errors import EternalOpsException

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("eternalops.main")

# Prometheus Metrics Instrumentation
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds for EternalOps backend endpoints",
    ["method", "path", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
)
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received by EternalOps backend",
    ["method", "path", "status_code"],
)
APP_INFO = Gauge(
    "eternalops_app_info",
    "EternalOps backend platform runtime information",
    ["version", "app_name"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown hooks."""
    settings = get_settings()
    logger.info("Starting EternalOps Backend v%s", settings.VERSION)
    logger.info("Prometheus URL: %s", settings.PROMETHEUS_URL)
    logger.info("Kubernetes In-Cluster: %s", settings.KUBERNETES_IN_CLUSTER)
    logger.info("CORS Origins: %s", settings.cors_origins_list)

    APP_INFO.labels(version=settings.VERSION, app_name=settings.PROJECT_NAME).set(1)

    # Start background detection loop
    detector = get_detection_service()
    detector.start()
    logger.info("Detection Engine loop started successfully.")

    yield

    logger.info("Shutting down EternalOps Backend...")
    detector.stop()
    logger.info("Detection Engine loop stopped.")


settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="EternalOps - AI-Powered Cloud Native Self-Healing DevOps Platform Backend API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    """Middleware to record real HTTP request duration and request counts."""
    # Exclude /metrics itself to avoid circular telemetry noise
    if request.url.path == "/metrics":
        return await call_next(request)

    start_time = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = max(0.0, time.time() - start_time)
        path = request.url.path
        # Normalize dynamic path patterns
        if path.startswith("/api/incidents/") and len(path.split("/")) > 3:
            path = "/api/incidents/{id}/" + "/".join(path.split("/")[4:])
        elif path.startswith("/api/environments/") and len(path.split("/")) > 3:
            path = "/api/environments/{id}/" + "/".join(path.split("/")[4:])
        elif path.startswith("/api/agent/commands/") and len(path.split("/")) > 4:
            path = "/api/agent/commands/{id}/result"

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            path=path,
            status_code=str(status_code),
        ).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            path=path,
            status_code=str(status_code),
        ).inc()


# Register API routes under /api
app.include_router(api_router)


@app.get("/metrics", tags=["Telemetry"], summary="Prometheus Metrics Scrape Endpoint")
def get_metrics():
    """Exposes real Prometheus metrics for backend request latency, rates, and health."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(EternalOpsException)
async def eternalops_exception_handler(request: Request, exc: EternalOpsException):
    """Custom exception handler for EternalOps business errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )


@app.get("/", response_model=RootResponse, tags=["Root"], summary="API Root")
async def root() -> RootResponse:
    """EternalOps API root information."""
    return RootResponse(
        name=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs",
        health_url="/api/health",
    )
