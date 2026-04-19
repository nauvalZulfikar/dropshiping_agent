"use client";

import {
  BarChart as ReBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface BarChartProps {
  data: any[];
  xKey: string;
  bars: { key: string; color: string }[];
  height?: number;
  layout?: "horizontal" | "vertical";
}

export function BarChart({ data, xKey, bars, height = 300, layout = "horizontal" }: BarChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReBarChart data={data} layout={layout === "vertical" ? "vertical" : "horizontal"}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        {layout === "vertical" ? (
          <>
            <XAxis type="number" stroke="#71717a" tick={{ fontSize: 12 }} />
            <YAxis dataKey={xKey} type="category" stroke="#71717a" tick={{ fontSize: 11 }} width={120} />
          </>
        ) : (
          <>
            <XAxis dataKey={xKey} stroke="#71717a" tick={{ fontSize: 12 }} />
            <YAxis stroke="#71717a" tick={{ fontSize: 12 }} />
          </>
        )}
        <Tooltip
          contentStyle={{ backgroundColor: "#18181b", border: "1px solid #27272a", borderRadius: 8 }}
        />
        <Legend />
        {bars.map((b) => (
          <Bar key={b.key} dataKey={b.key} fill={b.color} radius={[4, 4, 0, 0]} />
        ))}
      </ReBarChart>
    </ResponsiveContainer>
  );
}
