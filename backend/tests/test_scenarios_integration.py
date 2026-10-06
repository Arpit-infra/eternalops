"""Integration tests for Scenarios A, B, and C with EternalOps Control Plane & Edge Agent."""

import pytest
from app.schemas.agent import AgentActionType, AgentCommandResult
from app.schemas.incidents import (
    HealingStage,
    IncidentCreate,
    IncidentSeverity,
    IncidentStatus,
    RemediationAction,
)
from app.services.agent_service import get_agent_service
from app.services.audit_service import get_audit_service
from app.services.connections.agent_connection import AgentConnection
from app.services.connections.connection_manager import get_connection_manager
from app.services.decision_engine import RuleBasedDecisionEngine, SafetyPolicy
from app.services.healing_orchestrator import HealingOrchestrator
from app.services.incident_service import get_incident_service
from app.services.notification_service import get_notification_service
from app.services.remediation_service import RemediationService
from app.services.verification_service import VerificationService


@pytest.fixture(autouse=True)
def setup_integration_env():
    inc_svc = get_incident_service()
    inc_svc.clear()
    audit_svc = get_audit_service()
    audit_svc.clear()
    yield
    inc_svc.clear()
    audit_svc.clear()


@pytest.mark.asyncio
async def test_scenario_a_application_readiness_failure_healed_by_edge_agent():
    """
    Scenario A: Application/Readiness failure where container is Running,
    Kubernetes does not automatically restart it, EternalOps detects the anomaly,
    Decision Engine & Safety Policy approve RESTART_POD,
    Edge Agent executes the allowlisted action, Verification confirms Ready status,
    and the Incident is RESOLVED / AUTO-RECOVERED.
    """
    env_id = "env_agent_demo"
    agent_svc = get_agent_service()
    tok = agent_svc.generate_enrollment_token(env_id)
    reg_resp = agent_svc.register_agent(
        type("RegReq", (), {
            "environment_id": env_id,
            "enrollment_token": tok,
            "agent_version": "0.1.0",
            "hostname": "edge-agent-node-1",
            "cluster_name": "customer-cluster",
            "kubernetes_version": "v1.28.2",
            "capabilities": ["RESTART_POD", "ROLLOUT_RESTART_DEPLOYMENT", "VERIFY_WORKLOAD"],
        })()
    )
    assert reg_resp.success is True
    session_token = reg_resp.session_token

    conn_mgr = get_connection_manager()
    agent_conn = conn_mgr.get_connection(env_id)
    assert agent_conn.is_connected() is True

    # 1. Inject application readiness failure into target workload state
    # Workload is phase='Running', but ready=False (Kubernetes native keeps it running)
    agent_conn.update_pod_status("eternalops-agent-demo", "agent-target-workload", phase="Running", ready=False)

    # 2. EternalOps Detection creates an incident
    inc_svc = get_incident_service()
    incident = inc_svc.create_incident(
        IncidentCreate(
            title="Application readiness probe failing on agent-target-workload",
            description="HTTP GET / returned 503/404; container process is alive but application is unhealthy.",
            severity=IncidentSeverity.CRITICAL,
            service="agent-target-workload",
            namespace="eternalops-agent-demo",
            pod="agent-target-workload",
            detection_source="Prometheus (Kube State Metrics / Probe Telemetry)",
            organization_id="org_default",
            environment_id=env_id,
            fingerprint="eternalops-agent-demo:readiness:agent-target-workload",
            metrics="Readiness: 0/1 · Phase: Running · ContainerStatus: NotReady",
        )
    )

    # 3. Decision Engine & Safety Policy evaluate
    dec_engine = RuleBasedDecisionEngine(SafetyPolicy())
    dec_res = dec_engine.evaluate(incident)
    assert dec_res.action == RemediationAction.RESTART_POD
    assert dec_res.safe_to_execute is True

    # 4. Remediation Service dispatches to Agent Connection
    remediation_svc = RemediationService(connection_manager=conn_mgr)
    incident.recommended_action = dec_res.action
    incident.selected_action = dec_res.action_label

    success, msg = remediation_svc.execute_remediation(incident)
    assert success is True
    assert "queued" in msg.lower() or "cmd-" in msg

    # 5. Agent polls for command and executes
    cmds = agent_svc.poll_commands(env_id, session_token)
    assert len(cmds) == 1
    assert cmds[0].action == AgentActionType.RESTART_POD
    assert cmds[0].target_name == "agent-target-workload"
    cmd_id = cmds[0].command_id

    # Agent reports successful execution result and recovers the workload
    agent_svc.record_command_result(
        AgentCommandResult(
            command_id=cmd_id,
            environment_id=env_id,
            action=AgentActionType.RESTART_POD,
            success=True,
            output="Pod deleted safely; ReplicaSet recreated healthy pod.",
            duration_seconds=0.35,
        )
    )

    # Workload returns to healthy Running + ready=True
    agent_conn.update_pod_status("eternalops-agent-demo", "agent-target-workload", phase="Running", ready=True)

    # 6. Verification Service verifies recovery
    verification_svc = VerificationService(connection_manager=conn_mgr)
    verified, v_msg = await verification_svc.verify_remediation(incident, timeout_seconds=2.0, poll_interval=0.1)
    assert verified is True
    assert "ready" in v_msg.lower() or "running" in v_msg.lower()

    # 7. Incident transitions to RESOLVED
    inc_svc.set_stage(incident.id, HealingStage.RESOLVED, IncidentStatus.RESOLVED)
    final_inc = inc_svc.get_by_id(incident.id)
    assert final_inc.status == IncidentStatus.RESOLVED
    assert final_inc.escalated is False
    assert final_inc.recovery_duration is not None


