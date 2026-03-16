"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api-client";

export default function WatchlistPage() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => api.get("/api/watchlist").then((r) => r.data),
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/api/watchlist/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
  });

  const items = data?.items ?? [];

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-6">Watchlist</h1>

      {isLoading ? (
        <div className="animate-pulse">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-muted-foreground">
          No products in watchlist. Add products from the{" "}
          <a href="/products" className="text-primary hover:underline">Products page</a>.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-secondary text-muted-foreground">
              <tr>
                {["Product", "Platform", "Price (IDR)", "Margin%", "Score", "Alerts", "Actions"].map((h) => (
                  <th key={h} className="text-left px-4 py-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item: Record<string, unknown>) => (
                <tr key={String(item.id)} className="border-t border-border hover:bg-secondary/30">
                  <td className="px-4 py-3 max-w-xs">
                    <a href={`/products/${String(item.listing_id)}`} className="hover:text-primary line-clamp-1">
                      {String(item.title ?? "—")}
                    </a>
                    {item.note && <p className="text-muted-foreground text-xs mt-0.5">{String(item.note)}</p>}
                  </td>
                  <td className="px-4 py-3 capitalize">{String(item.platform ?? "—")}</td>
                  <td className="px-4 py-3 font-mono">{item.price_idr != null ? Number(item.price_idr).toLocaleString("id-ID") : "—"}</td>
                  <td className={`px-4 py-3 font-semibold ${Number(item.margin_pct) >= 30 ? "text-green-400" : Number(item.margin_pct) >= 15 ? "text-yellow-400" : "text-red-400"}`}>
                    {item.margin_pct != null ? `${Number(item.margin_pct).toFixed(1)}%` : "—"}
                  </td>
                  <td className="px-4 py-3">{item.opportunity_score != null ? Number(item.opportunity_score).toFixed(1) : "—"}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {item.alert_on_price_drop ? "💰 Price" : ""}{" "}
                    {item.alert_on_spike ? "📈 Spike" : ""}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      className="text-destructive hover:text-red-400 text-xs"
                      onClick={() => removeMutation.mutate(String(item.id))}
                      disabled={removeMutation.isPending}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
