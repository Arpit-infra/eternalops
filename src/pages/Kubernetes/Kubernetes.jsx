import { useState, useEffect, useCallback } from "react";
import { AlertCircle, RefreshCw, CheckCircle2 } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { Panel } from "../../components/common/Panel";
import { DataTable } from "../../components/tables/DataTable";
import { kubernetesService } from "../../services/kubernetesService";

function getPodHealthCategory(pod) {
  const phase = (pod.phase || "").toLowerCase();
  const restartCount = pod.restart_count || 0;

  // If failed or unknown phase, or containers in CrashLoopBackOff/Error
  if (phase === "failed" || phase === "unknown") {
    return "critical";
  }

  // Check container states
  if (pod.containers && pod.containers.length > 0) {
    for (const c of pod.containers) {
      if (!c.ready && phase === "running") {
        return "warning";
      }
      const state = (c.state || "").toLowerCase();
      if (state.includes("crashloopbackoff") || state.includes("error") || state.includes("terminated")) {
        return "critical";
      }
      if (state.includes("imagepullbackoff") || state.includes("errimagepull") || state.includes("containercreating") || state.includes("pending")) {
        return "warning";
      }
    }
  }

  if (restartCount > 5) {
    return "critical";
  }
  if (restartCount > 0 || phase === "pending") {
    return "warning";
  }
  if (phase === "running" || phase === "succeeded") {
    return "healthy";
  }

  return "healthy";
}

