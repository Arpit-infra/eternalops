"""Application error definitions."""

from typing import Optional


class EternalOpsException(Exception):
    """Base exception for EternalOps."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class PrometheusUnavailableError(EternalOpsException):
    """Raised when Prometheus server cannot be reached."""

    def __init__(self, message: str = "Prometheus server is unavailable", details: Optional[dict] = None):
        super().__init__(message=message, status_code=503, details=details)


class PrometheusQueryError(EternalOpsException):
    """Raised when Prometheus returns a query execution error."""

    def __init__(self, message: str = "Prometheus query failed", details: Optional[dict] = None):
        super().__init__(message=message, status_code=400, details=details)


class KubernetesUnavailableError(EternalOpsException):
    """Raised when Kubernetes cluster cannot be reached or initialized."""

    def __init__(self, message: str = "Kubernetes cluster is unavailable", details: Optional[dict] = None):
        super().__init__(message=message, status_code=503, details=details)
