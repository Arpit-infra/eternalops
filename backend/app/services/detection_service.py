"""Prometheus Anomaly Detection Service and Polling Loop."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.config import Settings, get_settings
from app.schemas.incidents import IncidentCreate, IncidentSeverity
from app.services.healing_orchestrator import HealingOrchestrator, get_healing_orchestrator
from app.services.incident_service import IncidentService, get_incident_service
from app.services.prometheus_service import PrometheusService, get_prometheus_service

logger = logging.getLogger("eternalops.detection")


class DetectionService:
    """Evaluates real Prometheus telemetry to detect cluster anomalies with deduplication."""

    def __init__(
        self,
        prometheus_service: Optional[PrometheusService] = None,
        incident_service: Optional[IncidentService] = None,
        orchestrator: Optional[HealingOrchestrator] = None,
        settings: Optional[Settings] = None,
    ):
        self.prom = prometheus_service or get_prometheus_service()
        self.incidents = incident_service or get_incident_service()
        self.orchestrator = orchestrator or get_healing_orchestrator()
        self.settings = settings or get_settings()
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._known_restart_counts: Dict[str, int] = {}
        self._consecutive_prom_errors = 0

    async def scan_anomalies(self) -> List[IncidentCreate]:
        """Query Prometheus for anomalies across pods, deployments, and services."""
        anomalies: List[IncidentCreate] = []

        is_healthy, err = await self.prom.check_health()
        if not is_healthy:
            if self._consecutive_prom_errors == 0:
                logger.warning("[Detection] Prometheus unreachable: %s. Skipping anomaly scan.", err)
            self._consecutive_prom_errors += 1
            return []

        self._consecutive_prom_errors = 0

        # 1. Check Pod Restarts: sum by (namespace, pod) (kube_pod_container_status_restarts_total)
        try:
            res = await self.prom.query_instant("sum by (namespace, pod) (kube_pod_container_status_restarts_total)")
            if res.get("status") == "success" and res.get("data", {}).get("result"):
                for item in res["data"]["result"]:
                    pod_name = item.get("metric", {}).get("pod")
                    ns = item.get("metric", {}).get("namespace", "default")
                    val_str = item.get("value", [0, "0"])[1]
                    restarts = int(float(val_str))

                    if pod_name and restarts > 0:
                        key = f"{ns}/{pod_name}"
                        prev = self._known_restart_counts.get(key, 0)
                        self._known_restart_counts[key] = restarts

                        # Anomaly flagged if restarts > 0 and is new or increased
                        if restarts > prev:
                            fingerprint = f"{ns}:pod_restart:{pod_name}"
                            service_name = pod_name.split("-")[0] if "-" in pod_name else pod_name
                            anomalies.append(
                                IncidentCreate(
                                    title=f"Elevated restart count on {pod_name} (x{restarts})",
                                    description=f"Prometheus detected container restarts totaling {restarts} for pod {pod_name} in namespace {ns}.",
                                    severity=IncidentSeverity.CRITICAL if restarts >= 3 else IncidentSeverity.WARNING,
                                    service=service_name,
                                    namespace=ns,
                                    pod=pod_name,
                                    detection_source="Prometheus (Kube State Metrics)",
                                    organization_id=self.settings.DEFAULT_ORGANIZATION_ID,
                                    environment_id=self.settings.DEFAULT_ENVIRONMENT_ID,
                                    fingerprint=fingerprint,
                                    metrics=f"Restart count: {restarts} · Pod: {pod_name} · Namespace: {ns}",
                                    logs=f"KSM alert: kube_pod_container_status_restarts_total={restarts}",
                                )
                            )
        except Exception as exc:
            logger.debug("[Detection] Pod restart query error: %s", str(exc))

        # 2. Check Unavailable Deployments: available < desired
        try:
            spec_res = await self.prom.query_instant("kube_deployment_spec_replicas")
            avail_res = await self.prom.query_instant("kube_deployment_status_replicas_available")

            specs: Dict[str, int] = {}
            if spec_res.get("status") == "success" and spec_res.get("data", {}).get("result"):
                for item in spec_res["data"]["result"]:
                    d_name = item.get("metric", {}).get("deployment")
                    ns = item.get("metric", {}).get("namespace", "default")
                    if d_name:
                        specs[f"{ns}/{d_name}"] = int(float(item.get("value", [0, "0"])[1]))

            if avail_res.get("status") == "success" and avail_res.get("data", {}).get("result"):
                for item in avail_res["data"]["result"]:
                    d_name = item.get("metric", {}).get("deployment")
                    ns = item.get("metric", {}).get("namespace", "default")
                    if d_name:
                        avail = int(float(item.get("value", [0, "0"])[1]))
                        desired = specs.get(f"{ns}/{d_name}", 0)
                        if desired > 0 and avail < desired:
                            fingerprint = f"{ns}:deployment_unavailable:{d_name}"
                            anomalies.append(
                                IncidentCreate(
                                    title=f"Deployment replica mismatch on {d_name} ({avail}/{desired} available)",
                                    description=f"Deployment {d_name} in namespace {ns} has {avail} ready replicas out of {desired} desired.",
                                    severity=IncidentSeverity.CRITICAL if avail == 0 else IncidentSeverity.WARNING,
                                    service=d_name,
                                    namespace=ns,
                                    deployment=d_name,
                                    detection_source="Prometheus (Kube State Metrics)",
                                    organization_id=self.settings.DEFAULT_ORGANIZATION_ID,
                                    environment_id=self.settings.DEFAULT_ENVIRONMENT_ID,
                                    fingerprint=fingerprint,
                                    metrics=f"Desired: {desired} · Available: {avail} · Missing: {desired - avail}",
                                    logs=f"KSM alert: kube_deployment_status_replicas_available ({avail}) < spec ({desired})",
                                )
                            )
        except Exception as exc:
            logger.debug("[Detection] Deployment query error: %s", str(exc))

        # 3. Check Failed Pods: kube_pod_status_phase{phase="Failed"} == 1
        try:
            failed_res = await self.prom.query_instant('sum by (namespace, pod) (kube_pod_status_phase{phase="Failed"} == 1)')
            if failed_res.get("status") == "success" and failed_res.get("data", {}).get("result"):
                for item in failed_res["data"]["result"]:
                    pod_name = item.get("metric", {}).get("pod")
                    ns = item.get("metric", {}).get("namespace", "default")
                    if pod_name:
                        fingerprint = f"{ns}:pod_failed:{pod_name}"
                        service_name = pod_name.split("-")[0] if "-" in pod_name else pod_name
                        anomalies.append(
                            IncidentCreate(
                                title=f"Pod {pod_name} entered Failed phase",
                                description=f"Pod {pod_name} in namespace {ns} terminated with phase Failed.",
                                severity=IncidentSeverity.CRITICAL,
                                service=service_name,
                                namespace=ns,
                                pod=pod_name,
                                detection_source="Prometheus (Kube State Metrics)",
                                organization_id=self.settings.DEFAULT_ORGANIZATION_ID,
                                environment_id=self.settings.DEFAULT_ENVIRONMENT_ID,
                                fingerprint=fingerprint,
                                metrics=f"Phase: Failed · Pod: {pod_name} · Namespace: {ns}",
                                logs=f"KSM alert: kube_pod_status_phase{{phase='Failed'}}=1",
                            )
                        )
        except Exception as exc:
            logger.debug("[Detection] Failed pod query error: %s", str(exc))

        return anomalies

    async def run_detection_cycle(self) -> None:
        """Run a single detection and remediation cycle."""
        detected = await self.scan_anomalies()
        for anomaly in detected:
            existing = self.incidents.get_by_fingerprint(anomaly.fingerprint)
            if existing:
                # Deduplication: already active incident exists
                logger.debug("[Detection] Deduplicated anomaly for %s (active: %s)", anomaly.fingerprint, existing.id)
                continue

            # Create new incident
            created_incident = self.incidents.create_incident(anomaly)
            logger.info("[Detection] NEW INCIDENT %s: %s", created_incident.id, created_incident.title)

            # Trigger auto-healing pipeline if enabled
            if self.settings.HEALING_ENABLED:
                asyncio.create_task(self.orchestrator.run_healing_pipeline(created_incident))

    async def _loop(self) -> None:
        """Continuous polling loop."""
        logger.info("[Detection] Background detection loop started (interval: %ss)", self.settings.DETECTION_INTERVAL_SECONDS)
        while self._running:
            try:
                await self.run_detection_cycle()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[Detection] Unhandled exception in detection cycle: %s", str(exc))

            try:
                await asyncio.sleep(self.settings.DETECTION_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break

        logger.info("[Detection] Background detection loop stopped.")

    def start(self) -> None:
        """Start the background detection loop."""
        if self._running:
            return
        self._running = True
        self._loop_task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        """Stop the background detection loop."""
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()


_detection_service_instance: Optional[DetectionService] = None


def get_detection_service() -> DetectionService:
    """Dependency provider for DetectionService."""
    global _detection_service_instance
    if _detection_service_instance is None:
        _detection_service_instance = DetectionService()
    return _detection_service_instance
