"use client";

import { useDashboard } from "@/lib/api";
import { maskPhone } from "@/lib/utils";
import { KpiCard } from "@/components/layout/kpi-card";
import { BarChart } from "@/components/charts/bar-chart";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

interface CsStats {
  total_messages: number;
  unique_customers: number;
  escalated: number;
  resolution_rate: number;
}

interface Escalation {
  created_at: string;
  customer_phone: string;
  platform: string;
  preview: string;
}

interface IntentRow {
  intent: string;
  count: number;
}

export default function CsAnalyticsPage() {
  const { data: stats } = useDashboard<CsStats>("/cs/stats");
  const { data: escalations } = useDashboard<Escalation[]>("/cs/escalations?limit=20");
  const { data: intents } = useDashboard<IntentRow[]>("/cs/intents?days=7");

  if (!stats) return <div className="animate-pulse text-zinc-500">Loading...</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">CS Bot Analytics</h1>

      <div className="grid grid-cols-4 gap-4">
        <KpiCard title="Pesan Hari Ini" value={stats.total_messages} />
        <KpiCard title="Customer Unik" value={stats.unique_customers} />
        <KpiCard
          title="Resolution Rate"
          value={`${stats.resolution_rate}%`}
          deltaType={stats.resolution_rate >= 85 ? "positive" : "negative"}
          delta={stats.resolution_rate >= 85 ? "Di atas target 85%" : "Di bawah target 85%"}
        />
        <KpiCard title="Eskalasi" value={stats.escalated} alert={stats.escalated > 0} />
      </div>

      {intents && intents.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Distribusi Intent (7 hari)</h2>
          <BarChart
            data={intents}
            xKey="intent"
            bars={[{ key: "count", color: "#8b5cf6" }]}
            height={250}
          />
        </div>
      )}

      {escalations && escalations.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Eskalasi Terbaru</h2>
          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800">
                  <TableHead>Waktu</TableHead>
                  <TableHead>Customer</TableHead>
                  <TableHead>Platform</TableHead>
                  <TableHead>Pesan</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {escalations.map((e, i) => (
                  <TableRow key={i} className="border-zinc-800">
                    <TableCell className="text-xs text-zinc-400">
                      {new Date(e.created_at).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{maskPhone(e.customer_phone)}</TableCell>
                    <TableCell>{e.platform}</TableCell>
                    <TableCell className="max-w-64 truncate text-sm">{e.preview}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}
