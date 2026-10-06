import React from "react";
import {
  Globe2,
  Network,
  MonitorSmartphone,
  Server,
  Database,
  Boxes,
  Activity,
  HeartPulse,
} from "lucide-react";
import { C } from "../../constants/theme";
import { Panel } from "../../components/common/Panel";

export function TopologyPage() {
  const nodes = [
    { label: "Internet", icon: Globe2 },
    { label: "Load Balancer", icon: Network },
    { label: "Frontend", icon: MonitorSmartphone },
    { label: "Backend", icon: Server },
    { label: "Database", icon: Database },
    { label: "Kubernetes Cluster", icon: Boxes },
    { label: "Monitoring Stack", icon: Activity },
    { label: "Healing Engine", icon: HeartPulse },
  ];
  return (
    <div className="p-6 flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold" style={{ color: C.textPrimary }}>Topology</h2>
        <p className="text-sm mt-0.5" style={{ color: C.textTertiary }}>Live architecture map · prod-use1</p>
      </div>
      <Panel>
        <div className="flex flex-col items-center py-4">
          {nodes.map((n, i) => {
            const Icon = n.icon;
            const isHealing = n.label === "Healing Engine";
            return (
              <React.Fragment key={n.label}>
                <div
                  className="flex items-center gap-3 rounded-xl px-5 py-3.5 w-72 justify-center relative"
                  style={{ background: isHealing ? C.accentSoft : C.surface2, border: `1px solid ${isHealing ? C.accentBorder : C.border}` }}
                >
                  <Icon size={17} style={{ color: isHealing ? C.accent : C.textSecondary }} />
                  <span className="text-[13px] font-medium" style={{ color: isHealing ? C.accent : C.textPrimary }}>{n.label}</span>
                  <span className="absolute right-4 w-1.5 h-1.5 rounded-full" style={{ background: C.success }} />
                </div>
                {i < nodes.length - 1 && (
                  <div className="topology-line" style={{ height: 32, width: 2 }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}

export default TopologyPage;
