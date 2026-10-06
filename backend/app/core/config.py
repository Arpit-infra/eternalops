"""Application Configuration Module."""

from functools import lru_cache
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    # Server Configuration
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    PROJECT_NAME: str = "EternalOps Backend"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # CORS Configuration
    CORS_ORIGINS: str = "http://localhost:5173"

    # Prometheus Configuration
    PROMETHEUS_URL: str = "http://localhost:9090"
    PROMETHEUS_TIMEOUT_SECONDS: float = 10.0

    # Kubernetes Configuration
    KUBERNETES_IN_CLUSTER: bool = False
    KUBERNETES_CONTEXT: Optional[str] = None
    KUBERNETES_TIMEOUT_SECONDS: float = 2.0

    # Control Plane & Multi-Environment Configuration
    DEFAULT_ORGANIZATION_ID: str = "org_default"
    DEFAULT_ORGANIZATION_NAME: str = "EternalOps Development"
    DEFAULT_ENVIRONMENT_ID: str = "env_local_dev"
    DEFAULT_ENVIRONMENT_NAME: str = "Local Development"
    CONNECTION_TYPE: str = "local_kubernetes"
    AGENT_ENABLED: bool = True
    AGENT_HEARTBEAT_INTERVAL_SECONDS: int = 30
    AGENT_CONNECTION_TIMEOUT_SECONDS: int = 90

    # Self-Healing & Detection Configuration
    HEALING_ENABLED: bool = True
    AUTO_HEAL_CONFIDENCE_THRESHOLD: float = 0.80
    VERIFICATION_TIMEOUT_SECONDS: float = 60.0
    VERIFICATION_POLL_INTERVAL_SECONDS: float = 3.0
    DETECTION_INTERVAL_SECONDS: float = 15.0
    PROTECTED_NAMESPACES: List[str] = ["kube-system", "kube-public", "kube-node-lease", "local-path-storage"]

    @field_validator("KUBERNETES_CONTEXT", mode="before")
    @classmethod
    def validate_kubernetes_context(cls, v: Optional[str]) -> Optional[str]:
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a parsed list of strings."""
        if not self.CORS_ORIGINS:
            return ["http://localhost:5173"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
