import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from "recharts";
import { C } from "../../constants/theme";
import { ChartTooltip } from "./ChartTooltip";

export function MiniAreaChart({ data, color, suffix = "", height = 90 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.4} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="t" hide />
        <YAxis hide domain={["dataMin - 5", "dataMax + 5"]} />
        <Tooltip content={<ChartTooltip suffix={suffix} />} cursor={{ stroke: C.border }} />
        <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2} fill={`url(#grad-${color})`} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
