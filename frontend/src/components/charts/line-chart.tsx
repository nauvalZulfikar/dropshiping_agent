"use client";

import {
  LineChart as ReLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface LineChartProps {
  data: any[];
  xKey: string;
  lines: { key: string; color: string; dashed?: boolean }[];
  height?: number;
  referenceLine?: { y: number; label: string; color: string };
}

export function LineChart({ data, xKey, lines, height = 300, referenceLine }: LineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ReLineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
        <XAxis dataKey={xKey} stroke="#71717a" tick={{ fontSize: 12 }} />
        <YAxis stroke="#71717a" tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{ backgroundColor: "#18181b", border: "1px solid #27272a", borderRadius: 8 }}
          labelStyle={{ color: "#a1a1aa" }}
        />
        <Legend />
        {lines.map((l) => (
          <Line
            key={l.key}
            type="monotone"
            dataKey={l.key}
            stroke={l.color}
            strokeDasharray={l.dashed ? "5 5" : undefined}
            strokeWidth={2}
            dot={false}
          />
        ))}
        {referenceLine && (
          <ReferenceLine
            y={referenceLine.y}
            stroke={referenceLine.color}
            strokeDasharray="3 3"
            label={{ value: referenceLine.label, fill: referenceLine.color, fontSize: 12 }}
          />
        )}
      </ReLineChart>
    </ResponsiveContainer>
  );
}
