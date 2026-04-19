"use client";

import { useDashboard } from "@/lib/api";
import { formatIDR } from "@/lib/utils";
import { KpiCard } from "@/components/layout/kpi-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface ReturnRow {
  id: number;
  order_id: number;
  reason: string;
  status: string;
  created_at: string;
  buyer_name: string;
  city: string;
  sale_price_idr: number;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-600",
  approved: "bg-green-600",
  rejected: "bg-red-600",
  resolved: "bg-zinc-600",
};

export default function ReturnsPage() {
  const { data: returns, mutate } = useDashboard<ReturnRow[]>("/returns");

  const pending = (returns || []).filter((r) => r.status === "pending").length;
  const approved = (returns || []).filter((r) => r.status === "approved").length;
  const totalValue = (returns || []).reduce((sum, r) => sum + r.sale_price_idr, 0);

  async function handleAction(returnId: number, action: "approve" | "reject", note?: string) {
    const url = `/api/dashboard/returns/${returnId}/${action}`;
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note: note || "" }),
    });
    mutate();
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Returns & Disputes</h1>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard title="Total Returns" value={String(returns?.length || 0)} />
        <KpiCard
          title="Pending Review"
          value={String(pending)}
          delta={pending > 0 ? "Perlu tindakan" : "Bersih"}
          deltaType={pending > 0 ? "negative" : "positive"}
          alert={pending > 0}
        />
        <KpiCard title="Approved" value={String(approved)} />
        <KpiCard title="Total Value" value={formatIDR(totalValue)} delta="nilai return aktif" deltaType="neutral" />
      </div>

      {/* Returns Table */}
      <Card>
        <CardHeader><CardTitle>Return Requests Aktif</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Order</TableHead>
                <TableHead>Buyer</TableHead>
                <TableHead>Alasan</TableHead>
                <TableHead>Nilai</TableHead>
                <TableHead>Tanggal</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Aksi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(returns || []).map((r) => (
                <TableRow key={r.id}>
                  <TableCell>#{r.id}</TableCell>
                  <TableCell>#{r.order_id}</TableCell>
                  <TableCell>{r.buyer_name} · {r.city}</TableCell>
                  <TableCell className="max-w-40 truncate">{r.reason}</TableCell>
                  <TableCell>{formatIDR(r.sale_price_idr)}</TableCell>
                  <TableCell>{new Date(r.created_at).toLocaleDateString("id-ID")}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-0.5 rounded text-xs ${STATUS_COLORS[r.status] || "bg-zinc-600"}`}>
                      {r.status}
                    </span>
                  </TableCell>
                  <TableCell>
                    {r.status === "pending" && (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-green-400 border-green-700 hover:bg-green-900"
                          onClick={() => handleAction(r.id, "approve")}
                        >
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-400 border-red-700 hover:bg-red-900"
                          onClick={() => handleAction(r.id, "reject", "Tidak memenuhi syarat retur")}
                        >
                          Reject
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {!returns?.length && (
                <TableRow>
                  <TableCell colSpan={8} className="text-zinc-500 text-center py-8">
                    Tidak ada return request aktif
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
