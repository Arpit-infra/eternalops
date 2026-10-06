import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  BrainCircuit,
  Workflow,
  HeartPulse,
  ShieldCheck,
  CheckCircle2,
  AlertOctagon,
  Zap,
  RefreshCw,
  Play,
  ShieldAlert,
} from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { SeverityChip } from "../../components/common/SeverityChip";
import { healingService } from "../../services/healingService";
import { incidentService } from "../../services/incidentService";

export function HealingEnginePage() {
  const [loading, setLoading] = useState(true);
  const [healingData, setHealingData] = useState({
    enabled: true,
    currently_healing: null,
    active_stage: null,
    recent_healed: [],
    total_healed_count: 0,
    total_escalated_count: 0,
  });
  const [triggering, setTriggering] = useState(false);

  const fetchHealingStatus = useCallback(async () => {
    try {
      const data = await healingService.getStatus();
      setHealingData(data);
    } catch (err) {
      console.warn("Failed to fetch healing engine status:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealingStatus();
    const interval = setInterval(fetchHealingStatus, 3000);
    return () => clearInterval(interval);
  }, [fetchHealingStatus]);

  const handleTestTrigger = async (simulateEscalation = false) => {
    setTriggering(true);
    try {
      await incidentService.triggerTestIncident({
        service: simulateEscalation ? "storage-controller" : "demo-auth-svc",
        namespace: simulateEscalation ? "kube-system" : "default",
        simulate_escalation: simulateEscalation,
      });
      await fetchHealingStatus();
    } catch (err) {
      console.error("Test incident trigger failed:", err);
    } finally {
      setTriggering(false);
    }
  };

  const current = healingData.currently_healing;
  const isEscalated = current?.status === "ESCALATED" || current?.healing_stage === "ESCALATED";

  const stageMap = {
    DETECTION: 0,
    ANALYSIS: 1,
    DECISION: 2,
    HEALING: 3,
    VERIFICATION: 4,
    RESOLVED: 5,
    ESCALATED: 5,
  };

  const activeStageIdx = current ? (stageMap[current.healing_stage] ?? 0) : -1;

  const steps = [
    { label: "Detection", icon: Activity, desc: "Anomaly flagged by Prometheus" },
    { label: "AI Analysis", icon: BrainCircuit, desc: "Root cause modeled" },
    { label: "Decision", icon: Workflow, desc: "Remediation plan selected" },
    { label: "Healing", icon: HeartPulse, desc: "Kubernetes action executed" },
    { label: "Verification", icon: ShieldCheck, desc: "Metrics confirmed stable" },
    {
      label: isEscalated ? "Escalated" : "Resolved",
      icon: isEscalated ? AlertOctagon : CheckCircle2,
      desc: isEscalated ? "Human intervention required" : "Workload healthy & closed",
    },
  ];

  const history = healingData.recent_healed || [];

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>Healing Engine</h2>
          <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>
            Autonomous detection, decision and recovery pipeline
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => handleTestTrigger(false)}
            disabled={triggering}
            className="flex items-center gap-1.5 px-3 h-8 rounded-lg text-xs font-medium cursor-pointer transition-colors"
            style={{ background: C.accentSoft, border: `1px solid ${C.accent}`, color: C.accent }}
            title="Trigger a healable pod restart demo incident"
          >
            <Play size={12} /> Simulate Healable Incident
          </button>
          <button
            onClick={() => handleTestTrigger(true)}
            disabled={triggering}
            className="flex items-center gap-1.5 px-3 h-8 rounded-lg text-xs font-medium cursor-pointer transition-colors"
            style={{ background: C.criticalSoft, border: `1px solid ${C.critical}`, color: C.critical }}
            title="Trigger an unhealable incident to test escalation flow"
          >
            <ShieldAlert size={12} /> Simulate Escalation
          </button>
          <button
            onClick={fetchHealingStatus}
            className="flex items-center gap-1.5 px-3 h-8 rounded-lg text-xs font-medium cursor-pointer"
            style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textSecondary }}
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Active Pipeline Card */}
      <div
        className="rounded-2xl p-8"
        style={{
          background: `radial-gradient(circle at 20% 0%, ${isEscalated ? C.criticalSoft : C.accentSoft}, transparent 60%), ${C.surface}`,
          border: `1px solid ${isEscalated ? C.critical : C.border}`,
        }}
      >
        <div className="flex items-center justify-between mb-2">
          <span
            className="text-xs font-medium uppercase tracking-wide"
            style={{ color: isEscalated ? C.critical : current ? C.accent : C.success }}
          >
            {current
              ? isEscalated
                ? `Remediation Escalated · ${current.id}`
                : `Currently healing · ${current.id}`
              : "Healing Pipeline · Standby"}
          </span>
          <span className="text-xs" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>
            {current?.detected_at
              ? `Detected ${new Date(current.detected_at).toLocaleTimeString()}`
              : "Continuous Prometheus polling active (15s)"}
          </span>
        </div>

        <h3 className="text-[16px] font-semibold mb-2" style={{ color: C.textPrimary }}>
          {current
            ? current.title
            : "No active anomalies — cluster is operating within normal baseline"}
        </h3>

        {current && (
          <p className="text-xs mb-6 leading-relaxed" style={{ color: C.textSecondary }}>
            {isEscalated
              ? `⚠️ ${current.escalation_reason || current.error || "Automatic remediation blocked by safety policy. Human intervention required."}`
              : current.root_cause
              ? `Root cause: ${current.root_cause}`
              : "Evaluating telemetry and determining safe remediation strategy..."}
          </p>
        )}

        {!current && (
          <p className="text-xs mb-6" style={{ color: C.textTertiary }}>
            Prometheus is monitoring restart counters, deployment replicas, and container failure phases.
          </p>
        )}

        {/* Workflow Stages Visualization */}
        <div className="flex items-center">
          {steps.map((s, i) => {
            const isDone = current ? i < activeStageIdx : false;
            const isActive = current ? i === activeStageIdx : false;
            const isStepEscalated = isEscalated && i === steps.length - 1;
            const Icon = s.icon;
            const stepAccent = isStepEscalated ? C.critical : C.accent;

            return (
              <React.Fragment key={s.label}>
                <div className="flex flex-col items-center gap-2" style={{ minWidth: 90 }}>
                  <div
                    className="w-11 h-11 rounded-full flex items-center justify-center relative"
                    style={{
                      background: isDone
                        ? C.accentSoft
                        : isActive
                        ? isStepEscalated
                          ? C.criticalSoft
                          : C.accentSoft
                        : C.surface3,
                      border: `1.5px solid ${
                        isDone || isActive ? stepAccent : C.border
                      }`,
                    }}
                  >
                    {isActive && (
                      <span
                        className="absolute inset-0 rounded-full animate-ping"
                        style={{ background: stepAccent, opacity: 0.25 }}
                      />
                    )}
                    <Icon
                      size={17}
                      style={{
                        color: isDone || isActive ? stepAccent : C.textTertiary,
                      }}
                    />
                  </div>
                  <div
                    className="text-[12px] font-medium text-center"
                    style={{
                      color: isDone || isActive ? C.textPrimary : C.textTertiary,
                    }}
                  >
                    {s.label}
                  </div>
                  <div
                    className="text-[10px] text-center"
                    style={{ color: C.textTertiary, maxWidth: 100 }}
                  >
                    {s.desc}
                  </div>
                </div>
                {i < steps.length - 1 && (
                  <div
                    className="flex-1 h-[2px] mb-8 rounded-full"
                    style={{
                      background: current && i < activeStageIdx ? C.accent : C.border,
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Recent History Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[14px] font-semibold" style={{ color: C.textPrimary }}>
            Recent healed incidents
          </h3>
          <span className="text-xs" style={{ color: C.textTertiary }}>
            {history.length} incident(s) recorded
          </span>
        </div>

        {history.length === 0 ? (
          <div
            className="rounded-2xl p-8 text-center border border-dashed"
            style={{ borderColor: C.border, color: C.textTertiary }}
          >
            No completed healing operations yet. Click "Simulate Healable Incident" above to test the pipeline.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {history.map((inc) => (
              <div
                key={inc.id}
                className="rounded-2xl p-5 flex flex-col gap-3"
                style={{
                  background: C.surface,
                  border: `1px solid ${inc.status === "ESCALATED" ? C.criticalBorder : C.border}`,
                }}
              >
                <div className="flex items-center justify-between">
                  <span
                    className="text-xs font-medium"
                    style={{ color: C.textTertiary, fontFamily: FONT_MONO }}
                  >
                    {inc.id}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {inc.status === "ESCALATED" && (
                      <span
                        className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                        style={{ background: C.criticalSoft, color: C.critical }}
                      >
                        Escalated
                      </span>
                    )}
                    <SeverityChip severity={inc.severity} />
                  </div>
                </div>
                <div className="text-[13px] font-medium" style={{ color: C.textPrimary }}>
                  {inc.title}
                </div>
                <div className="text-xs leading-relaxed" style={{ color: C.textSecondary }}>
                  {inc.status === "ESCALATED"
                    ? inc.escalation_reason || "Escalated for human review"
                    : inc.root_cause || "Root cause identified by AI Decision Engine"}
                </div>
                <div
                  className="grid grid-cols-2 gap-3 pt-2"
                  style={{ borderTop: `1px solid ${C.borderSoft}` }}
                >
                  <div>
                    <div className="text-[10px] uppercase" style={{ color: C.textTertiary }}>
                      Confidence
                    </div>
                    <div
                      className="text-[13px] font-semibold"
                      style={{ color: C.violet, fontFamily: FONT_MONO }}
                    >
                      {inc.confidence != null ? `${inc.confidence}%` : "—"}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase" style={{ color: C.textTertiary }}>
                      Recovery
                    </div>
                    <div
                      className="text-[13px] font-semibold"
                      style={{ color: C.textPrimary, fontFamily: FONT_MONO }}
                    >
                      {inc.recovery_duration || "—"}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs" style={{ color: C.textTertiary }}>
                  <Zap size={12} style={{ color: inc.status === "ESCALATED" ? C.critical : C.accent }} />{" "}
                  {inc.selected_action || (inc.status === "ESCALATED" ? "Escalated to human operator" : "Autonomous Remediation")}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default HealingEnginePage;
