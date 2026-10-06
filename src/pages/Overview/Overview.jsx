import { useState, useEffect, useCallback } from "react";
import {
  ShieldCheck,
  CheckCheck,
  AlertTriangle,
  HeartPulse,
  Box,
  Server,
  Layers,
  GitBranch,
  RefreshCw,
  Loader2,
  CheckCircle2,
  ShieldAlert,
  CircleDot,
  BrainCircuit,
  Radio,
} from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";
import { C, FONT_MONO } from "../../constants/theme";
import { KpiCard } from "../../components/cards/KpiCard";
import { MetricPanel } from "../../components/cards/MetricPanel";
import { Panel } from "../../components/common/Panel";
import { ChartTooltip } from "../../components/charts/ChartTooltip";
import { prometheusService } from "../../services/prometheusService";
import { incidentService } from "../../services/incidentService";
import { auditService } from "../../services/auditService";
import { environmentService } from "../../services/environmentService";
import { kubernetesService } from "../../services/kubernetesService";
import { activityFeed as defaultActivityFeed, feedIcon } from "../../data/dashboardData";

export function OverviewPage() {
  const [loading, setLoading] = useState(true);
  const [activeIncidentsCount, setActiveIncidentsCount] = useState(0);
  const [avgRecoveryTime, setAvgRecoveryTime] = useState("No recovery data");
  const [runningPodsCount, setRunningPodsCount] = useState({ running: 0, total: 0, hasData: false });
  const [deploymentsCount, setDeploymentsCount] = useState({ count: 0, hasData: false });
  const [recoveredCount, setRecoveredCount] = useState(0);
  const [agentStatus, setAgentStatus] = useState({ connected: false, label: "Disconnected" });
  const [liveActivityFeed, setLiveActivityFeed] = useState([]);
  const [prometheusData, setPrometheusData] = useState({
    status: { available: false, status: "checking" },
    targets: { total: null, healthy: null, availability: null, ratio: null, hasData: false },
    metrics: {
      cpu: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
      mem: { data: [], current: null, delta: null, deltaGood: false, hasData: false },
      latency: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
      disk: { data: [], current: null, delta: null, deltaGood: false, hasData: false },
      net: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
      req: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
      err: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
    },
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [promData, incData, auditData, healthSummary, k8sPods, k8sDeps] = await Promise.all([
        prometheusService.getDashboardMetrics("2h"),
        incidentService.getIncidents().catch(() => ({ active_count: 0, resolved_count: 0 })),
        auditService.getAuditLogs({ limit: 10 }).catch(() => ({ logs: [] })),
        environmentService.getHealthSummary().catch(() => null),
        kubernetesService.getPods().catch(() => ({ available: false, total: 0, pods: [] })),
        kubernetesService.getDeployments().catch(() => ({ available: false, total: 0, deployments: [] })),
      ]);

      setPrometheusData(promData);
      setActiveIncidentsCount(incData.active_count ?? 0);
      setRecoveredCount(incData.resolved_count ?? (healthSummary?.auto_recovered_count ?? 0));

      if (healthSummary) {
        setAvgRecoveryTime(healthSummary.avg_recovery_time || "No recovery data");
        setAgentStatus({
          connected: Boolean(healthSummary.agent_connected),
          label: healthSummary.agent_connected ? "CONNECTED" : "DISCONNECTED",
        });
      }

      if (k8sPods.available) {
        const running = k8sPods.pods.filter((p) => p.phase === "Running").length;
        setRunningPodsCount({ running, total: k8sPods.total, hasData: true });
      } else {
        setRunningPodsCount({ running: 0, total: 0, hasData: false });
      }

      if (k8sDeps.available) {
        setDeploymentsCount({ count: k8sDeps.total, hasData: true });
      } else {
        setDeploymentsCount({ count: 0, hasData: false });
      }

      if (auditData.logs && auditData.logs.length > 0) {
        const mapped = auditData.logs.map((a) => {
          let type = "info";
          if (a.status === "Success") type = a.action.toLowerCase().includes("heal") || a.action.toLowerCase().includes("restart") ? "heal" : "success";
          else if (a.status === "Failed" || a.status === "Escalated") type = "critical";
          else if (a.action.toLowerCase().includes("ai") || a.action.toLowerCase().includes("analysis")) type = "ai";

          return {
            t: a.ts,
            type,
            text: a.action,
            meta: `${a.target} · ${a.status}`,
          };
        });
        setLiveActivityFeed(mapped);
      }
    } catch {
      // Keep existing state or mark unavailable
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const { status, targets, metrics } = prometheusData;

  // Build combined CPU & Memory series
  const combinedSeries = [];
  const cpuList = metrics.cpu.data || [];
  const memList = metrics.mem.data || [];
  const maxLen = Math.max(cpuList.length, memList.length);

  for (let i = 0; i < maxLen; i++) {
    const cPt = cpuList[i];
    const mPt = memList[i];
    combinedSeries.push({
      t: cPt ? cPt.t : (mPt ? mPt.t : ""),
      value: cPt ? cPt.value : 0,
      mem: mPt ? mPt.value : 0,
    });
  }

  const hasCombinedData = combinedSeries.length > 0;

  // Format request sparkline or fallback
  const reqSparkline = metrics.req.data;

  // Determine availability values
  const availabilityVal = targets.availability !== null ? targets.availability : (status.available ? "100.00" : "N/A");
  const healthyServicesVal = targets.ratio !== null ? targets.ratio : (status.available ? "0/0" : "N/A");

  const displayFeed = liveActivityFeed.length > 0 ? liveActivityFeed : [];

  return (
    <div className="flex gap-6 p-6">
      <div className="flex-1 min-w-0 flex flex-col gap-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>Mission Control</h2>
            <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>
              {status.available ? "Live metrics from connected Prometheus backend" : "Prometheus server at localhost:9090 is offline"}
            </p>
          </div>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 h-9 rounded-lg text-[13px] font-medium cursor-pointer transition-colors"
            style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textSecondary }}
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
        </div>

        {/* Hero KPIs */}
        <div className="grid grid-cols-4 gap-4">
          <KpiCard
            label="Availability"
            value={availabilityVal}
            unit="%"
            delta={status.available ? "+0.00%" : "+0.02%"}
            icon={ShieldCheck}
            sparkline={reqSparkline}
            loading={loading && targets.availability === null}
          />
          <KpiCard
            label="Healthy Services"
            value={healthyServicesVal}
            delta={status.available && targets.hasData ? "live" : "stable"}
            deltaGood
            icon={CheckCheck}
            accentColor={C.success}
            loading={loading && targets.ratio === null}
          />
          <KpiCard
            label="Active Incidents"
            value={String(activeIncidentsCount)}
            delta={activeIncidentsCount > 0 ? "active" : "0"}
            deltaGood={activeIncidentsCount === 0}
            icon={AlertTriangle}
            accentColor={activeIncidentsCount > 0 ? C.critical : C.warning}
          />
          <KpiCard
            label="Avg Recovery Time"
            value={avgRecoveryTime}
            delta={avgRecoveryTime !== "No recovery data" ? "verified" : "no data"}
            icon={HeartPulse}
            accentColor={C.accent}
          />
        </div>

        {/* Secondary strip */}
        <div className="grid grid-cols-5 gap-4">
          {[
            {
              label: "Running Pods",
              value: runningPodsCount.hasData ? `${runningPodsCount.running}/${runningPodsCount.total}` : "N/A",
              icon: Box,
            },
            {
              label: "Edge Agent",
              value: agentStatus.label,
              icon: Radio,
            },
            {
              label: "Deployments",
              value: deploymentsCount.hasData ? String(deploymentsCount.count) : "N/A",
              icon: Layers,
            },
            {
              label: "Cluster Connection",
              value: runningPodsCount.hasData ? "Connected" : "Disconnected",
              icon: Server,
            },
            {
              label: "Auto-Recovered",
              value: String(recoveredCount),
              icon: HeartPulse,
            },
          ].map((s) => (
            <div key={s.label} className="rounded-xl px-4 py-3 flex items-center gap-3" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: C.surface3 }}>
                <s.icon size={14} style={{ color: C.textSecondary }} />
              </div>
              <div className="min-w-0">
                <div className="text-[15px] font-semibold leading-tight" style={{ fontFamily: FONT_MONO, color: C.textPrimary }}>{s.value}</div>
                <div className="text-[11px] truncate" style={{ color: C.textTertiary }}>{s.label}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Big combined chart */}
        <Panel
          title="Compute Utilization"
          subtitle={
            status.available
              ? "CPU vs Memory · Live Prometheus Range (2h)"
              : "CPU vs Memory · Prometheus instance offline"
          }
        >
          {loading && !hasCombinedData ? (
            <div className="h-[220px] flex items-center justify-center rounded-lg" style={{ background: C.surface2 }}>
              <div className="flex items-center gap-2 text-sm" style={{ color: C.textTertiary }}>
                <Loader2 size={16} className="animate-spin" /> Loading Prometheus compute metrics...
              </div>
            </div>
          ) : hasCombinedData ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={combinedSeries}>
                <defs>
                  <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={C.accent} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={C.accent} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={C.violet} stopOpacity={0.3} />
                    <stop offset="100%" stopColor={C.violet} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={C.borderSoft} vertical={false} />
                <XAxis dataKey="t" tick={{ fill: C.textTertiary, fontSize: 11, fontFamily: FONT_MONO }} axisLine={{ stroke: C.border }} tickLine={false} />
                <YAxis tick={{ fill: C.textTertiary, fontSize: 11, fontFamily: FONT_MONO }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip suffix="%" />} cursor={{ stroke: C.border }} />
                <Area type="monotone" dataKey="value" name="CPU" stroke={C.accent} strokeWidth={2} fill="url(#cpuGrad)" />
                <Area type="monotone" dataKey="mem" name="Memory" stroke={C.violet} strokeWidth={2} fill="url(#memGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center rounded-lg border border-dashed text-sm" style={{ borderColor: C.border, color: C.textTertiary }}>
              No compute data available from Prometheus
            </div>
          )}
          <div className="flex items-center gap-4 mt-2">
            <div className="flex items-center gap-1.5 text-xs" style={{ color: C.textSecondary }}><span style={{ width: 8, height: 8, borderRadius: 2, background: C.accent }} />CPU</div>
            <div className="flex items-center gap-1.5 text-xs" style={{ color: C.textSecondary }}><span style={{ width: 8, height: 8, borderRadius: 2, background: C.violet }} />Memory</div>
          </div>
        </Panel>

        {/* Grid of small charts */}
        <div className="grid grid-cols-2 gap-4">
          <MetricPanel
            title="Latency (p95)"
            unit="ms"
            data={metrics.latency.data}
            color={C.info}
            current={metrics.latency.current}
            delta={metrics.latency.delta}
            loading={loading}
          />
          <MetricPanel
            title="Requests / sec"
            unit="/s"
            data={metrics.req.data}
            color={C.success}
            current={metrics.req.current}
            delta={metrics.req.delta}
            loading={loading}
          />
          <MetricPanel
            title="Disk Usage"
            unit="%"
            data={metrics.disk.data}
            color={C.warning}
            current={metrics.disk.current}
            delta={metrics.disk.delta}
            deltaGood={metrics.disk.deltaGood ?? false}
            loading={loading}
          />
          <MetricPanel
            title="Error Rate"
            unit="%"
            data={metrics.err.data}
            color={C.critical}
            current={metrics.err.current}
            delta={metrics.err.delta}
            loading={loading}
          />
        </div>
      </div>

      {/* Right activity panel */}
      <div className="w-[300px] shrink-0">
        <Panel title="Live Activity Feed" subtitle="Streaming" className="sticky top-6">
          <div className="flex flex-col">
            {displayFeed.map((item, i) => {
              const meta = feedIcon[item.type] || feedIcon.info;
              const Icon = meta.icon;
              return (
                <div key={i} className="flex gap-3 py-3" style={{ borderTop: i === 0 ? "none" : `1px solid ${C.borderSoft}` }}>
                  <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5" style={{ background: meta.color + "20" }}>
                    <Icon size={12} style={{ color: meta.color }} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-[13px] leading-snug" style={{ color: C.textPrimary }}>{item.text}</div>
                    <div className="text-[11px] mt-0.5" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>{item.t} · {item.meta}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>
    </div>
  );
}

export default OverviewPage;
