/**
 * Prometheus Service for live metrics from FastAPI Prometheus proxy backend.
 */
import { apiClient } from "./api";

/**
 * Helper to compute range parameters in unix epoch seconds and resolution step.
 */
function getRangeParams(rangeStr) {
  const now = Math.floor(Date.now() / 1000);
  let duration = 7200; // default 2h in seconds
  let step = "30s";

  switch (rangeStr) {
    case "1h":
      duration = 3600;
      step = "15s";
      break;
    case "2h":
      duration = 7200;
      step = "30s";
      break;
    case "6h":
      duration = 21600;
      step = "2m";
      break;
    case "24h":
      duration = 86400;
      step = "10m";
      break;
    default:
      duration = 7200;
      step = "30s";
  }

  return {
    start: String(now - duration),
    end: String(now),
    step,
  };
}

/**
 * Format unix timestamp (seconds) into HH:MM or HH:MM:SS
 */
function formatTime(unixSec) {
  const d = new Date(unixSec * 1000);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

/**
 * Standard PromQL queries for dashboard panels.
 * Provides resilient fallbacks for common Prometheus installations
 * (node_exporter, kube-prometheus-stack, cAdvisor, demo exporters, or internal Prometheus metrics).
 */
const METRIC_QUERIES = {
  cpu: [
    "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)",
    "100 - (avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)",
    "sum(rate(container_cpu_usage_seconds_total{container!='',container!='POD'}[5m])) * 100",
    "rate(process_cpu_seconds_total[5m]) * 100",
  ],
  mem: [
    "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
    "((node_memory_MemTotal_bytes - node_memory_MemFree_bytes) / node_memory_MemTotal_bytes) * 100",
    "(sum(container_memory_working_set_bytes{container!='',container!='POD'}) / sum(machine_memory_bytes)) * 100",
    "(process_resident_memory_bytes / 1024 / 1024 / 1024)",
  ],
  latency: [
    "(sum(rate(http_request_duration_seconds_sum[5m])) / sum(rate(http_request_duration_seconds_count[5m]))) * 1000",
    "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) * 1000",
    "histogram_quantile(0.95, sum(rate(prometheus_http_request_duration_seconds_bucket[5m])) by (le)) * 1000",
  ],
  disk: [
    "(1 - (node_filesystem_free_bytes{mountpoint='/'} / node_filesystem_size_bytes{mountpoint='/'})) * 100",
    "(1 - (sum(node_filesystem_free_bytes) / sum(node_filesystem_size_bytes))) * 100",
  ],
  net: [
    "(sum(rate(node_network_receive_bytes_total[5m])) + sum(rate(node_network_transmit_bytes_total[5m]))) * 8 / 1000000",
    "(sum(rate(container_network_receive_bytes_total[5m])) + sum(rate(container_network_transmit_bytes_total[5m]))) * 8 / 1000000",
  ],
  req: [
    "sum(rate(http_requests_total[5m]))",
    "sum(rate(nginx_ingress_controller_requests[5m]))",
    "sum(rate(prometheus_http_requests_total[5m]))",
  ],
  err: [
    "(sum(rate(http_requests_total{status=~'5..'}[5m])) / sum(rate(http_requests_total[5m]))) * 100",
    "(sum(rate(nginx_ingress_controller_requests{status=~'5..'}[5m])) / sum(rate(nginx_ingress_controller_requests[5m]))) * 100",
    "(sum(rate(prometheus_http_requests_total{code=~'5..'}[5m])) / sum(rate(prometheus_http_requests_total[5m]))) * 100",
  ],
  up: [
    "up",
  ],
  availability: [
    "(sum(up == 1) / count(up)) * 100",
  ],
};

export const prometheusService = {
  /**
   * Check Prometheus connection status.
   */
  getStatus: async () => {
    try {
      return await apiClient.get("/api/prometheus/status");
    } catch (err) {
      return {
        available: false,
        status: "unavailable",
        error: err.message || "Failed to contact Prometheus proxy",
      };
    }
  },

  /**
   * Execute instant query.
   */
  queryInstant: async (query) => {
    return await apiClient.get("/api/prometheus/query", { query });
  },

  /**
   * Execute range query.
   */
  queryRange: async (query, start, end, step) => {
    return await apiClient.get("/api/prometheus/query-range", { query, start, end, step });
  },

  /**
   * Fetch Kubernetes pod status phase counts from KSM.
   * Query: sum by (phase) (kube_pod_status_phase == 1)
   */
  getKubernetesPodPhases: async (namespace = null) => {
    try {
      const nsFilter = namespace && namespace !== "all" ? `{namespace="${namespace}"}` : "";
      const query = `sum by (phase) (kube_pod_status_phase${nsFilter} == 1)`;
      const resp = await apiClient.get("/api/prometheus/query", { query });

      const phases = {
        Running: 0,
        Pending: 0,
        Failed: 0,
        Succeeded: 0,
        total: 0,
        hasData: false,
      };

      if (resp?.data?.result && Array.isArray(resp.data.result)) {
        resp.data.result.forEach((item) => {
          const phase = item.metric?.phase;
          const val = item.value && item.value[1] !== undefined ? Number(item.value[1]) : 0;
          if (!isNaN(val) && phase) {
            phases[phase] = (phases[phase] || 0) + val;
            phases.total += val;
            phases.hasData = true;
          }
        });
      }

      return phases;
    } catch (err) {
      return {
        Running: 0,
        Pending: 0,
        Failed: 0,
        Succeeded: 0,
        total: 0,
        hasData: false,
        error: err.message || "Failed to query pod phases",
      };
    }
  },

  /**
   * Fetch container restart counts aggregated by (namespace, pod) from KSM.
   * Query: sum by (namespace, pod) (kube_pod_container_status_restarts_total)
   */
  getKubernetesPodRestarts: async (namespace = null) => {
    try {
      const nsFilter = namespace && namespace !== "all" ? `{namespace="${namespace}"}` : "";
      const query = `sum by (namespace, pod) (kube_pod_container_status_restarts_total${nsFilter})`;
      const resp = await apiClient.get("/api/prometheus/query", { query });

      const restartMap = {};
      let totalRestarts = 0;
      let hasData = false;

      if (resp?.data?.result && Array.isArray(resp.data.result)) {
        resp.data.result.forEach((item) => {
          const podName = item.metric?.pod;
          const podNs = item.metric?.namespace;
          const val = item.value && item.value[1] !== undefined ? Number(item.value[1]) : 0;
          if (!isNaN(val) && podName) {
            hasData = true;
            totalRestarts += val;
            restartMap[podName] = val;
            if (podNs) {
              restartMap[`${podNs}/${podName}`] = val;
            }
          }
        });
      }

      return {
        restartMap,
        totalRestarts,
        hasData,
      };
    } catch (err) {
      return {
        restartMap: {},
        totalRestarts: 0,
        hasData: false,
        error: err.message || "Failed to query pod restarts",
      };
    }
  },

  /**
   * Fetch Kubernetes deployment metrics from KSM.
   */
  getKubernetesDeploymentsMetrics: async (namespace = null) => {
    try {
      const nsFilter = namespace && namespace !== "all" ? `{namespace="${namespace}"}` : "";
      const [specRes, availRes, readyRes, updatedRes] = await Promise.all([
        apiClient.get("/api/prometheus/query", { query: `kube_deployment_spec_replicas${nsFilter}` }),
        apiClient.get("/api/prometheus/query", { query: `kube_deployment_status_replicas_available${nsFilter}` }),
        apiClient.get("/api/prometheus/query", { query: `kube_deployment_status_replicas_ready${nsFilter}` }),
        apiClient.get("/api/prometheus/query", { query: `kube_deployment_status_replicas_updated${nsFilter}` }),
      ]);

      const depMetrics = {};

      const parseSeries = (resp, field) => {
        if (resp?.data?.result && Array.isArray(resp.data.result)) {
          resp.data.result.forEach((item) => {
            const depName = item.metric?.deployment;
            const depNs = item.metric?.namespace;
            const val = item.value && item.value[1] !== undefined ? Number(item.value[1]) : 0;
            if (depName && depNs && !isNaN(val)) {
              const key = `${depNs}/${depName}`;
              if (!depMetrics[key]) {
                depMetrics[key] = { namespace: depNs, name: depName };
              }
              depMetrics[key][field] = val;
            }
          });
        }
      };

      parseSeries(specRes, "specReplicas");
      parseSeries(availRes, "availableReplicas");
      parseSeries(readyRes, "readyReplicas");
      parseSeries(updatedRes, "updatedReplicas");

      return {
        metrics: depMetrics,
        hasData: Object.keys(depMetrics).length > 0,
      };
    } catch (err) {
      return {
        metrics: {},
        hasData: false,
        error: err.message || "Failed to query deployment metrics",
      };
    }
  },

  /**
   * Try candidate queries until one returns data or all fail.
   */
  queryRangeWithCandidates: async (candidateQueries, rangeStr = "2h") => {
    const { start, end, step } = getRangeParams(rangeStr);

    for (const query of candidateQueries) {
      try {
        const resp = await apiClient.get("/api/prometheus/query-range", { query, start, end, step });
        if (resp && resp.data && resp.data.result && resp.data.result.length > 0) {
          const firstSeries = resp.data.result[0];
          if (firstSeries.values && firstSeries.values.length > 0) {
            const series = firstSeries.values.map(([ts, val]) => ({
              t: formatTime(ts),
              value: Math.round(parseFloat(val) * 100) / 100,
            })).filter(pt => !isNaN(pt.value));

            if (series.length > 0) {
              const latestVal = series[series.length - 1].value;
              const prevVal = series.length > 1 ? series[0].value : latestVal;
              let deltaStr = "0%";
              let deltaGood = true;

              if (prevVal !== 0 && prevVal !== undefined) {
                const diff = latestVal - prevVal;
                const pct = ((diff / Math.abs(prevVal)) * 100).toFixed(1);
                deltaStr = `${diff >= 0 ? "+" : ""}${pct}%`;
                deltaGood = diff <= 0;
              }

              return {
                data: series,
                current: latestVal,
                delta: deltaStr,
                deltaGood,
                query,
                hasData: true,
              };
            }
          }
        }
      } catch {
        // Try next candidate
      }
    }

    return {
      data: [],
      current: null,
      delta: null,
      deltaGood: true,
      hasData: false,
    };
  },

  /**
   * Fetch target health stats from `up`.
   */
  getTargetHealth: async () => {
    try {
      const resp = await apiClient.get("/api/prometheus/query", { query: "up" });
      if (resp && resp.data && resp.data.result && resp.data.result.length > 0) {
        const total = resp.data.result.length;
        const healthy = resp.data.result.filter(r => String(r.value[1]) === "1").length;
        const availability = total > 0 ? ((healthy / total) * 100).toFixed(2) : "100.00";
        return {
          total,
          healthy,
          availability,
          ratio: `${healthy}/${total}`,
          hasData: true,
        };
      }
    } catch {
      // no data or error
    }
    return {
      total: null,
      healthy: null,
      availability: null,
      ratio: null,
      hasData: false,
    };
  },

  /**
   * Fetch all 8 dashboard metric panels for a given time range.
   */
  getDashboardMetrics: async (rangeStr = "2h") => {
    const [
      statusResult,
      targetResult,
      cpuRes,
      memRes,
      latencyRes,
      diskRes,
      netRes,
      reqRes,
      errRes,
    ] = await Promise.all([
      prometheusService.getStatus(),
      prometheusService.getTargetHealth(),
      prometheusService.queryRangeWithCandidates(METRIC_QUERIES.cpu, rangeStr),
      prometheusService.queryRangeWithCandidates(METRIC_QUERIES.mem, rangeStr),
      prometheusService.queryRangeWithCandidates(METRIC_QUERIES.latency, rangeStr),
      prometheusService.queryRangeWithCandidates(METRIC_QUERIES.disk, rangeStr),
      prometheusService.queryRangeWithCandidates(METRIC_QUERIES.net, rangeStr),
      prometheusService.queryRangeWithCandidates(METRIC_QUERIES.req, rangeStr),
      prometheusService.queryRangeWithCandidates(METRIC_QUERIES.err, rangeStr),
    ]);

    return {
      status: statusResult,
      targets: targetResult,
      metrics: {
        cpu: cpuRes,
        mem: memRes,
        latency: latencyRes,
        disk: diskRes,
        net: netRes,
        req: reqRes,
        err: errRes,
      },
    };
  },
};
