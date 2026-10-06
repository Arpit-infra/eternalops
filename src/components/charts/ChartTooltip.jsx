import { C, FONT_MONO } from "../../constants/theme";

export function ChartTooltip({ active, payload, label, suffix = "" }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div
      className="rounded-lg px-3 py-2 text-xs"
      style={{ background: C.surface3, border: `1px solid ${C.border}`, fontFamily: FONT_MONO }}
    >
      <div style={{ color: C.textTertiary, marginBottom: 2 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || C.textPrimary }}>
          {p.value}{suffix}
        </div>
      ))}
    </div>
  );
}
