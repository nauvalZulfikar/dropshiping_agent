"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api-client";

interface Product {
  id: string;
  title: string;
  platform: string;
  price_idr: number;
  image_url?: string;
  margin_pct?: number;
  opportunity_score?: number;
  gate_passed?: boolean;
}

interface Trend {
  keyword: string;
  peak_value: number;
}

interface Summary {
  total_listings: number;
  gate_passed_count: number;
  unique_products: number;
  avg_margin_pct: number;
  avg_opportunity_score: number;
  platforms_tracked: number;
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-card rounded-lg p-5 border border-border">
      <p className="text-muted-foreground text-xs uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { data: summary } = useQuery<Summary>({
    queryKey: ["analytics", "summary"],
    queryFn: () => api.get("/api/analytics/summary").then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const { data: topData, isLoading } = useQuery<{ items: Product[] }>({
    queryKey: ["products", "top"],
    queryFn: () => api.get("/api/products/top").then((r) => r.data),
    staleTime: 15 * 60 * 1000,
  });

  const { data: trendsData } = useQuery<{ items: Trend[] }>({
    queryKey: ["analytics", "trends"],
    queryFn: () => api.get("/api/analytics/trends").then((r) => r.data),
    staleTime: 10 * 60 * 1000,
  });

  return (
    <main className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-1">Dashboard</h1>
        <p className="text-muted-foreground text-sm">Indonesian marketplace intelligence · updated hourly</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-10">
        <StatCard label="Total Listings" value={summary?.total_listings?.toLocaleString() ?? "—"} />
        <StatCard
          label="Gate Passed"
          value={summary?.gate_passed_count?.toLocaleString() ?? "—"}
          sub={
            summary?.total_listings
              ? `${((summary.gate_passed_count / summary.total_listings) * 100).toFixed(1)}% of total`
              : undefined
          }
        />
        <StatCard label="Unique Products" value={summary?.unique_products?.toLocaleString() ?? "—"} />
        <StatCard
          label="Avg Margin"
          value={summary?.avg_margin_pct != null ? `${Number(summary.avg_margin_pct).toFixed(1)}%` : "—"}
        />
        <StatCard
          label="Avg Opp Score"
          value={summary?.avg_opportunity_score != null ? Number(summary.avg_opportunity_score).toFixed(1) : "—"}
          sub="/ 100"
        />
        <StatCard label="Platforms" value={summary?.platforms_tracked?.toString() ?? "—"} />
      </div>

      {/* Top products */}
      <section className="mb-10">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Top Opportunity Products</h2>
          <Link href="/products" className="text-sm text-primary hover:underline">View all →</Link>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="bg-card rounded-lg p-4 border border-border animate-pulse h-40" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(topData?.items ?? []).map((p) => (
              <Link
                key={p.id}
                href={`/products/${p.id}`}
                className="bg-card rounded-lg p-4 border border-border hover:border-primary/60 transition-colors block"
              >
                <div className="flex gap-3">
                  {p.image_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.image_url} alt="" className="w-16 h-16 object-cover rounded flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm line-clamp-2 mb-1">{p.title}</p>
                    <p className="text-xs text-muted-foreground capitalize">{p.platform}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
                  <p className="font-bold">Rp {Number(p.price_idr).toLocaleString("id-ID")}</p>
                  <div className="flex items-center gap-3 text-sm">
                    <span className={`font-semibold ${Number(p.margin_pct) >= 30 ? "text-green-400" : Number(p.margin_pct) >= 15 ? "text-yellow-400" : "text-red-400"}`}>
                      {p.margin_pct != null ? `${Number(p.margin_pct).toFixed(1)}%` : "—"}
                    </span>
                    <span className={`font-bold ${Number(p.opportunity_score) >= 70 ? "text-green-400" : Number(p.opportunity_score) >= 45 ? "text-yellow-400" : "text-red-400"}`}>
                      {p.opportunity_score != null ? Number(p.opportunity_score).toFixed(0) : "—"}
                    </span>
                    <span>{p.gate_passed ? "✅" : "❌"}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Trending keywords */}
      {(trendsData?.items?.length ?? 0) > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-4">Trending in Indonesia</h2>
          <div className="flex flex-wrap gap-2">
            {(trendsData?.items ?? []).map((t) => (
              <span
                key={t.keyword}
                className="bg-secondary px-3 py-1.5 rounded-full text-sm border border-border flex items-center gap-1.5"
              >
                {t.keyword}
                <span className="text-primary font-semibold text-xs">{t.peak_value}</span>
              </span>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