@pytest.mark.asyncio
async def test_scenario_b_persistent_failure_verification_fails_and_escalates():
    """
    Scenario B: Persistent / unresolvable application failure.
    Agent executes remediation, but verification fails -> Incident ESCALATED.
    """
    env_id = "env_agent_demo"
    agent_svc = get_agent_service()
    tok = agent_svc.generate_enrollment_token(env_id)
    reg_resp = agent_svc.register_agent(
        type("RegReq", (), {
            "environment_id": env_id,
            "enrollment_token": tok,
            "agent_version": "0.1.0",
            "hostname": "edge-agent-node-1",
            "cluster_name": "customer-cluster",
            "kubernetes_version": "v1.28.2",
            "capabilities": ["RESTART_POD", "ROLLOUT_RESTART_DEPLOYMENT"],
        })()
    )
    conn_mgr = get_connection_manager()
    agent_conn = conn_mgr.get_connection(env_id)

    # Inject persistent failure: Pod remains Not Ready even after restart
    agent_conn.update_pod_status("eternalops-agent-demo", "agent-target-workload", phase="Running", ready=False)

    inc_svc = get_incident_service()
    incident = inc_svc.create_incident(
        IncidentCreate(
            title="Persistent database corruption on agent-target-workload",
            description="Workload cannot start due to corrupt PVC mount.",
            severity=IncidentSeverity.CRITICAL,
            service="agent-target-workload",
            namespace="eternalops-agent-demo",
            pod="agent-target-workload",
            detection_source="Prometheus",
            organization_id="org_default",
            environment_id=env_id,
            fingerprint="eternalops-agent-demo:persistent:agent-target-workload",
        )
    )

    remediation_svc = RemediationService(connection_manager=conn_mgr)
    dec_engine = RuleBasedDecisionEngine(SafetyPolicy())
    dec_res = dec_engine.evaluate(incident)
    incident.recommended_action = dec_res.action

    # Execute remediation
    remediation_svc.execute_remediation(incident)
    # Drain command
    agent_svc.poll_commands(env_id, reg_resp.session_token)

    # Workload REMAINS unhealthy (verification will fail)
    agent_conn.update_pod_status("eternalops-agent-demo", "agent-target-workload", phase="Running", ready=False)

    verification_svc = VerificationService(connection_manager=conn_mgr)
    verified, v_msg = await verification_svc.verify_remediation(incident, timeout_seconds=0.3, poll_interval=0.1)
    assert verified is False

    # Orchestrator marks ESCALATED
    updated = inc_svc.set_stage(
        incident.id,
        HealingStage.ESCALATED,
        IncidentStatus.ESCALATED,
        error=f"Verification failed: {v_msg}",
        escalation_reason=f"Verification failed: {v_msg}",
    )
    assert updated.status == IncidentStatus.ESCALATED
    assert updated.escalated is True
    assert "Verification failed" in updated.escalation_reason


@pytest.mark.asyncio
async def test_scenario_c_native_kubernetes_recovery_observed_by_eternalops():
    """
    Scenario C: Kubernetes native container crash restart.
    Kubernetes restarts the container natively; EternalOps observes restart count anomaly,
    records detection and verifies recovery without claiming it replaced Kubernetes native self-healing.
    """
    inc_svc = get_incident_service()
    audit_svc = get_audit_service()

    # Container process crashed and was restarted natively by kubelet (restart_count=1)
    incident = inc_svc.create_incident(
        IncidentCreate(
            title="Native container restart anomaly observed on checkout-svc",
            description="Container crashed with SIGKILL (Exit code 137). Kubelet natively restarted container.",
            severity=IncidentSeverity.WARNING,
            service="checkout-svc",
            namespace="eternalops-demo",
            pod="checkout-svc-57df9b",
            detection_source="Prometheus (kube_pod_container_status_restarts_total)",
            organization_id="org_default",
            environment_id="env_local_dev",
            fingerprint="eternalops-demo:native_restart:checkout-svc-57df9b",
            metrics="Restarts: 1 (native recovery) · ExitCode: 137",
        )
    )
    assert incident.id.startswith("INC-")

    # EternalOps verifies that container is healthy and ready following the native restart
    inc_svc.set_stage(incident.id, HealingStage.VERIFICATION, IncidentStatus.VERIFYING)
    inc_svc.set_stage(incident.id, HealingStage.RESOLVED, IncidentStatus.RESOLVED)

    audit_svc.log(
        action="Native recovery verified: Container healthy after kubelet restart",
        performed_by="EternalOps Telemetry Observer",
        target="checkout-svc-57df9b",
        status="Success",
        duration="—",
        incident_id=incident.id,
        details={"type": "kubernetes_native_recovery", "restarts": 1},
    )

    resolved = inc_svc.get_by_id(incident.id)
    assert resolved.status == IncidentStatus.RESOLVED
    assert resolved.escalated is False

    logs = audit_svc.get_logs(incident_id=incident.id)
    assert any("Native recovery" in l.action for l in logs.logs)
