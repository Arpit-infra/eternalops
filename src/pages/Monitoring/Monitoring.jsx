import { useState, useEffect, useCallback } from "react";
import { AlertCircle, RefreshCw, CheckCircle2 } from "lucide-react";
import { C } from "../../constants/theme";
import { MetricPanel } from "../../components/cards/MetricPanel";
import { prometheusService } from "../../services/prometheusService";

export function MonitoringPage() {
  const [range, setRange] = useState("2h");
  const [loading, setLoading] = useState(true);
  const [prometheusStatus, setPrometheusStatus] = useState({ available: false, status: "checking" });
  const [metricsData, setMetricsData] = useState({
    cpu: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
    mem: { data: [], current: null, delta: null, deltaGood: false, hasData: false },
    latency: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
    disk: { data: [], current: null, delta: null, deltaGood: false, hasData: false },
    net: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
    req: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
    err: { data: [], current: null, delta: null, deltaGood: true, hasData: false },
  });

  const fetchData = useCallback(async (timeRange = range) => {
    setLoading(true);
    try {
      const res = await prometheusService.getDashboardMetrics(timeRange);
      setPrometheusStatus(res.status || { available: false, status: "unavailable" });
      setMetricsData(res.metrics);
    } catch {
      setPrometheusStatus({ available: false, status: "unavailable", error: "Failed to connect to Prometheus API" });
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    fetchData(range);
    const interval = setInterval(() => {
      fetchData(range);
    }, 15000);
    return () => clearInterval(interval);
  }, [range, fetchData]);

  const panels = [
    {
      title: "CPU Usage",
      unit: "%",
      data: metricsData.cpu.data,
      color: C.accent,
      current: metricsData.cpu.current,
      delta: metricsData.cpu.delta,
      deltaGood: metricsData.cpu.deltaGood ?? true,
      loading,
    },
    {
      title: "Memory Usage",
      unit: "%",
      data: metricsData.mem.data,
      color: C.violet,
      current: metricsData.mem.current,
      delta: metricsData.mem.delta,
      deltaGood: metricsData.mem.deltaGood ?? false,
      loading,
    },
    {
      title: "Latency (p95)",
      unit: "ms",
      data: metricsData.latency.data,
      color: C.info,
      current: metricsData.latency.current,
      delta: metricsData.latency.delta,
      deltaGood: metricsData.latency.deltaGood ?? true,
      loading,
    },
    {
      title: "Disk Usage",
      unit: "%",
      data: metricsData.disk.data,
      color: C.warning,
      current: metricsData.disk.current,
      delta: metricsData.disk.delta,
      deltaGood: metricsData.disk.deltaGood ?? false,
      loading,
    },
    {
      title: "Network I/O",
      unit: " Mb/s",
      data: metricsData.net.data,
      color: C.success,
      current: metricsData.net.current,
      delta: metricsData.net.delta,
      deltaGood: metricsData.net.deltaGood ?? true,
      loading,
    },
    {
      title: "HTTP Requests",
      unit: "/s",
      data: metricsData.req.data,
      color: C.success,
      current: metricsData.req.current,
      delta: metricsData.req.delta,
      deltaGood: metricsData.req.deltaGood ?? true,
      loading,
    },
    {
      title: "Error Rate",
      unit: "%",
      data: metricsData.err.data,
      color: C.critical,
      current: metricsData.err.current,
      delta: metricsData.err.delta,
      deltaGood: metricsData.err.deltaGood ?? true,
      loading,
    },
    {
      title: "Request Rate",
      unit: "/s",
      data: metricsData.req.data,
      color: C.info,
      current: metricsData.req.current,
      delta: metricsData.req.delta,
      deltaGood: metricsData.req.deltaGood ?? true,
      loading,
    },
  ];

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>Monitoring</h2>
            {prometheusStatus.available ? (
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ background: C.successSoft, color: C.success }}>
                <CheckCircle2 size={12} /> Prometheus Connected
              </span>
            ) : (
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ background: C.criticalSoft, color: C.critical }}>
                <AlertCircle size={12} /> Prometheus Unavailable
              </span>
            )}
          </div>
          <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>
            {prometheusStatus.available ? "Live metrics from Prometheus backend" : "Prometheus server at localhost:9090 is unreachable"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchData(range)}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors"
            style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textSecondary }}
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} /> Refresh
          </button>
          <div className="flex gap-1 p-1 rounded-lg" style={{ background: C.surface2, border: `1px solid ${C.border}` }}>
            {["1h", "2h", "6h", "24h"].map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className="px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer"
                style={{
                  background: range === r ? C.surface3 : "transparent",
                  color: range === r ? C.textPrimary : C.textTertiary,
                }}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {panels.map((p, idx) => (
          <MetricPanel key={`${p.title}-${idx}`} {...p} />
        ))}
      </div>
    </div>
  );
}

export default MonitoringPage;
