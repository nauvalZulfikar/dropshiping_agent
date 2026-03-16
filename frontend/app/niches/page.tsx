"use client";

import { useQuery } from "@tanstack/react-query";
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, ZAxis } from "recharts";
import { api } from "@/lib/api-client";

export default function NichesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["analytics", "niche-map"],
    queryFn: () => api.get("/api/analytics/niche-map").then((r) => r.data),
    staleTime: 60 * 60 * 1000,
  });

  const items = (data?.items ?? []).map((item: Record<string, unknown>) => ({
    ...item,
    x: Number(item.avg_margin ?? 0),
    y: Number(item.market_size_idr ?? 0) / 1_000_000,
    z: Number(item.listing_count ?? 1),
  }));

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-2">Niche Explorer</h1>
      <p className="text-muted-foreground mb-8">
        X = Avg Margin % · Y = Market Size (IDR juta) · Bubble size = Listing count
      </p>

      {isLoading ? (
        <div className="bg-card rounded-lg border border-border h-96 animate-pulse" />
      ) : (
        <div className="bg-card rounded-lg border border-border p-4 h-96 mb-8">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart>
              <XAxis dataKey="x" name="Avg Margin %" unit="%" tick={{ fill: "#94a3b8", fontSize: 12 }} label={{ value: "Avg Margin %", position: "insideBottom", offset: -5, fill: "#94a3b8" }} />
              <YAxis dataKey="y" name="Market Size" unit="M" tick={{ fill: "#94a3b8", fontSize: 12 }} label={{ value: "Market Size (IDR juta)", angle: -90, position: "insideLeft", fill: "#94a3b8" }} />
              <ZAxis dataKey="z" range={[50, 500]} />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="bg-card border border-border rounded p-3 text-sm">
                      <p className="font-bold">{d.niche}</p>
                      <p>Margin: {d.x.toFixed(1)}%</p>
                      <p>Market: Rp {(d.y * 1_000_000).toLocaleString("id-ID")}</p>
                      <p>Listings: {d.listing_count}</p>
                    </div>
                  );
                }}
              />
              <Scatter data={items} fill="#3b82f6" fillOpacity={0.7} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-secondary text-muted-foreground">
            <tr>
              {["Niche", "Avg Margin %", "Market Size (IDR)", "Sellers", "Avg Trend", "Listings"].map((h) => (
                <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data?.items ?? []).map((item: Record<string, unknown>) => (
              <tr key={String(item.slug)} className="border-t border-border hover:bg-secondary/30">
                <td className="px-4 py-3 font-medium">{String(item.niche)}</td>
                <td className={`px-4 py-3 font-semibold ${Number(item.avg_margin) >= 30 ? "text-green-400" : Number(item.avg_margin) >= 15 ? "text-yellow-400" : "text-red-400"}`}>
                  {item.avg_margin != null ? `${Number(item.avg_margin).toFixed(1)}%` : "—"}
                </td>
                <td className="px-4 py-3 font-mono">{item.market_size_idr != null ? Number(item.market_size_idr).toLocaleString("id-ID") : "—"}</td>
                <td className="px-4 py-3">{item.seller_count?.toLocaleString() ?? "—"}</td>
                <td className="px-4 py-3">{item.avg_trend_score != null ? Number(item.avg_trend_score).toFixed(1) : "—"}</td>
                <td className="px-4 py-3">{item.listing_count?.toLocaleString() ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