export function KubernetesPage() {
  const [ns, setNs] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [clusterStatus, setClusterStatus] = useState({ available: false, cluster_version: null, context: null });
  const [clusterInfo, setClusterInfo] = useState({ available: false, git_version: null, platform: null });
  const [namespacesList, setNamespacesList] = useState([]);
  const [nodesList, setNodesList] = useState([]);
  const [podsList, setPodsList] = useState([]);
  const [deploymentsList, setDeploymentsList] = useState([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [statusRes, clusterRes, nsRes, nodesRes, podsRes, depsRes] = await Promise.all([
        kubernetesService.getStatus(),
        kubernetesService.getClusterInfo(),
        kubernetesService.getNamespaces(),
        kubernetesService.getNodes(),
        kubernetesService.getPods(),
        kubernetesService.getDeployments(),
      ]);

      setClusterStatus(statusRes || { available: false, cluster_version: null, context: null });
      setClusterInfo(clusterRes || { available: false, git_version: null, platform: null });
      setNamespacesList(nsRes?.namespaces || []);
      setNodesList(nodesRes?.nodes || []);
      setPodsList(podsRes?.pods || []);
      setDeploymentsList(depsRes?.deployments || []);
      setError(null);
    } catch (err) {
      setError(err.message || "Failed to fetch Kubernetes data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Derived filtered data
  const filteredDeployments = ns === "all"
    ? deploymentsList
    : deploymentsList.filter((d) => d.namespace === ns);

  const filteredPods = ns === "all"
    ? podsList
    : podsList.filter((p) => p.namespace === ns);

  // Derived cluster metrics
  const k8sVersion = clusterInfo.git_version || clusterStatus.cluster_version || (clusterStatus.available ? "v1.36.1" : "Unavailable");
  const isClusterHealthy = clusterStatus.available;
  const activeContext = clusterStatus.context || "default";

  // Node counts
  const totalNodes = nodesList.length;
  const readyNodes = nodesList.filter((n) => n.status === "Ready").length;

  // Subtitle info
  const totalNamespacesCount = namespacesList.length;
  const totalPodsCount = podsList.length;

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>Kubernetes</h2>
            {isClusterHealthy ? (
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ background: C.successSoft, color: C.success }}>
                <CheckCircle2 size={12} /> Connected ({activeContext})
              </span>
            ) : (
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium" style={{ background: C.criticalSoft, color: C.critical }}>
                <AlertCircle size={12} /> Cluster Unavailable
              </span>
            )}
          </div>
          <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>
            {activeContext} · {totalNamespacesCount} namespaces · {totalPodsCount} pods
          </p>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors"
          style={{ background: C.surface2, border: `1px solid ${C.border}`, color: C.textSecondary }}
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl flex items-center gap-2 text-xs" style={{ background: C.criticalSoft, color: C.critical, border: `1px solid ${C.critical}` }}>
          <AlertCircle size={14} />
          <span>Error connecting to Kubernetes API: {error}</span>
        </div>
      )}

      {/* Namespace selector buttons */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setNs("all")}
          className="px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
          style={{
            background: ns === "all" ? C.accentSoft : C.surface2,
            color: ns === "all" ? C.accent : C.textSecondary,
            border: `1px solid ${ns === "all" ? C.accentBorder : C.border}`,
          }}
        >
          All namespaces
        </button>
        {namespacesList.map((n) => (
          <button
            key={n.name}
            onClick={() => setNs(n.name)}
            className="px-3 py-1.5 rounded-full text-xs font-medium cursor-pointer"
            style={{
              background: ns === n.name ? C.accentSoft : C.surface2,
              color: ns === n.name ? C.accent : C.textSecondary,
              border: `1px solid ${ns === n.name ? C.accentBorder : C.border}`,
            }}
          >
            {n.name}
          </button>
        ))}
      </div>

      {/* Top 3 Metric Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-2xl p-5" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="text-xs uppercase tracking-wide mb-2" style={{ color: C.textTertiary }}>Cluster status</div>
          <div className="flex items-center gap-2">
            <span style={{ width: 8, height: 8, borderRadius: 999, background: isClusterHealthy ? C.success : C.critical }} />
            <span className="text-[15px] font-semibold" style={{ color: C.textPrimary }}>
              {isClusterHealthy ? "Healthy" : "Unreachable"}
            </span>
          </div>
          <div className="text-xs mt-2" style={{ color: C.textTertiary }}>
            {totalNodes > 0 ? `${totalNodes} node${totalNodes > 1 ? "s" : ""}` : "No nodes"} · {k8sVersion}
          </div>
        </div>

        <div className="rounded-2xl p-5" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="text-xs uppercase tracking-wide mb-2" style={{ color: C.textTertiary }}>Node health</div>
          <div className="text-[15px] font-semibold" style={{ color: C.textPrimary, fontFamily: FONT_MONO }}>
            {loading && nodesList.length === 0 ? "—" : `${readyNodes}/${totalNodes} Ready`}
          </div>
          <div className="text-xs mt-2" style={{ color: C.textTertiary }}>
            Avg CPU — · Avg Mem —
          </div>
        </div>

        <div className="rounded-2xl p-5" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="text-xs uppercase tracking-wide mb-2" style={{ color: C.textTertiary }}>Storage</div>
          <div className="text-[15px] font-semibold" style={{ color: C.textPrimary, fontFamily: FONT_MONO }}>
            Metrics unavailable
          </div>
          <div className="text-xs mt-2" style={{ color: C.textTertiary }}>
            Volume metrics unavailable
          </div>
        </div>
      </div>

      {/* Pod Health Map */}
      <Panel
        title="Pod Health Map"
        subtitle={`${filteredPods.length} pod${filteredPods.length === 1 ? "" : "s"} · ${ns === "all" ? "all namespaces" : `${ns} namespace`}`}
      >
        {filteredPods.length === 0 ? (
          <div className="py-6 text-center text-xs" style={{ color: C.textTertiary }}>
            {loading ? "Loading pods..." : "No pods found in selected namespace"}
          </div>
        ) : (
          <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${Math.min(Math.max(filteredPods.length, 12), 24)}, minmax(0,1fr))` }}>
            {filteredPods.map((pod, i) => {
              const health = getPodHealthCategory(pod);
              const tooltip = `${pod.name} (${pod.namespace}) - ${pod.phase} - Restarts: ${pod.restart_count}`;
              return (
                <div
                  key={pod.name || i}
                  title={tooltip}
                  className="aspect-square rounded-[3px] transition-all"
                  style={{
                    background: health === "critical" ? C.critical : health === "warning" ? C.warning : C.accent,
                    opacity: health === "healthy" ? 0.55 : 1,
                  }}
                />
              );
            })}
          </div>
        )}

        <div className="flex items-center gap-4 mt-4">
          <div className="flex items-center gap-1.5 text-xs" style={{ color: C.textSecondary }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: C.accent, opacity: 0.55 }} />Healthy
          </div>
          <div className="flex items-center gap-1.5 text-xs" style={{ color: C.textSecondary }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: C.warning }} />Warning
          </div>
          <div className="flex items-center gap-1.5 text-xs" style={{ color: C.textSecondary }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: C.critical }} />Critical
          </div>
        </div>
      </Panel>

      {/* Deployments Table */}
      <Panel title="Deployments" pad={false}>
        {filteredDeployments.length === 0 ? (
          <div className="py-8 text-center text-xs" style={{ color: C.textTertiary }}>
            {loading ? "Loading deployments..." : "No deployments found in selected namespace"}
          </div>
        ) : (
          <DataTable
            columns={["Deployment", "Namespace", "Desired", "Ready", "Available", "Updated"]}
            rows={filteredDeployments}
            renderRow={(d, i) => (
              <tr key={`${d.namespace}-${d.name}-${i}`} style={{ borderBottom: i === filteredDeployments.length - 1 ? "none" : `1px solid ${C.borderSoft}` }}>
                <td className="px-3 py-3 text-[13px] font-medium" style={{ color: C.textPrimary }}>{d.name}</td>
                <td className="px-3 py-3 text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>{d.namespace}</td>
                <td className="px-3 py-3 text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>{d.desired_replicas}</td>
                <td className="px-3 py-3 text-[13px]" style={{ color: d.ready_replicas < d.desired_replicas ? C.warning : C.textSecondary, fontFamily: FONT_MONO }}>{d.ready_replicas}</td>
                <td className="px-3 py-3 text-[13px]" style={{ color: d.available_replicas < d.desired_replicas ? C.warning : C.textSecondary, fontFamily: FONT_MONO }}>{d.available_replicas}</td>
                <td className="px-3 py-3 text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>{d.updated_replicas}</td>
              </tr>
            )}
          />
        )}
      </Panel>
    </div>
  );
}

export default KubernetesPage;

