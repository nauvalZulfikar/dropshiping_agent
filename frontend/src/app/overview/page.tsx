"use client";

import { useDashboard } from "@/lib/api";
import { formatIDR, formatPct } from "@/lib/utils";
import { KpiCard } from "@/components/layout/kpi-card";
import { LineChart } from "@/components/charts/line-chart";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface OverviewData {
  rev_today: number;
  rev_yesterday: number;
  orders_today: number;
  orders_yesterday: number;
  margin_7d: number;
  margin_prev_7d: number;
  critical_stock: number;
  zero_stock: number;
  pending_old: number;
  margin_low: boolean;
}

interface RevenueRow {
  date: string;
  revenue: number;
  net_profit: number;
}

interface OrderRow {
  created_at: string;
  platform: string;
  product: string;
  city: string;
  price: number;
  status: string;
}

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-500",
  sent_to_supplier: "bg-yellow-500",
  shipped: "bg-green-500",
  delivered: "bg-emerald-600",
  returned: "bg-red-500",
};

export default function OverviewPage() {
  const { data: kpi } = useDashboard<OverviewData>("/overview");
  const { data: revenue } = useDashboard<RevenueRow[]>("/overview/revenue-30d");
  const { data: orders } = useDashboard<OrderRow[]>("/overview/recent-orders?limit=20");

  if (!kpi) return <div className="animate-pulse text-zinc-500">Loading...</div>;

  const revDelta = kpi.rev_yesterday > 0
    ? ((kpi.rev_today - kpi.rev_yesterday) / kpi.rev_yesterday * 100).toFixed(1)
    : "0";
  const marginDelta = ((kpi.margin_7d - kpi.margin_prev_7d) * 100).toFixed(1);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Overview</h1>

      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          title="Revenue Hari Ini"
          value={formatIDR(kpi.rev_today)}
          delta={`${Number(revDelta) >= 0 ? "+" : ""}${revDelta}% vs kemarin`}
          deltaType={Number(revDelta) >= 0 ? "positive" : "negative"}
        />
        <KpiCard
          title="Order Masuk"
          value={kpi.orders_today}
          delta={`${kpi.orders_today - kpi.orders_yesterday >= 0 ? "+" : ""}${kpi.orders_today - kpi.orders_yesterday} vs kemarin`}
          deltaType={kpi.orders_today >= kpi.orders_yesterday ? "positive" : "negative"}
        />
        <KpiCard
          title="Margin Rata-rata 7d"
          value={formatPct(kpi.margin_7d)}
          delta={`${Number(marginDelta) >= 0 ? "+" : ""}${marginDelta}pp`}
          deltaType={Number(marginDelta) >= 0 ? "positive" : "negative"}
        />
        <KpiCard
          title="Stok Kritis"
          value={kpi.critical_stock}
          alert={kpi.critical_stock > 0}
        />
      </div>

      {/* Alerts */}
      {kpi.zero_stock > 0 && (
        <div className="bg-red-950/50 border border-red-800 rounded-lg p-3 text-red-200 text-sm">
          {kpi.zero_stock} produk kehabisan stok — listing dinonaktifkan
        </div>
      )}
      {kpi.pending_old > 0 && (
        <div className="bg-yellow-950/50 border border-yellow-800 rounded-lg p-3 text-yellow-200 text-sm">
          {kpi.pending_old} order status &apos;new&apos; belum diproses &gt;2 jam
        </div>
      )}
      {kpi.margin_low && (
        <div className="bg-yellow-950/50 border border-yellow-800 rounded-lg p-3 text-yellow-200 text-sm">
          Margin di bawah 15% di 5 order terakhir
        </div>
      )}

      {/* Revenue Chart */}
      {revenue && revenue.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Revenue & Profit 30 Hari</h2>
          <LineChart
            data={revenue}
            xKey="date"
            lines={[
              { key: "revenue", color: "#3b82f6" },
              { key: "net_profit", color: "#22c55e", dashed: true },
            ]}
          />
        </div>
      )}

      {/* Recent Orders */}
      {orders && orders.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Order Terbaru</h2>
          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800">
                  <TableHead>Waktu</TableHead>
                  <TableHead>Platform</TableHead>
                  <TableHead>Produk</TableHead>
                  <TableHead>Kota</TableHead>
                  <TableHead>Harga</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((o, i) => (
                  <TableRow key={i} className="border-zinc-800">
                    <TableCell className="text-xs text-zinc-400">
                      {new Date(o.created_at).toLocaleString("id-ID", { timeZone: "Asia/Jakarta" })}
                    </TableCell>
                    <TableCell>{o.platform}</TableCell>
                    <TableCell className="max-w-48 truncate">{o.product}</TableCell>
                    <TableCell>{o.city}</TableCell>
                    <TableCell>{formatIDR(o.price)}</TableCell>
                    <TableCell>
                      <Badge className={`${STATUS_COLORS[o.status] || "bg-gray-500"} text-white text-xs`}>
                        {o.status}
                      </Badge>
                    </TableCell>
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
