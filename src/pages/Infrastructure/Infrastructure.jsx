import { useState, useEffect, useCallback } from "react";
import { Server, Activity, ShieldCheck, Cpu, HardDrive, RefreshCw, Layers } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { statusMeta } from "../../constants/status";
import { StatusChip } from "../../components/common/StatusChip";
import { environmentService } from "../../services/environmentService";
import { kubernetesService } from "../../services/kubernetesService";

export function InfrastructurePage() {
  const [environments, setEnvironments] = useState([]);
  const [workloads, setWorkloads] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [envs, wlResp, depsResp] = await Promise.all([
        environmentService.getEnvironments().catch(() => []),
        environmentService.getWorkloadHealth().catch(() => ({ workloads: [] })),
        kubernetesService.getDeployments().catch(() => ({ available: false, deployments: [] })),
      ]);

      setEnvironments(envs || []);

      if (wlResp && wlResp.workloads && wlResp.workloads.length > 0) {
        setWorkloads(
          wlResp.workloads.map((w) => ({
            name: w.name,
            version: `${w.ready_replicas || 0}/${w.desired_replicas || 0} replicas`,
            status: w.health_state === "HEALTHY" ? "Healthy" : (w.health_state === "RECOVERING" ? "Degraded" : "Critical"),
            lastSync: "Live K8s",
            health: w.desired_replicas > 0 ? Math.round(((w.ready_replicas || 0) / w.desired_replicas) * 100) : 100,
            icon: Layers,
          }))
        );
      } else if (depsResp.available && depsResp.deployments.length > 0) {
        setWorkloads(
          depsResp.deployments.map((d) => ({
            name: d.name,
            version: `${d.ready_replicas}/${d.desired_replicas} replicas`,
            status: d.ready_replicas >= d.desired_replicas ? "Healthy" : (d.ready_replicas > 0 ? "Degraded" : "Critical"),
            lastSync: "Live K8s",
            health: d.desired_replicas > 0 ? Math.round((d.ready_replicas / d.desired_replicas) * 100) : 100,
            icon: Layers,
          }))
        );
      } else {
        setWorkloads([]);
      }
    } catch (err) {
      console.warn("Failed to load infrastructure data:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 8000);
    return () => clearInterval(interval);
  }, [loadData]);

  return (
    <div className="p-6 flex flex-col gap-6">
      {/* Environments Section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>
              Control Plane Environments
            </h2>
            <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>
              Managed infrastructure environments and connected Kubernetes clusters
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {environments.map((env) => {
            const isConn = env.status === "CONNECTED";
            return (
              <div
                key={env.id}
                className="rounded-2xl p-5 flex flex-col gap-3 relative overflow-hidden"
                style={{ background: C.surface, border: `1px solid ${C.border}` }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center"
                      style={{ background: C.surface3 }}
                    >
                      <Server size={16} style={{ color: C.accent }} />
                    </div>
                    <div>
                      <div className="text-[14px] font-semibold" style={{ color: C.textPrimary }}>
                        {env.name}
                      </div>
                      <div className="text-xs" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>
                        {env.id}
                      </div>
                    </div>
                  </div>
                  <span
                    className="text-[11px] font-semibold px-2 py-0.5 rounded-full flex items-center gap-1.5"
                    style={{
                      background: isConn ? `${C.success}20` : `${C.critical}20`,
                      color: isConn ? C.success : C.critical,
                    }}
                  >
                    <span
                      style={{ width: 6, height: 6, borderRadius: 999, background: isConn ? C.success : C.critical }}
                    />
                    {env.status}
                  </span>
                </div>

                <div className="text-xs leading-relaxed" style={{ color: C.textSecondary }}>
                  {env.description || "Connected infrastructure environment"}
                </div>

                <div
                  className="grid grid-cols-2 gap-2 text-xs pt-3 mt-1"
                  style={{ borderTop: `1px solid ${C.borderSoft}` }}
                >
                  <div>
                    <span style={{ color: C.textTertiary }}>Provider:</span>{" "}
                    <span className="font-medium" style={{ color: C.textPrimary }}>
                      {env.provider}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: C.textTertiary }}>Platform:</span>{" "}
                    <span className="font-medium" style={{ color: C.textPrimary }}>
                      {env.platform}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: C.textTertiary }}>Connection:</span>{" "}
                    <span className="font-medium" style={{ color: C.textPrimary }}>
                      {env.connection_type}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: C.textTertiary }}>Self-Healing:</span>{" "}
                    <span className="font-medium" style={{ color: C.success }}>
                      Autonomous
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Connected Services Grid */}
      <div>
        <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>Connected Services & Workloads</h2>
        <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>Active workloads discovered in connected Kubernetes cluster</p>
      </div>
      {workloads.length === 0 ? (
        <div
          className="rounded-2xl p-8 text-center border border-dashed"
          style={{ borderColor: C.border, color: C.textTertiary }}
        >
          {loading ? "Discovering Kubernetes workloads..." : "No active deployments found in cluster."}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {workloads.map((s) => {
            const meta = statusMeta[s.status] || statusMeta.Healthy;
            const Icon = s.icon;
            return (
              <div key={s.name} className="rounded-2xl p-5 flex flex-col gap-4 transition-all duration-200 hover:-translate-y-0.5" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
                <div className="flex items-center justify-between">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: C.surface3 }}>
                    <Icon size={16} style={{ color: C.textSecondary }} />
                  </div>
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60" style={{ background: meta.color }} />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5" style={{ background: meta.color }} />
                  </span>
                </div>
                <div>
                  <div className="text-[14px] font-semibold" style={{ color: C.textPrimary }}>{s.name}</div>
                  <div className="text-xs mt-0.5" style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>{s.version}</div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <StatusChip status={s.status} />
                  <span style={{ color: C.textTertiary, fontFamily: FONT_MONO }}>{s.lastSync}</span>
                </div>
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[11px]" style={{ color: C.textTertiary }}>Health</span>
                    <span className="text-[11px] font-medium" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>{s.health}%</span>
                  </div>
                  <div className="h-1.5 rounded-full overflow-hidden" style={{ background: C.surface3 }}>
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${s.health}%`, background: meta.color }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default InfrastructurePage;
