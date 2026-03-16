"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import Link from "next/link";
import { api } from "@/lib/api-client";

interface Props {
  params: { id: string };
}

function ScoreBar({ label, value }: { label: string; value?: number }) {
  const pct = value != null ? Math.min(value, 100) : 0;
  const color = pct >= 70 ? "bg-green-500" : pct >= 45 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold">{value != null ? value.toFixed(1) : "—"}</span>
      </div>
      <div className="h-2 bg-secondary rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const GATE_KEYS = ["margin", "demand", "trend", "competition", "supplier"];
const GATE_LABELS: Record<string, string> = {
  margin: "Gate 1 · Net margin ≥ 20%",
  demand: "Gate 2 · Sold ≥ 300/month",
  trend: "Gate 3 · Trend score ≥ 40",
  competition: "Gate 4 · Competition ≥ 35",
  supplier: "Gate 5 · Supplier ≤ 40% of price",
};

export default function ProductDetailPage({ params }: Props) {
  const { id } = params;
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: () => api.get(`/api/products/${id}`).then((r) => r.data),
  });

  const scoreMutation = useMutation({
    mutationFn: () => api.post(`/api/products/${id}/score`),
    onSuccess: () => {
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["product", id] }), 3000);
    },
  });

  const watchMutation = useMutation({
    mutationFn: () =>
      api.post("/api/watchlist", {
        listing_id: id,
        alert_on_price_drop: true,
        alert_on_spike: true,
      }),
  });

  if (isLoading) {
    return (
      <div className="p-8 space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card rounded-lg border border-border h-32 animate-pulse" />
        ))}
      </div>
    );
  }

  const listing = data?.listing;
  const priceHistory = data?.price_history ?? [];
  const suppliers = data?.suppliers ?? [];
  const competition = data?.competition ?? {};
  const platformComparison: Record<string, unknown>[] = data?.platform_comparison ?? [];
  const gatesFailed: string[] = listing?.gates_failed ?? [];

  return (
    <main className="p-8 max-w-5xl">
      {/* Breadcrumb */}
      <nav className="text-sm text-muted-foreground mb-6">
        <Link href="/products" className="hover:text-foreground">Products</Link>
        <span className="mx-2">/</span>
        <span className="text-foreground line-clamp-1">{listing?.title}</span>
      </nav>

      {/* Header */}
      <div className="flex gap-6 mb-8">
        {listing?.image_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={listing.image_url} alt={listing.title} className="w-48 h-48 object-cover rounded-lg border border-border flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <h1 className="text-2xl font-bold mb-2 leading-tight">{listing?.title}</h1>
            <div className="flex gap-2 flex-shrink-0">
              <button
                onClick={() => watchMutation.mutate()}
                disabled={watchMutation.isPending || watchMutation.isSuccess}
                className="px-3 py-1.5 text-xs bg-primary/10 text-primary border border-primary/30 rounded hover:bg-primary/20 transition-colors disabled:opacity-50"
              >
                {watchMutation.isSuccess ? "Watching ✓" : watchMutation.isPending ? "Adding…" : "+ Watchlist"}
              </button>
              <button
                onClick={() => scoreMutation.mutate()}
                disabled={scoreMutation.isPending}
                className="px-3 py-1.5 text-xs bg-secondary border border-border rounded hover:border-primary transition-colors disabled:opacity-50"
              >
                {scoreMutation.isPending ? "Queued…" : "Rescore"}
              </button>
            </div>
          </div>
          <p className="text-muted-foreground capitalize mb-1 text-sm">
            {listing?.platform} · {listing?.seller_name}
            {listing?.seller_city ? ` · ${listing.seller_city}` : ""}
          </p>
          {listing?.seller_badge && (
            <span className="inline-block text-xs bg-yellow-500/10 text-yellow-400 border border-yellow-500/30 px-2 py-0.5 rounded mb-2">
              {listing.seller_badge}
            </span>
          )}
          <p className="text-3xl font-bold mt-3">
            Rp {Number(listing?.price_idr).toLocaleString("id-ID")}
          </p>
          <div className="flex gap-4 mt-3 text-sm flex-wrap">
            <span>Sold 30d: <strong>{listing?.sold_30d?.toLocaleString() ?? "—"}</strong></span>
            <span>Reviews: <strong>{listing?.review_count?.toLocaleString() ?? "—"}</strong></span>
            <span>Rating: <strong>{listing?.rating != null ? `${Number(listing.rating).toFixed(1)}/5` : "—"}</strong></span>
          </div>
          {listing?.url && (
            <a href={listing.url} target="_blank" rel="noopener noreferrer" className="inline-block mt-3 text-sm text-primary hover:underline">
              View on {listing.platform} →
            </a>
          )}
        </div>
      </div>

      {/* Scores & Gates */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-card rounded-lg p-5 border border-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Opportunity Score</h2>
            <span className={`text-2xl font-bold ${Number(listing?.opportunity_score) >= 70 ? "text-green-400" : Number(listing?.opportunity_score) >= 45 ? "text-yellow-400" : "text-red-400"}`}>
              {listing?.opportunity_score != null ? Number(listing.opportunity_score).toFixed(1) : "—"}
              <span className="text-sm text-muted-foreground font-normal">/100</span>
            </span>
          </div>
          <div className="space-y-3">
            <ScoreBar label="Margin (35%)" value={listing?.margin_pct} />
            <ScoreBar label="Sellability (30%)" value={listing?.sellability_score} />
            <ScoreBar label="Trend (20%)" value={listing?.trend_score} />
            <ScoreBar label="Competition (15%)" value={listing?.competition_score} />
          </div>
        </div>

        <div className="bg-card rounded-lg p-5 border border-border">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">5-Gate Filter</h2>
            <span className={`text-sm font-bold px-2 py-1 rounded ${listing?.gate_passed ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
              {listing?.gate_passed ? "PASSED" : "FAILED"}
            </span>
          </div>
          <div className="space-y-2">
            {GATE_KEYS.map((key) => {
              const passed = !gatesFailed.includes(key);
              return (
                <div key={key} className="flex items-center gap-2 text-sm">
                  <span>{passed ? "✅" : "❌"}</span>
                  <span className={passed ? "text-foreground" : "text-muted-foreground line-through"}>{GATE_LABELS[key]}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Price History */}
      {priceHistory.length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Price History (30 days)</h2>
          <div className="bg-card rounded-lg p-4 border border-border h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={priceHistory}>
                <XAxis
                  dataKey="recorded_at"
                  tickFormatter={(v) => new Date(v).toLocaleDateString("id-ID", { month: "short", day: "numeric" })}
                  tick={{ fill: "#94a3b8", fontSize: 11 }}
                />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip
                  formatter={(v: number) => [`Rp ${v.toLocaleString("id-ID")}`, "Price"]}
                  labelFormatter={(l) => new Date(l).toLocaleString("id-ID")}
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}
                />
                <Line type="monotone" dataKey="price_idr" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* Competition */}
      {Object.keys(competition).length > 0 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Competition Analysis</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Sellers", value: competition.seller_count != null ? Number(competition.seller_count).toLocaleString() : null },
              { label: "Avg Price", value: competition.avg_price_idr ? `Rp ${Number(competition.avg_price_idr).toLocaleString("id-ID")}` : null },
              { label: "Top Seller", value: competition.top_seller_name as string },
              { label: "Top Share", value: competition.top_seller_share_pct ? `${Number(competition.top_seller_share_pct).toFixed(1)}%` : null },
            ].map(({ label, value }) => (
              <div key={label} className="bg-card rounded-lg p-4 border border-border">
                <p className="text-xs text-muted-foreground mb-1">{label}</p>
                <p className="font-semibold text-sm">{value ?? "—"}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Platform comparison */}
      {platformComparison.length > 1 && (
        <section className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Platform Comparison</h2>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-muted-foreground">
                <tr>
                  {["Platform", "Price (IDR)", "Sold 30d", "Margin%", "Score"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {platformComparison.map((p) => (
                  <tr key={String(p.id)} className="border-t border-border hover:bg-secondary/30">
                    <td className="px-4 py-3 capitalize font-medium">{String(p.platform ?? "—")}</td>
                    <td className="px-4 py-3 font-mono">{p.price_idr != null ? Number(p.price_idr).toLocaleString("id-ID") : "—"}</td>
                    <td className="px-4 py-3">{p.sold_30d != null ? Number(p.sold_30d).toLocaleString() : "—"}</td>
                    <td className={`px-4 py-3 font-semibold ${Number(p.margin_pct) >= 30 ? "text-green-400" : Number(p.margin_pct) >= 15 ? "text-yellow-400" : "text-red-400"}`}>
                      {p.margin_pct != null ? `${Number(p.margin_pct).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-4 py-3">{p.opportunity_score != null ? Number(p.opportunity_score).toFixed(1) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Suppliers */}
      {suppliers.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-4">Matched Suppliers</h2>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-secondary text-muted-foreground">
                <tr>
                  {["Source", "Title", "Price (IDR)", "Shipping", "Total", "MOQ", "Rating"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {suppliers.map((s: Record<string, unknown>) => (
                  <tr key={String(s.id)} className="border-t border-border hover:bg-secondary/30">
                    <td className="px-4 py-3 capitalize">{String(s.source)}</td>
                    <td className="px-4 py-3 max-w-xs">
                      <a href={String(s.url ?? "#")} target="_blank" rel="noopener noreferrer" className="hover:text-primary line-clamp-1">
                        {String(s.title ?? "—")}
                      </a>
                    </td>
                    <td className="px-4 py-3 font-mono">{s.price_idr != null ? Number(s.price_idr).toLocaleString("id-ID") : "—"}</td>
                    <td className="px-4 py-3 font-mono">{s.shipping_cost_idr != null ? Number(s.shipping_cost_idr).toLocaleString("id-ID") : "—"}</td>
                    <td className="px-4 py-3 font-mono font-semibold">
                      {s.price_idr != null ? Number(Number(s.price_idr) + Number(s.shipping_cost_idr ?? 0)).toLocaleString("id-ID") : "—"}
                    </td>
                    <td className="px-4 py-3">{String(s.moq ?? 1)}</td>
                    <td className="px-4 py-3">{s.rating != null ? `${Number(s.rating).toFixed(1)}/5` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}
