"""Prometheus HTTP API integration service."""

import logging
from typing import Any, Dict, Optional, Tuple
import httpx

from app.core.config import Settings, get_settings
from app.utils.errors import PrometheusQueryError, PrometheusUnavailableError

logger = logging.getLogger("eternalops.prometheus")


class PrometheusService:
    """Service for interacting with Prometheus HTTP API."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        settings: Settings = get_settings()
        self.base_url = (base_url or settings.PROMETHEUS_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.PROMETHEUS_TIMEOUT_SECONDS

    def _get_client(self) -> httpx.AsyncClient:
        """Create an async HTTP client configured for Prometheus."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        )

    async def check_health(self) -> Tuple[bool, Optional[str]]:
        """
        Check connectivity to the Prometheus server.
        Returns: (is_available, error_message)
        """
        try:
            async with self._get_client() as client:
                # Prometheus provides a /-/healthy probe endpoint
                resp = await client.get("/-/healthy")
                if resp.status_code == 200:
                    return True, None
                # Fallback check query if probe returns non-200
                q_resp = await client.get("/api/v1/query", params={"query": "up"})
                if q_resp.status_code == 200:
                    return True, None
                return False, f"Prometheus returned HTTP {resp.status_code}"
        except httpx.ConnectError:
            logger.warning("Prometheus connection refused at %s", self.base_url)
            return False, f"Connection refused at {self.base_url}"
        except httpx.TimeoutException:
            logger.warning("Prometheus connection timed out at %s", self.base_url)
            return False, f"Connection timed out after {self.timeout}s"
        except Exception as exc:
            logger.warning("Prometheus health check failed: %s", str(exc))
            return False, str(exc)

    async def query_instant(self, query: str, time: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute an instant PromQL query against /api/v1/query.
        """
        params: Dict[str, Any] = {"query": query}
        if time is not None:
            params["time"] = time

        try:
            async with self._get_client() as client:
                resp = await client.get("/api/v1/query", params=params)
                data = resp.json()

                if resp.status_code != 200 or data.get("status") == "error":
                    error_msg = data.get("error", f"Prometheus error HTTP {resp.status_code}")
                    raise PrometheusQueryError(message=error_msg, details=data)

                return data
        except (PrometheusQueryError, PrometheusUnavailableError):
            raise
        except (httpx.ConnectError, httpx.ConnectTimeout):
            logger.error("Unable to connect to Prometheus at %s", self.base_url)
            raise PrometheusUnavailableError(
                message=f"Prometheus server unavailable at {self.base_url}"
            )
        except httpx.TimeoutException:
            logger.error("Prometheus query timed out for query: %s", query)
            raise PrometheusUnavailableError(
                message=f"Prometheus query timed out after {self.timeout}s"
            )
        except Exception as exc:
            logger.error("Unexpected error executing Prometheus query: %s", str(exc))
            raise PrometheusUnavailableError(
                message=f"Prometheus request failed: {str(exc)}"
            )

    async def query_range(
        self,
        query: str,
        start: str,
        end: str,
        step: str,
    ) -> Dict[str, Any]:
        """
        Execute a range PromQL query against /api/v1/query_range.
        """
        params = {
            "query": query,
            "start": start,
            "end": end,
            "step": step,
        }

        try:
            async with self._get_client() as client:
                resp = await client.get("/api/v1/query_range", params=params)
                data = resp.json()

                if resp.status_code != 200 or data.get("status") == "error":
                    error_msg = data.get("error", f"Prometheus error HTTP {resp.status_code}")
                    raise PrometheusQueryError(message=error_msg, details=data)

                return data
        except (PrometheusQueryError, PrometheusUnavailableError):
            raise
        except (httpx.ConnectError, httpx.ConnectTimeout):
            logger.error("Unable to connect to Prometheus at %s", self.base_url)
            raise PrometheusUnavailableError(
                message=f"Prometheus server unavailable at {self.base_url}"
            )
        except httpx.TimeoutException:
            logger.error("Prometheus range query timed out for query: %s", query)
            raise PrometheusUnavailableError(
                message=f"Prometheus query timed out after {self.timeout}s"
            )
        except Exception as exc:
            logger.error("Unexpected error executing Prometheus range query: %s", str(exc))
            raise PrometheusUnavailableError(
                message=f"Prometheus request failed: {str(exc)}"
            )


def get_prometheus_service() -> PrometheusService:
    """Dependency provider for PrometheusService."""
    return PrometheusService()
