import { Loader2 } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { statusMeta } from "../../constants/status";

export function StatusChip({ status, dot = true }) {
  const meta = statusMeta[status] || { color: C.textSecondary, bg: "rgba(154,156,166,0.12)" };
  const spinning = status === "Running";
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ background: meta.bg, color: meta.color, fontFamily: FONT_MONO, letterSpacing: "0.01em" }}
    >
      {dot && (spinning
        ? <Loader2 size={11} className="animate-spin" />
        : <span style={{ width: 6, height: 6, borderRadius: 999, background: meta.color, display: "inline-block" }} />
      )}
      {status}
    </span>
  );
}
