import { ResponsiveContainer, AreaChart, Area } from "recharts";
import { TrendingUp, TrendingDown, Loader2 } from "lucide-react";
import { C, FONT_MONO } from "../../constants/theme";

export function KpiCard({
  label,
  value,
  unit,
  delta,
  deltaGood = true,
  icon: Icon,
  sparkline,
  accentColor,
  loading = false,
}) {
  const positive = delta && String(delta).startsWith("-") ? !deltaGood : deltaGood;
  const hasSparkline = Array.isArray(sparkline) && sparkline.length > 0;

  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-3 group transition-all duration-200 hover:-translate-y-0.5"
      style={{ background: C.surface, border: `1px solid ${C.border}` }}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium tracking-wide uppercase" style={{ color: C.textTertiary }}>{label}</span>
        {loading ? (
          <Loader2 size={14} className="animate-spin" style={{ color: C.textTertiary }} />
        ) : (
          Icon && (
            <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: (accentColor || C.accent) + "20" }}>
              <Icon size={14} style={{ color: accentColor || C.accent }} />
            </div>
          )
        )}
      </div>
      <div className="flex items-end justify-between">
        <div className="flex items-baseline gap-1">
          <span className="text-[26px] font-semibold leading-none" style={{ fontFamily: FONT_MONO, color: value !== "No data" && value !== null ? C.textPrimary : C.textTertiary }}>
            {value ?? "—"}
          </span>
          {unit && value !== "No data" && value !== null && <span className="text-sm" style={{ color: C.textTertiary }}>{unit}</span>}
        </div>
        {delta && !loading && (
          <span className="flex items-center gap-0.5 text-xs font-medium" style={{ fontFamily: FONT_MONO, color: positive ? C.success : C.critical }}>
            {positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {delta}
          </span>
        )}
      </div>
      {hasSparkline && (
        <div style={{ height: 32, marginTop: 2 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkline}>
              <defs>
                <linearGradient id={`spark-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={accentColor || C.accent} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={accentColor || C.accent} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="value" stroke={accentColor || C.accent} strokeWidth={1.5} fill={`url(#spark-${label})`} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
