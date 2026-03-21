"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api-client";

interface Supplier {
  id: string;
  source: string;
  title?: string;
  url?: string;
  price_idr?: number;
  shipping_cost_idr?: number;
  moq?: number;
  seller_name?: string;
  rating?: number;
  review_count?: number;
  product_name?: string;
}

export default function SuppliersPage() {
  const [source, setSource] = useState("");
  const [maxPrice, setMaxPrice] = useState(0);
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery<{ items: Supplier[]; total: number }>({
    queryKey: ["suppliers", source, maxPrice, page],
    queryFn: () =>
      api.get("/api/suppliers", {
        params: {
          source: source || undefined,
          max_price_idr: maxPrice || undefined,
          page,
          limit: 30,
        },
      }).then((r) => r.data),
  });

  const items = data?.items ?? [];

  return (
    <main className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-1">Suppliers</h1>
        <p className="text-muted-foreground text-sm">AliExpress & 1688 supplier database matched to products</p>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6 items-end flex-wrap">
        <div>
          <label className="text-sm text-muted-foreground block mb-1">Source</label>
          <select
            className="bg-card border border-border rounded px-3 py-2 text-sm"
            value={source}
            onChange={(e) => { setSource(e.target.value); setPage(1); }}
          >
            <option value="">All</option>
            <option value="aliexpress">AliExpress</option>
            <option value="1688">1688</option>
          </select>
        </div>
        <div>
          <label className="text-sm text-muted-foreground block mb-1">Max Price (IDR)</label>
          <input
            type="number"
            className="bg-card border border-border rounded px-3 py-2 text-sm w-36"
            placeholder="e.g. 500000"
            value={maxPrice || ""}
            onChange={(e) => { setMaxPrice(Number(e.target.value)); setPage(1); }}
          />
        </div>
        {data?.total != null && (
          <div className="text-sm text-muted-foreground self-center">
            {data.total.toLocaleString()} suppliers
          </div>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-secondary text-muted-foreground">
            <tr>
              {["Source", "Title / Product", "Price (IDR)", "Shipping", "Sold", "MOQ", "Seller", "Rating"].map((h) => (
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
              : items.map((s) => (
                  <tr key={s.id} className="border-t border-border hover:bg-secondary/30 transition-colors">
                    <td className="px-4 py-3 capitalize text-xs font-medium text-muted-foreground">{s.source}</td>
                    <td className="px-4 py-3 max-w-xs">
                      {s.url ? (
                        <a href={s.url} target="_blank" rel="noopener noreferrer" className="hover:text-primary line-clamp-1">
                          {s.title ?? "—"}
                        </a>
                      ) : (
                        <span className="line-clamp-1">{s.title ?? "—"}</span>
                      )}
                      {s.product_name && (
                        <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">↳ {s.product_name}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono">{s.price_idr != null ? Number(s.price_idr).toLocaleString("id-ID") : "—"}</td>
                    <td className="px-4 py-3 font-mono">{s.shipping_cost_idr != null ? Number(s.shipping_cost_idr).toLocaleString("id-ID") : "—"}</td>
                    <td className="px-4 py-3 font-mono">{s.review_count ? s.review_count.toLocaleString("id-ID") : "—"}</td>
                    <td className="px-4 py-3">{s.moq ?? 1}</td>
                    <td className="px-4 py-3 text-xs">{s.seller_name ?? "—"}</td>
                    <td className="px-4 py-3">{s.rating != null ? `${Number(s.rating).toFixed(1)}/5` : "—"}</td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>

      <div className="flex gap-2 mt-4 items-center">
        <button
          className="px-4 py-2 bg-secondary rounded border border-border disabled:opacity-40 text-sm"
          disabled={page === 1}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </button>
        <span className="text-muted-foreground text-sm">Page {page}</span>
        <button
          className="px-4 py-2 bg-secondary rounded border border-border disabled:opacity-40 text-sm"
          disabled={items.length < 30}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>
    </main>
  );
}
