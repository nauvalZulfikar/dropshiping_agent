"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface KpiCardProps {
  title: string;
  value: string | number;
  delta?: string;
  deltaType?: "positive" | "negative" | "neutral";
  alert?: boolean;
}

export function KpiCard({ title, value, delta, deltaType = "neutral", alert }: KpiCardProps) {
  const deltaColor =
    deltaType === "positive"
      ? "text-green-400"
      : deltaType === "negative"
        ? "text-red-400"
        : "text-zinc-400";

  return (
    <Card className={alert ? "border-red-500/50 bg-red-950/20" : ""}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-zinc-400">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {delta && <p className={`text-xs mt-1 ${deltaColor}`}>{delta}</p>}
      </CardContent>
    </Card>
  );
}
