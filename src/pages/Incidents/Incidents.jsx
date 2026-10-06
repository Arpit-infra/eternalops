import { useState, useEffect, useCallback } from "react";
import {
  Search,
  Filter,
  ChevronRight,
  X,
  HeartPulse,
  CheckCircle2,
  AlertOctagon,
  RefreshCw,
  Play,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { SeverityChip } from "../../components/common/SeverityChip";
import { StatusChip } from "../../components/common/StatusChip";
import { IconButton } from "../../components/common/IconButton";
import { incidentService } from "../../services/incidentService";

export function IncidentsPage() {
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("Metrics");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [incidentsResponse, setIncidentsResponse] = useState({
    total: 0,
    active_count: 0,
    resolved_count: 0,
    escalated_count: 0,
    incidents: [],
  });

  const fetchIncidents = useCallback(async () => {
    try {
      const data = await incidentService.getIncidents({
        severity: filter !== "all" ? filter : undefined,
        search: search.trim() || undefined,
      });
      setIncidentsResponse(data);
      // Update selected drawer if open
      if (selected) {
        const updated = data.incidents.find((i) => i.id === selected.id);
        if (updated) setSelected(updated);
      }
    } catch (err) {
      console.warn("Error fetching incidents:", err);
    } finally {
      setLoading(false);
    }
  }, [filter, search, selected]);

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 4000);
    return () => clearInterval(interval);
  }, [fetchIncidents]);

  const handleTestTrigger = async (simulateEscalation = false) => {
    setActionLoading(true);
    try {
      await incidentService.triggerTestIncident({
        service: simulateEscalation ? "storage-controller" : "demo-auth-svc",
        namespace: simulateEscalation ? "kube-system" : "default",
        simulate_escalation: simulateEscalation,
      });
      await fetchIncidents();
    } catch (err) {
      console.error("Test incident trigger failed:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleManualHeal = async (incidentId) => {
    setActionLoading(true);
    try {
      await incidentService.healIncident(incidentId);
      await fetchIncidents();
    } catch (err) {
      console.error("Manual heal failed:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleManualResolve = async (incidentId) => {
    setActionLoading(true);
    try {
      await incidentService.resolveIncident(incidentId);
      await fetchIncidents();
    } catch (err) {
      console.error("Resolve failed:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const incidents = incidentsResponse.incidents || [];

  return (
    <div className="p-6 flex flex-col gap-6 relative">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>Incidents</h2>
          <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>
            {incidentsResponse.total} incident(s) · {incidentsResponse.active_count} active · {incidentsResponse.resolved_count} resolved · {incidentsResponse.escalated_count} escalated
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="flex items-center gap-2 px-3 h-9 rounded-lg"
            style={{ background: C.surface2, border: `1px solid ${C.border}`, width: 260 }}
          >
            <Search size={13} style={{ color: C.textTertiary }} />
            <input
              type="text"
              placeholder="Search incidents…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent border-none outline-none text-[13px] w-full"
              style={{ color: C.textPrimary }}
            />
          </div>
          <button
            onClick={() => handleTestTrigger(false)}
            disabled={actionLoading}
            className="flex items-center gap-1.5 px-3 h-9 rounded-lg text-xs font-medium cursor-pointer transition-colors"
            style={{ background: C.accentSoft, border: `1px solid ${C.accent}`, color: C.accent }}
            title="Create test healable incident"
          >
            <Play size={12} /> Test Heal
          </button>
          <button
            onClick={() => handleTestTrigger(true)}
            disabled={actionLoading}
            className="flex items-center gap-1.5 px-3 h-9 rounded-lg text-xs font-medium cursor-pointer transition-colors"
            style={{ background: C.criticalSoft, border: `1px solid ${C.critical}`, color: C.critical }}
            title="Create test unhealable incident"
          >
            <ShieldAlert size={12} /> Test Escalate
          </button>
          <button
            onClick={fetchIncidents}
            className="flex items-center gap-1.5 px-3 h-9 rounded-lg text-xs font-medium cursor-pointer"
            style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textSecondary }}
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      <div className="flex gap-2">
        {["all", "critical", "warning", "info"].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium capitalize cursor-pointer"
            style={{
              background: filter === f ? C.accentSoft : C.surface2,
              color: filter === f ? C.accent : C.textSecondary,
              border: `1px solid ${filter === f ? C.accentBorder : C.border}`,
            }}
          >
            <Filter size={11} />
            {f}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-3">
        {incidents.length === 0 ? (
          <div
            className="rounded-2xl p-12 text-center border border-dashed"
            style={{ borderColor: C.border, color: C.textTertiary }}
          >
            {loading ? (
              <div className="flex items-center justify-center gap-2">
                <Loader2 size={16} className="animate-spin" /> Loading live incidents...
              </div>
            ) : (
              "No incidents detected. System is running cleanly. Click 'Test Heal' or 'Test Escalate' above to test the autonomous pipeline."
            )}
          </div>
        ) : (
          incidents.map((inc) => (
            <button
              key={inc.id}
              onClick={() => {
                setSelected(inc);
                setTab("Metrics");
              }}
              className="text-left rounded-2xl p-5 flex items-center gap-5 transition-all duration-150 hover:-translate-y-0.5 cursor-pointer"
              style={{ background: C.surface, border: `1px solid ${C.border}` }}
            >
              <div
                className="w-1 self-stretch rounded-full shrink-0"
                style={{
                  background:
                    inc.severity === "critical"
                      ? C.critical
                      : inc.severity === "warning"
                      ? C.warning
                      : C.info,
                }}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span
                    className="text-xs font-medium"
                    style={{ color: C.textTertiary, fontFamily: FONT_MONO }}
                  >
                    {inc.id}
                  </span>
                  <SeverityChip severity={inc.severity} />
                  <StatusChip status={inc.status} />
                  {inc.escalated && (
                    <span
                      className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                      style={{ background: C.criticalSoft, color: C.critical }}
                    >
                      Escalated
                    </span>
                  )}
                </div>
                <div className="text-[14px] font-medium" style={{ color: C.textPrimary }}>
                  {inc.title}
                </div>
                <div className="text-xs mt-1" style={{ color: C.textTertiary }}>
                  Service:{" "}
                  <span style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>
                    {inc.service}
                  </span>{" "}
                  · Namespace:{" "}
                  <span style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>
                    {inc.namespace}
                  </span>{" "}
                  · Detected{" "}
                  {inc.detected_at
                    ? new Date(inc.detected_at).toLocaleTimeString()
                    : "—"}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-xs" style={{ color: C.textTertiary }}>
                  Recovery
                </div>
                <div
                  className="text-[14px] font-semibold"
                  style={{ color: C.textPrimary, fontFamily: FONT_MONO }}
                >
                  {inc.recovery_duration || "—"}
                </div>
              </div>
              <ChevronRight size={16} style={{ color: C.textTertiary }} />
            </button>
          ))
        )}
      </div>

      {/* Drawer */}
      {selected && (
        <>
          <div
            onClick={() => setSelected(null)}
            className="fixed inset-0 z-40"
            style={{ background: "rgba(0,0,0,0.5)" }}
          />
          <div
            className="fixed right-0 top-0 h-full w-[460px] z-50 flex flex-col"
            style={{ background: C.bgElevated, borderLeft: `1px solid ${C.border}` }}
          >
            <div
              className="flex items-center justify-between px-6 h-16 shrink-0"
              style={{ borderBottom: `1px solid ${C.border}` }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="text-xs font-medium"
                  style={{ color: C.textTertiary, fontFamily: FONT_MONO }}
                >
                  {selected.id}
                </span>
                <SeverityChip severity={selected.severity} />
                <StatusChip status={selected.status} />
              </div>
              <IconButton icon={X} onClick={() => setSelected(null)} />
            </div>
            <div className="px-6 py-5 overflow-y-auto flex-1">
              <h3 className="text-[16px] font-semibold mb-1" style={{ color: C.textPrimary }}>
                {selected.title}
              </h3>
              <div
                className="flex items-center gap-3 text-xs mb-5 flex-wrap"
                style={{ color: C.textTertiary }}
              >
                <span>
                  Detected{" "}
                  {selected.detected_at
                    ? new Date(selected.detected_at).toLocaleTimeString()
                    : "—"}
                </span>
                <span>·</span>
                <span>Recovery: {selected.recovery_duration || "—"}</span>
                <span>·</span>
                <span>Source: {selected.detection_source}</span>
              </div>

              {/* Action Buttons */}
              {selected.status !== "RESOLVED" && (
                <div className="flex gap-2 mb-4">
                  <button
                    onClick={() => handleManualHeal(selected.id)}
                    disabled={actionLoading}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold cursor-pointer"
                    style={{ background: C.accentSoft, border: `1px solid ${C.accent}`, color: C.accent }}
                  >
                    <HeartPulse size={13} /> Run Auto-Heal
                  </button>
                  <button
                    onClick={() => handleManualResolve(selected.id)}
                    disabled={actionLoading}
                    className="px-3 py-2 rounded-lg text-xs font-medium cursor-pointer"
                    style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textSecondary }}
                  >
                    <CheckCircle2 size={13} /> Resolve
                  </button>
                </div>
              )}

              <div className="flex gap-1 p-1 rounded-lg mb-4" style={{ background: C.surface2 }}>
                {["Metrics", "Logs", "Root Cause", "Recovery", "Timeline"].map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className="flex-1 px-2 py-1.5 rounded-md text-[11px] font-medium cursor-pointer"
                    style={{
                      background: tab === t ? C.surface3 : "transparent",
                      color: tab === t ? C.textPrimary : C.textTertiary,
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>

              {tab === "Metrics" && (
                <div
                  className="rounded-xl p-4 text-[13px] leading-relaxed"
                  style={{
                    background: C.surface,
                    border: `1px solid ${C.border}`,
                    color: C.textSecondary,
                    fontFamily: FONT_MONO,
                  }}
                >
                  {selected.metrics || "No metric telemetry snapshot attached."}
                </div>
              )}
              {tab === "Logs" && (
                <pre
                  className="rounded-xl p-4 text-[12px] leading-relaxed whitespace-pre-wrap"
                  style={{
                    background: "#000",
                    border: `1px solid ${C.border}`,
                    color: C.success,
                    fontFamily: FONT_MONO,
                  }}
                >
                  {selected.logs || "No error logs captured."}
                </pre>
              )}
              {tab === "Root Cause" && (
                <div className="flex flex-col gap-3">
                  <div
                    className="rounded-xl p-4"
                    style={{ background: C.surface, border: `1px solid ${C.border}` }}
                  >
                    <div className="text-[13px] leading-relaxed" style={{ color: C.textSecondary }}>
                      {selected.root_cause || "AI Root Cause analysis in progress..."}
                    </div>
                  </div>
                  {selected.confidence != null && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs" style={{ color: C.textTertiary }}>
                        AI confidence
                      </span>
                      <div
                        className="h-1.5 flex-1 rounded-full overflow-hidden"
                        style={{ background: C.surface3 }}
                      >
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${selected.confidence}%`,
                            background: C.violet,
                          }}
                        />
                      </div>
                      <span
                        className="text-xs font-medium"
                        style={{ color: C.violet, fontFamily: FONT_MONO }}
                      >
                        {selected.confidence}%
                      </span>
                    </div>
                  )}
                </div>
              )}
              {tab === "Recovery" && (
                <div
                  className="rounded-xl p-4 flex flex-col gap-2"
                  style={{ background: C.surface, border: `1px solid ${C.border}` }}
                >
                  <div className="flex items-center gap-2">
                    <HeartPulse size={16} style={{ color: selected.escalated ? C.critical : C.accent }} />
                    <span className="text-[13px] font-medium" style={{ color: C.textPrimary }}>
                      {selected.selected_action || selected.recommended_action || "Pending Decision"}
                    </span>
                  </div>
                  {selected.escalated && (
                    <p className="text-xs mt-1" style={{ color: C.critical }}>
                      ⚠️ {selected.escalation_reason || "Automatic remediation unavailable — human intervention required."}
                    </p>
                  )}
                  {selected.verification_status && (
                    <p className="text-xs mt-1" style={{ color: C.textTertiary }}>
                      Verification: {selected.verification_status}
                    </p>
                  )}
                </div>
              )}
              {tab === "Timeline" && (
                <div className="flex flex-col gap-4">
                  {[
                    { name: "Anomaly Detected", done: true },
                    {
                      name: "AI Root Cause Analysis",
                      done: selected.healing_stage !== "DETECTION",
                    },
                    {
                      name: "Remediation Decision",
                      done: ["DECISION", "HEALING", "VERIFICATION", "RESOLVED", "ESCALATED"].includes(
                        selected.healing_stage
                      ),
                    },
                    {
                      name: "Kubernetes Action Executed",
                      done: ["HEALING", "VERIFICATION", "RESOLVED", "ESCALATED"].includes(
                        selected.healing_stage
                      ),
                    },
                    {
                      name: "Metrics Verification",
                      done: ["VERIFICATION", "RESOLVED", "ESCALATED"].includes(
                        selected.healing_stage
                      ),
                    },
                    {
                      name: selected.escalated ? "Incident Escalated" : "Incident Resolved",
                      done: selected.status === "RESOLVED" || selected.status === "ESCALATED",
                      isEscalate: selected.escalated,
                    },
                  ].map((step, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <div
                        className="w-6 h-6 rounded-full flex items-center justify-center shrink-0"
                        style={{
                          background: step.done
                            ? step.isEscalate
                              ? C.criticalSoft
                              : C.accentSoft
                            : C.surface3,
                        }}
                      >
                        {step.isEscalate ? (
                          <AlertOctagon size={13} style={{ color: C.critical }} />
                        ) : (
                          <CheckCircle2
                            size={13}
                            style={{ color: step.done ? C.accent : C.textTertiary }}
                          />
                        )}
                      </div>
                      <span
                        className="text-[13px]"
                        style={{ color: step.done ? C.textPrimary : C.textTertiary }}
                      >
                        {step.name}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default IncidentsPage;
