"use client";

import { useDashboard } from "@/lib/api";
import { formatIDR, formatPct } from "@/lib/utils";
import { KpiCard } from "@/components/layout/kpi-card";
import { BarChart } from "@/components/charts/bar-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface BIData {
  unique_customers_30d: number;
  revenue_by_city: Array<{ city: string; revenue: number; order_count: number }>;
  margin_by_niche: Array<{ niche: string; avg_margin_pct: number; total_revenue: number; total_orders: number }>;
  profitability_by_platform: Array<{ platform: string; orders: number; revenue: number; net_profit: number; net_margin_pct: number }>;
  seasonal_comparison: Array<{ period: string; revenue: number; orders: number }>;
}

export default function BusinessIntelligencePage() {
  const { data, isLoading, error } = useDashboard<BIData>("/business-intelligence");

  if (isLoading) return <p className="p-6 text-zinc-400">Loading...</p>;
  if (error || !data) return <p className="p-6 text-red-400">Failed to load BI data.</p>;

  const bestNiche = data.margin_by_niche[0];
  const bestCity = data.revenue_by_city[0];
  const currentWeek = data.seasonal_comparison.find((r) => r.period === "current_week");
  const lastYearWeek = data.seasonal_comparison.find((r) => r.period === "last_year_week");
  const yoyChange = currentWeek && lastYearWeek && lastYearWeek.revenue > 0
    ? ((currentWeek.revenue - lastYearWeek.revenue) / lastYearWeek.revenue) * 100
    : null;

  const cityChartData = data.revenue_by_city.map((r) => ({ city: r.city, revenue: r.revenue }));
  const nicheChartData = data.margin_by_niche.map((r) => ({ niche: r.niche, margin: Number(r.avg_margin_pct) }));

  const today = new Date().toISOString().slice(0, 10);
  const monthStart = today.slice(0, 7) + "-01";

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Business Intelligence</h1>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          title="Best Niche (margin)"
          value={bestNiche ? bestNiche.niche : "-"}
          delta={bestNiche ? `${bestNiche.avg_margin_pct}% margin` : undefined}
          deltaType="neutral"
        />
        <KpiCard
          title="Best City (revenue)"
          value={bestCity ? bestCity.city : "-"}
          delta={bestCity ? formatIDR(bestCity.revenue) : undefined}
          deltaType="neutral"
        />
        <KpiCard
          title="Unique Customers 30d"
          value={String(data.unique_customers_30d)}
        />
        <KpiCard
          title="Revenue YoY Change"
          value={yoyChange !== null ? `${yoyChange >= 0 ? "+" : ""}${yoyChange.toFixed(1)}%` : "-"}
          delta="vs same week last year"
          deltaType="neutral"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>Revenue by City (Top 10)</CardTitle></CardHeader>
          <CardContent>
            <BarChart
              data={cityChartData}
              xKey="city"
              bars={[{ key: "revenue", color: "#3b82f6" }]}
              layout="vertical"
              height={320}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Avg Margin by Niche (%)</CardTitle></CardHeader>
          <CardContent>
            <BarChart
              data={nicheChartData}
              xKey="niche"
              bars={[{ key: "margin", color: "#22c55e" }]}
              height={320}
            />
          </CardContent>
        </Card>
      </div>

      {/* Platform profitability */}
      <Card>
        <CardHeader><CardTitle>Profitability by Platform</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Platform</TableHead>
                <TableHead className="text-right">Orders</TableHead>
                <TableHead className="text-right">Revenue</TableHead>
                <TableHead className="text-right">Net Profit</TableHead>
                <TableHead className="text-right">Net Margin</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.profitability_by_platform.map((r) => (
                <TableRow key={r.platform}>
                  <TableCell className="capitalize">{r.platform}</TableCell>
                  <TableCell className="text-right">{r.orders}</TableCell>
                  <TableCell className="text-right">{formatIDR(r.revenue)}</TableCell>
                  <TableCell className="text-right">{formatIDR(r.net_profit)}</TableCell>
                  <TableCell className="text-right">{r.net_margin_pct}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Export buttons */}
      <div className="flex gap-3">
        <a
          href={`/api/dashboard/export/orders-csv?date_from=${monthStart}&date_to=${today}`}
          className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm transition-colors"
        >
          Export Orders CSV
        </a>
        <a
          href={`/api/dashboard/export/affiliate-csv?month=${monthStart}`}
          className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm transition-colors"
        >
          Export Affiliate CSV
        </a>
        <a
          href="/api/dashboard/export/products-excel"
          className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm transition-colors"
        >
          Export Products Excel
        </a>
      </div>
    </div>
  );
}
