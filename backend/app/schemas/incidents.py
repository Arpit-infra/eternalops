"""Incident domain models and schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ANALYZING = "ANALYZING"
    HEALING = "HEALING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


class IncidentSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class HealingStage(str, Enum):
    DETECTION = "DETECTION"
    ANALYSIS = "ANALYSIS"
    DECISION = "DECISION"
    HEALING = "HEALING"
    VERIFICATION = "VERIFICATION"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class RemediationAction(str, Enum):
    RESTART_POD = "RESTART_POD"
    ROLLOUT_RESTART_DEPLOYMENT = "ROLLOUT_RESTART_DEPLOYMENT"
    SCALE_DEPLOYMENT = "SCALE_DEPLOYMENT"
    NONE = "NONE"


class IncidentBase(BaseModel):
    title: str = Field(..., description="Short descriptive title of the incident")
    description: Optional[str] = Field(None, description="Detailed description of the anomaly")
    severity: IncidentSeverity = Field(IncidentSeverity.WARNING, description="Severity level")
    service: str = Field(..., description="Affected service or workload name")
    namespace: str = Field("default", description="Kubernetes namespace")
    pod: Optional[str] = Field(None, description="Affected Kubernetes pod if applicable")
    deployment: Optional[str] = Field(None, description="Affected Kubernetes deployment if applicable")
    detection_source: str = Field("Prometheus", description="Detection source system")
    organization_id: str = Field("org_default", description="Organization / Tenant scope")
    environment_id: str = Field("env_local_dev", description="Target environment ID")


class IncidentCreate(IncidentBase):
    fingerprint: Optional[str] = Field(None, description="Unique anomaly deduplication key")
    metrics: Optional[str] = Field(None, description="Snapshot summary of triggering metrics")
    logs: Optional[str] = Field(None, description="Sample logs or error message")


class Incident(IncidentBase):
    id: str = Field(..., description="Unique incident identifier, e.g. INC-1001")
    fingerprint: str = Field(..., description="Anomaly deduplication key")
    status: IncidentStatus = Field(IncidentStatus.OPEN, description="Current incident lifecycle status")
    healing_stage: HealingStage = Field(HealingStage.DETECTION, description="Current workflow stage")
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="Time detected")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    started_at: Optional[datetime] = Field(None, description="When healing started")
    resolved_at: Optional[datetime] = Field(None, description="When incident was resolved")
    recovery_seconds: Optional[float] = Field(None, description="Elapsed recovery duration in seconds")
    recovery_duration: Optional[str] = Field(None, description="Formatted recovery duration (e.g. 45s)")
    
    # Telemetry and Root Cause Analysis
    metrics: Optional[str] = Field(None, description="Telemetry metrics summary")
    raw_telemetry: Optional[Dict[str, Any]] = Field(default=None, description="Raw feature metrics")
    logs: Optional[str] = Field(None, description="Relevant logs")
    root_cause: Optional[str] = Field(None, description="AI/Engine identified root cause")
    confidence: Optional[int] = Field(None, description="Confidence percentage (0-100)")
    
    # Decision and Action
    recommended_action: Optional[RemediationAction] = Field(None, description="Action recommended by engine")
    selected_action: Optional[str] = Field(None, description="Human-readable executed action description")
    requires_human: bool = Field(False, description="True if automatic remediation is unsafe")
    
    # Verification and Escalation
    verification_status: Optional[str] = Field(None, description="Status of recovery verification")
    error: Optional[str] = Field(None, description="Error message if remediation failed")
    escalated: bool = Field(False, description="True if incident was escalated")
    escalation_reason: Optional[str] = Field(None, description="Reason for escalation")


class IncidentsListResponse(BaseModel):
    total: int = Field(..., description="Total incidents matching query")
    active_count: int = Field(..., description="Count of open/analyzing/healing incidents")
    resolved_count: int = Field(..., description="Count of resolved incidents")
    escalated_count: int = Field(..., description="Count of escalated incidents")
    incidents: List[Incident] = Field(..., description="List of incidents")


class IncidentActionResponse(BaseModel):
    success: bool
    incident: Incident
    message: str


class IncidentTestRequest(BaseModel):
    service: Optional[str] = Field("demo-service", description="Service name for test incident")
    namespace: Optional[str] = Field("default", description="Namespace")
    pod: Optional[str] = Field(None, description="Optional pod name")
    deployment: Optional[str] = Field(None, description="Optional deployment name")
    severity: Optional[IncidentSeverity] = Field(IncidentSeverity.WARNING, description="Severity")
    action: Optional[str] = Field("RESTART_POD", description="Simulated remediation action")
    simulate_escalation: bool = Field(False, description="Simulate unhealable failure leading to escalation")
    organization_id: Optional[str] = Field("org_default", description="Target organization")
    environment_id: Optional[str] = Field("env_local_dev", description="Target environment")
