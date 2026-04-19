"use client";

import { useDashboard } from "@/lib/api";
import { KpiCard } from "@/components/layout/kpi-card";
import { BarChart } from "@/components/charts/bar-chart";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { useMemo } from "react";

interface ActiveOrder {
  id: number;
  platform: string;
  product: string;
  buyer_name: string;
  city: string;
  courier: string;
  status: string;
  hours_since_created: number;
  resi: string | null;
}

interface SupplierPerf {
  name: string;
  avg_delivery_days: number;
  fulfillment_rate: number;
  return_rate_pct: number;
  orders_this_month: number;
}

export default function OrdersPage() {
  const { data: active } = useDashboard<ActiveOrder[]>("/orders/active");
  const { data: suppliers } = useDashboard<SupplierPerf[]>("/orders/supplier-performance");

  const kpis = useMemo(() => {
    if (!active) return null;
    const pending = active.filter((o) => o.status === "new").length;
    const shipping = active.filter((o) => o.status === "shipped").length;
    return { total: active.length, pending, shipping };
  }, [active]);

  const funnel = useMemo(() => {
    if (!active) return [];
    const counts: Record<string, number> = {};
    for (const o of active) counts[o.status] = (counts[o.status] || 0) + 1;
    return ["new", "sent_to_supplier", "shipped"].map((s) => ({
      status: s,
      count: counts[s] || 0,
    }));
  }, [active]);

  function rowClass(o: ActiveOrder) {
    if (o.status === "sent_to_supplier" && o.hours_since_created > 12 && !o.resi)
      return "bg-red-950/40";
    if (o.status === "new" && o.hours_since_created > 2) return "bg-yellow-950/40";
    return "";
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Orders & Fulfillment</h1>

      {kpis && (
        <div className="grid grid-cols-4 gap-4">
          <KpiCard title="Order Aktif" value={kpis.total} />
          <KpiCard title="Pending" value={kpis.pending} alert={kpis.pending > 0} />
          <KpiCard title="Dalam Pengiriman" value={kpis.shipping} />
          <KpiCard title="Return Rate 30d" value="—" />
        </div>
      )}

      {funnel.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Order Funnel</h2>
          <BarChart
            data={funnel}
            xKey="status"
            bars={[{ key: "count", color: "#3b82f6" }]}
            height={200}
          />
        </div>
      )}

      {active && active.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Order Aktif</h2>
          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800">
                  <TableHead>ID</TableHead>
                  <TableHead>Platform</TableHead>
                  <TableHead>Produk</TableHead>
                  <TableHead>Buyer</TableHead>
                  <TableHead>Kota</TableHead>
                  <TableHead>Kurir</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {active.map((o) => (
                  <TableRow key={o.id} className={`border-zinc-800 ${rowClass(o)}`}>
                    <TableCell>#{o.id}</TableCell>
                    <TableCell>{o.platform}</TableCell>
                    <TableCell className="max-w-40 truncate">{o.product}</TableCell>
                    <TableCell>{o.buyer_name}</TableCell>
                    <TableCell>{o.city}</TableCell>
                    <TableCell>{o.courier}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">{o.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {suppliers && suppliers.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Supplier Performance</h2>
          <div className="rounded-lg border border-zinc-800 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800">
                  <TableHead>Supplier</TableHead>
                  <TableHead>Avg Delivery (hari)</TableHead>
                  <TableHead>Fulfillment Rate</TableHead>
                  <TableHead>Return Rate</TableHead>
                  <TableHead>Order Bulan Ini</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {suppliers.map((s) => (
                  <TableRow key={s.name} className="border-zinc-800">
                    <TableCell className="font-medium">{s.name}</TableCell>
                    <TableCell>{Number(s.avg_delivery_days).toFixed(1)}</TableCell>
                    <TableCell>{s.fulfillment_rate != null ? `${Number(s.fulfillment_rate).toFixed(1)}%` : "—"}</TableCell>
                    <TableCell>{Number(s.return_rate_pct).toFixed(1)}%</TableCell>
                    <TableCell>{s.orders_this_month}</TableCell>
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
