import { C } from "../../constants/theme";

export function SeverityChip({ severity }) {
  const map = {
    critical: { color: C.critical, bg: C.criticalSoft, label: "Critical" },
    warning: { color: C.warning, bg: C.warningSoft, label: "Warning" },
    info: { color: C.info, bg: C.infoSoft, label: "Info" },
  };
  const m = map[severity] || { color: C.textSecondary, bg: "rgba(154,156,166,0.12)", label: severity };
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ background: m.bg, color: m.color }}
    >
      {m.label}
    </span>
  );
}
