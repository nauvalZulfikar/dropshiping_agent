"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";

export default function ProductsPage() {
  const [platform, setPlatform] = useState("");
  const [minMargin, setMinMargin] = useState(0);
  const [sortBy, setSortBy] = useState("opportunity_score");
  const [gateOnly, setGateOnly] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["products", platform, minMargin, sortBy, gateOnly, page],
    queryFn: () =>
      api
        .get("/api/products", {
          params: {
            platform: platform || undefined,
            min_margin: minMargin || undefined,
            sort_by: sortBy,
            gate_passed: gateOnly ? true : undefined,
            page,
            limit: 20,
          },
        })
        .then((r) => r.data),
  });

  const items = data?.items ?? [];
  const total: number = data?.total ?? 0;
  const pages: number = data?.pages ?? 1;

  return (
    <main className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-1">Products</h1>
          {total > 0 && (
            <p className="text-muted-foreground text-sm">{total.toLocaleString()} listings</p>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6 items-end flex-wrap">
        <div>
          <label className="text-sm text-muted-foreground block mb-1">Platform</label>
          <select
            className="bg-card border border-border rounded px-3 py-2 text-sm"
            value={platform}
            onChange={(e) => { setPlatform(e.target.value); setPage(1); }}
          >
            <option value="">All</option>
            <option value="tokopedia">Tokopedia</option>
            <option value="shopee">Shopee</option>
            <option value="lazada">Lazada</option>
            <option value="tiktok_shop">TikTok Shop</option>
          </select>
        </div>
        <div>
          <label className="text-sm text-muted-foreground block mb-1">Min Margin %</label>
          <input
            type="number"
            className="bg-card border border-border rounded px-3 py-2 text-sm w-24"
            value={minMargin || ""}
            onChange={(e) => { setMinMargin(Number(e.target.value)); setPage(1); }}
          />
        </div>
        <div>
          <label className="text-sm text-muted-foreground block mb-1">Sort By</label>
          <select
            className="bg-card border border-border rounded px-3 py-2 text-sm"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="opportunity_score">Opportunity Score</option>
            <option value="margin_pct">Margin %</option>
            <option value="sold_30d">Sold 30d</option>
            <option value="trend_score">Trend Score</option>
          </select>
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer select-none pb-2">
          <input
            type="checkbox"
            className="rounded border-border"
            checked={gateOnly}
            onChange={(e) => { setGateOnly(e.target.checked); setPage(1); }}
          />
          Gate passed only
        </label>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-secondary text-muted-foreground">
            <tr>
              {["#", "Product", "Platform", "Price (IDR)", "Margin%", "Sold 30d", "Score", "Gate"].map((h) => (
                <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-t border-border animate-pulse">
                    {Array.from({ length: 8 }).map((_, j) => (
                      <td key={j} className="px-4 py-3"><div className="h-4 bg-secondary rounded" /></td>
                    ))}
                  </tr>
                ))
              : items.map((p: Record<string, unknown>, idx: number) => (
                  <tr key={String(p.id)} className="border-t border-border hover:bg-secondary/30 transition-colors">
                    <td className="px-4 py-3 text-muted-foreground">{(page - 1) * 20 + idx + 1}</td>
                    <td className="px-4 py-3 max-w-xs">
                      <a href={`/products/${String(p.id)}`} className="hover:text-primary line-clamp-1">{String(p.title)}</a>
                    </td>
                    <td className="px-4 py-3 capitalize">{String(p.platform)}</td>
                    <td className="px-4 py-3 font-mono">{Number(p.price_idr).toLocaleString("id-ID")}</td>
                    <td className={`px-4 py-3 font-semibold ${Number(p.margin_pct) >= 30 ? "text-green-400" : Number(p.margin_pct) >= 15 ? "text-yellow-400" : "text-red-400"}`}>
                      {p.margin_pct != null ? `${Number(p.margin_pct).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3">{p.sold_30d != null ? Number(p.sold_30d).toLocaleString() : "—"}</td>
                    <td className="px-4 py-3 font-semibold">{p.opportunity_score != null ? Number(p.opportunity_score).toFixed(1) : "—"}</td>
                    <td className="px-4 py-3">{p.gate_passed ? "✅" : "❌"}</td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex gap-2 mt-4 items-center">
        <button
          className="px-4 py-2 bg-secondary rounded border border-border disabled:opacity-40 text-sm"
          disabled={page === 1}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </button>
        <span className="text-muted-foreground text-sm">Page {page} / {pages}</span>
        <button
          className="px-4 py-2 bg-secondary rounded border border-border disabled:opacity-40 text-sm"
          disabled={page >= pages}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>
    </main>
  );
}
