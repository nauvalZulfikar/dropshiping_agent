"use client";

import { useState } from "react";
import { useDashboard } from "@/lib/api";
import { formatIDR } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface FlashSale {
  id: number;
  name: string;
  discount_pct: number;
  status: string;
  starts_at: string;
  ends_at: string;
}

interface NicheOpportunity {
  keyword: string;
  platform: string;
  opportunity_score: number;
  trend_direction: string;
  estimated_epc: number;
  is_tracked: boolean;
  discovered_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-600",
  scheduled: "bg-blue-600",
  ended: "bg-zinc-600",
  cancelled: "bg-red-600",
};

const TREND_ICON: Record<string, string> = {
  up: "↑",
  flat: "→",
  down: "↓",
};

export default function AutomationPage() {
  const { data: flashSales, mutate: mutateFlash } = useDashboard<FlashSale[]>("/automation/flash-sales");
  const { data: niches, mutate: mutateNiches } = useDashboard<NicheOpportunity[]>("/automation/niche-discovery");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", discount_pct: 10, duration_hours: 6, product_ids: "" });
  const [saving, setSaving] = useState(false);

  async function handleCreateFlashSale() {
    setSaving(true);
    const ids = form.product_ids.split(",").map((s) => parseInt(s.trim())).filter(Boolean);
    await fetch("/api/dashboard/automation/flash-sales", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, product_ids: ids, platforms: ["shopee", "tokopedia"] }),
    });
    mutateFlash();
    setShowForm(false);
    setSaving(false);
  }

  async function handleAddToTracking(keyword: string) {
    await fetch("/api/dashboard/automation/niche-discovery/track", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword }),
    });
    mutateNiches();
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Automation</h1>

      {/* Flash Sales */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Flash Sales</CardTitle>
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            + Buat Flash Sale
          </Button>
        </CardHeader>
        <CardContent>
          {showForm && (
            <div className="mb-4 p-4 bg-zinc-900 rounded-lg space-y-3 text-sm">
              <div>
                <label className="text-zinc-400">Nama</label>
                <input
                  className="w-full mt-1 px-3 py-1.5 bg-zinc-800 rounded border border-zinc-700 text-white"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Harbolnas Special"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-zinc-400">Diskon (%)</label>
                  <input
                    type="number"
                    className="w-full mt-1 px-3 py-1.5 bg-zinc-800 rounded border border-zinc-700 text-white"
                    value={form.discount_pct}
                    onChange={(e) => setForm({ ...form, discount_pct: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="text-zinc-400">Durasi (jam)</label>
                  <input
                    type="number"
                    className="w-full mt-1 px-3 py-1.5 bg-zinc-800 rounded border border-zinc-700 text-white"
                    value={form.duration_hours}
                    onChange={(e) => setForm({ ...form, duration_hours: Number(e.target.value) })}
                  />
                </div>
              </div>
              <div>
                <label className="text-zinc-400">Product IDs (pisah koma)</label>
                <input
                  className="w-full mt-1 px-3 py-1.5 bg-zinc-800 rounded border border-zinc-700 text-white"
                  value={form.product_ids}
                  onChange={(e) => setForm({ ...form, product_ids: e.target.value })}
                  placeholder="1, 2, 5"
                />
              </div>
              <Button size="sm" onClick={handleCreateFlashSale} disabled={saving}>
                {saving ? "Saving..." : "Buat"}
              </Button>
            </div>
          )}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nama</TableHead>
                <TableHead>Diskon</TableHead>
                <TableHead>Mulai</TableHead>
                <TableHead>Selesai</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(flashSales || []).map((s) => (
                <TableRow key={s.id}>
                  <TableCell>{s.name}</TableCell>
                  <TableCell>{s.discount_pct}%</TableCell>
                  <TableCell>{new Date(s.starts_at).toLocaleString("id-ID")}</TableCell>
                  <TableCell>{new Date(s.ends_at).toLocaleString("id-ID")}</TableCell>
                  <TableCell>
                    <span className={`px-2 py-0.5 rounded text-xs ${STATUS_COLORS[s.status] || "bg-zinc-600"}`}>
                      {s.status}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
              {!flashSales?.length && (
                <TableRow><TableCell colSpan={5} className="text-zinc-500 text-center">Belum ada flash sale</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Niche Discovery */}
      <Card>
        <CardHeader><CardTitle>Niche Discovery</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Keyword</TableHead>
                <TableHead>Opportunity Score</TableHead>
                <TableHead>Trend</TableHead>
                <TableHead>Est. EPC</TableHead>
                <TableHead>Status</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(niches || []).map((n) => (
                <TableRow key={n.keyword}>
                  <TableCell className="font-medium">{n.keyword}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-zinc-700 rounded">
                        <div
                          className="h-2 bg-green-500 rounded"
                          style={{ width: `${Math.min(n.opportunity_score, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs">{n.opportunity_score}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className={n.trend_direction === "up" ? "text-green-400" : n.trend_direction === "down" ? "text-red-400" : "text-zinc-400"}>
                      {TREND_ICON[n.trend_direction] || "→"}
                    </span>
                  </TableCell>
                  <TableCell>{formatIDR(n.estimated_epc)}</TableCell>
                  <TableCell>
                    {n.is_tracked
                      ? <Badge variant="outline" className="text-green-400 border-green-600">Tracked</Badge>
                      : <Badge variant="outline" className="text-zinc-400">Untracked</Badge>}
                  </TableCell>
                  <TableCell>
                    {!n.is_tracked && (
                      <Button size="sm" variant="outline" onClick={() => handleAddToTracking(n.keyword)}>
                        Track
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {!niches?.length && (
                <TableRow><TableCell colSpan={6} className="text-zinc-500 text-center">Belum ada data discovery</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
