import { useState } from "react";
import { Server, Mail, Bell, HeartPulse, KeyRound, MonitorSmartphone, Globe2 } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { Panel } from "../../components/common/Panel";
import { Toggle, SettingsRow } from "../../components/common/SettingsControls";

export function SettingsPage() {
  const [section, setSection] = useState("cluster");
  const [toggles, setToggles] = useState({ autoHeal: true, slack: true, email: false, pagerduty: true, canary: true });
  const flip = (k) => setToggles((t) => ({ ...t, [k]: !t[k] }));

  const sections = [
    { id: "cluster", label: "Cluster Configuration", icon: Server },
    { id: "smtp", label: "SMTP", icon: Mail },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "healing", label: "Healing Policies", icon: HeartPulse },
    { id: "keys", label: "API Keys", icon: KeyRound },
    { id: "theme", label: "Theme", icon: MonitorSmartphone },
    { id: "environment", label: "Environment", icon: Globe2 },
  ];

  return (
    <div className="p-6 flex gap-6">
      <div className="w-56 shrink-0 flex flex-col gap-1">
        {sections.map((s) => (
          <button
            key={s.id}
            onClick={() => setSection(s.id)}
            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium"
            style={{
              background: section === s.id ? C.surface2 : "transparent",
              color: section === s.id ? C.textPrimary : C.textSecondary,
            }}
          >
            <s.icon size={14} style={{ color: section === s.id ? C.accent : C.textTertiary }} /> {s.label}
          </button>
        ))}
      </div>

      <div className="flex-1 max-w-2xl">
        {section === "cluster" && (
          <Panel title="Cluster Configuration" subtitle="Connection details for prod-use1">
            <SettingsRow label="Cluster name" desc="Display name across the platform" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>prod-use1</span>} />
            <SettingsRow label="Kubernetes version" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>v1.29.4</span>} />
            <SettingsRow label="Region" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>us-east-1</span>} />
            <SettingsRow label="Node pools" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>3</span>} />
          </Panel>
        )}
        {section === "smtp" && (
          <Panel title="SMTP" subtitle="Outbound mail relay for alerts and reports">
            <SettingsRow label="Host" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>smtp.eternalops.io</span>} />
            <SettingsRow label="Port" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>587</span>} />
            <SettingsRow label="TLS" control={<Toggle on={true} onClick={() => {}} />} />
            <SettingsRow label="Send test email" control={<button className="px-3 py-1.5 rounded-lg text-xs font-medium" style={{ background: C.surface3, color: C.textSecondary }}>Send</button>} />
          </Panel>
        )}
        {section === "notifications" && (
          <Panel title="Notifications" subtitle="Where incidents and healing events get delivered">
            <SettingsRow label="Slack alerts" desc="#incidents channel" control={<Toggle on={toggles.slack} onClick={() => flip("slack")} />} />
            <SettingsRow label="Email digests" desc="Daily summary at 09:00" control={<Toggle on={toggles.email} onClick={() => flip("email")} />} />
            <SettingsRow label="PagerDuty escalation" desc="Critical severity only" control={<Toggle on={toggles.pagerduty} onClick={() => flip("pagerduty")} />} />
          </Panel>
        )}
        {section === "healing" && (
          <Panel title="Healing Policies" subtitle="Rules the healing engine follows before acting">
            <SettingsRow label="Automated healing" desc="Allow the engine to act without approval" control={<Toggle on={toggles.autoHeal} onClick={() => flip("autoHeal")} />} />
            <SettingsRow label="Canary verification" desc="Verify on a subset before full rollback" control={<Toggle on={toggles.canary} onClick={() => flip("canary")} />} />
            <SettingsRow label="Minimum confidence to auto-act" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>85%</span>} />
            <SettingsRow label="Max automatic rollbacks / hour" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>4</span>} />
          </Panel>
        )}
        {section === "keys" && (
          <Panel title="API Keys" subtitle="Scoped keys for integrations">
            {[{ name: "grafana-svc-key", scope: "read:metrics", created: "12 Jun 2026" }, { name: "jenkins-webhook", scope: "write:pipelines", created: "3 May 2026" }].map((k) => (
              <SettingsRow key={k.name} label={k.name} desc={`${k.scope} · created ${k.created}`} control={<span className="text-[12px] px-2 py-1 rounded" style={{ background: C.surface3, color: C.textTertiary, fontFamily: FONT_MONO }}>••••••••</span>} />
            ))}
          </Panel>
        )}
        {section === "theme" && (
          <Panel title="Theme" subtitle="Appearance across the platform">
            <SettingsRow label="Dark mode" desc="EternalOps is designed dark-first" control={<Toggle on={true} onClick={() => {}} />} />
            <SettingsRow label="Accent color" control={<span className="flex items-center gap-2 text-[13px]" style={{ color: C.textSecondary }}><span style={{ width: 14, height: 14, borderRadius: 4, background: C.accent }} />Signal Teal</span>} />
          </Panel>
        )}
        {section === "environment" && (
          <Panel title="Environment" subtitle="Active environment for this workspace">
            <SettingsRow label="Environment" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>Production</span>} />
            <SettingsRow label="Default namespace" control={<span className="text-[13px]" style={{ color: C.textSecondary, fontFamily: FONT_MONO }}>production</span>} />
          </Panel>
        )}
      </div>
    </div>
  );
}

export default SettingsPage;
