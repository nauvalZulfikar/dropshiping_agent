"use client";

import { useDashboard } from "@/lib/api";
import { formatIDR, decisionColor, trendIcon } from "@/lib/utils";
import { KpiCard } from "@/components/layout/kpi-card";
import { LineChart } from "@/components/charts/line-chart";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { useMemo } from "react";

interface NicheRow {
  niche: string;
  epc: number;
  cvr: number;
  total_clicks: number;
  aov: number;
  trend: string;
  score: number;
  decision: string;
}

interface EpcRow {
  date: string;
  niche: string;
  epc: number;
}

export default function AffiliatePage() {
  const { data: leaderboard } = useDashboard<NicheRow[]>("/affiliate/leaderboard");
  const { data: epcTrend } = useDashboard<EpcRow[]>("/affiliate/epc-trend");

  const kpis = useMemo(() => {
    if (!leaderboard || leaderboard.length === 0) return null;
    const avgEpc = leaderboard.reduce((s, r) => s + Number(r.epc), 0) / leaderboard.length;
    const totalClicks = leaderboard.reduce((s, r) => s + r.total_clicks, 0);
    const flipCount = leaderboard.filter((r) => r.decision === "flip_to_dropship").length;
    return { avgEpc, totalClicks, nicheCount: leaderboard.length, flipCount };
  }, [leaderboard]);

  const pivotedEpc = useMemo(() => {
    if (!epcTrend || epcTrend.length === 0) return { data: [], niches: [] };
    const topNiches = [...new Set(epcTrend.map((r) => r.niche))]
      .map((n) => ({
        niche: n,
        avg: epcTrend.filter((r) => r.niche === n).reduce((s, r) => s + r.epc, 0) /
          epcTrend.filter((r) => r.niche === n).length,
      }))
      .sort((a, b) => b.avg - a.avg)
      .slice(0, 5)
      .map((x) => x.niche);

    const byDate: Record<string, Record<string, number>> = {};
    for (const r of epcTrend) {
      if (!topNiches.includes(r.niche)) continue;
      if (!byDate[r.date]) byDate[r.date] = {};
      byDate[r.date][r.niche] = r.epc;
    }
    const data = Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, vals]) => ({ date, ...vals }));
    return { data, niches: topNiches };
  }, [epcTrend]);

  const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#a855f7"];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Affiliate Intelligence</h1>

      {kpis && (
        <div className="grid grid-cols-4 gap-4">
          <KpiCard title="EPC Rata-rata" value={formatIDR(Math.round(kpis.avgEpc))} />
          <KpiCard title="Total Klik" value={kpis.totalClicks.toLocaleString("id-ID")} />
          <KpiCard title="Niche Aktif" value={kpis.nicheCount} />
          <KpiCard title="Siap Flip" value={kpis.flipCount} />
        </div>
      )}

      {leaderboard && leaderboard.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Niche Leaderboard</h2>
          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800">
                  <TableHead>Niche</TableHead>
                  <TableHead>EPC</TableHead>
                  <TableHead>CVR</TableHead>
                  <TableHead>AOV</TableHead>
                  <TableHead>Klik</TableHead>
                  <TableHead>Trend</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Keputusan</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leaderboard.map((r) => (
                  <TableRow key={r.niche} className={`border-zinc-800 ${decisionColor(r.decision)}`}>
                    <TableCell className="font-medium">{r.niche}</TableCell>
                    <TableCell>{formatIDR(Math.round(Number(r.epc)))}</TableCell>
                    <TableCell>{(Number(r.cvr) * 100).toFixed(2)}%</TableCell>
                    <TableCell>{formatIDR(Number(r.aov))}</TableCell>
                    <TableCell>{r.total_clicks.toLocaleString("id-ID")}</TableCell>
                    <TableCell className="text-lg">{trendIcon(r.trend)}</TableCell>
                    <TableCell>{Number(r.score).toFixed(1)}</TableCell>
                    <TableCell className="text-xs">{r.decision}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {pivotedEpc.data.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">EPC Trend 14 Hari (Top 5 Niche)</h2>
          <LineChart
            data={pivotedEpc.data}
            xKey="date"
            lines={pivotedEpc.niches.map((n, i) => ({ key: n, color: COLORS[i % COLORS.length] }))}
          />
        </div>
      )}
    </div>
  );
}
