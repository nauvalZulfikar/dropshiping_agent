"use client";

import { useDashboard } from "@/lib/api";
import { formatIDR } from "@/lib/utils";
import { BarChart } from "@/components/charts/bar-chart";
import { LineChart } from "@/components/charts/line-chart";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useState } from "react";

interface ProductRow {
  sku: string;
  name: string;
  niche: string;
  stock: number;
  price: number;
  cogs: number;
  margin_pct: number;
  sold_30d: number;
  revenue_30d: number;
}

interface TopProduct {
  name: string;
  revenue: number;
}

const NICHES = ["Semua", "skincare", "aksesori hp", "peralatan dapur", "fashion wanita", "suplemen"];

export default function ProductsPage() {
  const [niche, setNiche] = useState("Semua");
  const nicheParam = niche === "Semua" ? "" : `&niche=${encodeURIComponent(niche)}`;
  const { data: products } = useDashboard<ProductRow[]>(`/products?active_only=true${nicheParam}`);
  const { data: topRev } = useDashboard<TopProduct[]>("/products/top-revenue?days=30&limit=10");

  function rowClass(p: ProductRow) {
    if (p.stock <= 5) return "bg-red-950/40";
    if (p.margin_pct < 20) return "bg-yellow-950/40";
    if (p.sold_30d > 50) return "bg-green-950/30";
    return "";
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Products & Inventory</h1>

      <div className="flex gap-4">
        <Select value={niche} onValueChange={(v) => setNiche(v ?? "Semua")}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Niche" />
          </SelectTrigger>
          <SelectContent>
            {NICHES.map((n) => (
              <SelectItem key={n} value={n}>{n}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {products && products.length > 0 && (
        <div className="rounded-lg border border-zinc-800 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800">
                <TableHead>SKU</TableHead>
                <TableHead>Nama</TableHead>
                <TableHead>Niche</TableHead>
                <TableHead>Stok</TableHead>
                <TableHead>Harga</TableHead>
                <TableHead>COGS</TableHead>
                <TableHead>Margin</TableHead>
                <TableHead>Terjual 30d</TableHead>
                <TableHead>Revenue 30d</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.map((p) => (
                <TableRow key={p.sku} className={`border-zinc-800 ${rowClass(p)}`}>
                  <TableCell className="font-mono text-xs">{p.sku}</TableCell>
                  <TableCell className="max-w-40 truncate">{p.name}</TableCell>
                  <TableCell>{p.niche}</TableCell>
                  <TableCell>{p.stock}</TableCell>
                  <TableCell>{formatIDR(p.price)}</TableCell>
                  <TableCell>{formatIDR(p.cogs)}</TableCell>
                  <TableCell>{Number(p.margin_pct).toFixed(1)}%</TableCell>
                  <TableCell>{p.sold_30d}</TableCell>
                  <TableCell>{formatIDR(p.revenue_30d)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {topRev && topRev.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">Top 10 Produk by Revenue (30 hari)</h2>
          <BarChart
            data={topRev}
            xKey="name"
            bars={[{ key: "revenue", color: "#3b82f6" }]}
            layout="vertical"
            height={400}
          />
        </div>
      )}

      <PriceHistory products={products ?? []} />
    </div>
  );
}

interface PriceHistoryRow {
  date: string;
  price: number;
}

function PriceHistory({ products }: { products: ProductRow[] }) {
  const [selectedSku, setSelectedSku] = useState<string>("");
  const selected = products.find((p) => p.sku === selectedSku);
  const productId = selected ? (selected as ProductRow & { id?: number }).id : undefined;

  const { data: history } = useDashboard<PriceHistoryRow[]>(
    productId ? `/products/price-history/${productId}?days=14` : ""
  );

  if (products.length === 0) return null;

  return (
    <div>
      <h2 className="text-lg font-semibold mb-3">Price History</h2>
      <div className="flex gap-4 mb-4">
        <Select value={selectedSku} onValueChange={(v) => setSelectedSku(v ?? "")}>
          <SelectTrigger className="w-64">
            <SelectValue placeholder="Pilih produk..." />
          </SelectTrigger>
          <SelectContent>
            {products.map((p) => (
              <SelectItem key={p.sku} value={p.sku}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {selectedSku && history && history.length > 0 && (
        <LineChart
          data={history}
          xKey="date"
          lines={[{ key: "price", color: "#f59e0b" }]}
          height={250}
        />
      )}
      {selectedSku && history && history.length === 0 && (
        <p className="text-sm text-zinc-500">Belum ada data price history untuk produk ini.</p>
      )}
    </div>
  );
}
