import { TrendingUp, TrendingDown, Loader2 } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";
import { MiniAreaChart } from "../charts/MiniAreaChart";

export function MetricPanel({ title, unit, data, color, current, delta, deltaGood = true, loading = false, error = null }) {
  const positive = delta && String(delta).startsWith("-") ? !deltaGood : deltaGood;
  const hasValidData = Array.isArray(data) && data.length > 0;
  const displayVal = current !== null && current !== undefined ? `${current}${unit || ""}` : "No data";

  return (
    <div className="rounded-2xl p-5 relative overflow-hidden" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium tracking-wide uppercase" style={{ color: C.textTertiary }}>{title}</span>
          {loading && <Loader2 size={12} className="animate-spin" style={{ color: C.textTertiary }} />}
        </div>
        {delta && !loading && (
          <span className="flex items-center gap-0.5 text-xs font-medium" style={{ fontFamily: FONT_MONO, color: positive ? C.success : C.critical }}>
            {positive ? <TrendingUp size={11} /> : <TrendingDown size={11} />}{delta}
          </span>
        )}
      </div>

      <div className="text-xl font-semibold mb-2" style={{ fontFamily: FONT_MONO, color: current !== null && current !== undefined ? C.textPrimary : C.textTertiary }}>
        {loading && current === undefined ? "—" : displayVal}
      </div>

      {loading && !hasValidData ? (
        <div className="h-[90px] flex items-center justify-center rounded-lg" style={{ background: C.surface2 }}>
          <div className="flex items-center gap-2 text-xs" style={{ color: C.textTertiary }}>
            <Loader2 size={14} className="animate-spin" /> Loading Prometheus metric...
          </div>
        </div>
      ) : hasValidData ? (
        <MiniAreaChart data={data} color={color} suffix={unit} />
      ) : (
        <div className="h-[90px] flex items-center justify-center rounded-lg border border-dashed text-xs" style={{ borderColor: C.border, color: C.textTertiary }}>
          {error ? "Query failed" : "No data in Prometheus"}
        </div>
      )}
    </div>
  );
}
