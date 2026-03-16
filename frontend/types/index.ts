export type Platform = "tokopedia" | "shopee" | "lazada" | "tiktok_shop";

export interface ProductListing {
  id: string;
  product_id?: string;
  platform: Platform;
  platform_product_id?: string;
  title: string;
  url?: string;
  image_url?: string;
  price_idr: number;
  original_price_idr?: number;
  sold_count: number;
  sold_30d: number;
  review_count: number;
  rating?: number;
  seller_name?: string;
  seller_id?: string;
  seller_badge?: string;
  seller_city?: string;
  stock?: number;
  is_active: boolean;
  scraped_at?: string;
  created_at?: string;
  // Joined scores
  margin_pct?: number;
  opportunity_score?: number;
  trend_score?: number;
  sellability_score?: number;
  competition_score?: number;
  gate_passed?: boolean;
}

export interface Supplier {
  id: string;
  product_id?: string;
  source: "aliexpress" | "1688" | "local";
  source_product_id?: string;
  title?: string;
  url?: string;
  image_url?: string;
  price_usd?: number;
  price_idr?: number;
  shipping_cost_idr: number;
  shipping_days_estimate?: number;
  moq: number;
  seller_name?: string;
  rating?: number;
}

export interface PriceHistoryPoint {
  price_idr: number;
  sold_count?: number;
  recorded_at: string;
}

export interface MarginResult {
  sell_price_idr: number;
  supplier_price_idr: number;
  shipping_cost_idr: number;
  platform_fee_idr: number;
  gross_profit_idr: number;
  net_profit_idr: number;
  margin_pct: number;
  gross_margin_pct: number;
  supplier_price_ratio: number;
}

export interface NicheMapItem {
  niche: string;
  slug: string;
  market_size_idr?: number;
  avg_margin?: number;
  seller_count: number;
  avg_trend_score?: number;
  listing_count: number;
}

export interface WatchlistItem {
  id: string;
  listing_id: string;
  note?: string;
  alert_on_price_drop: boolean;
  alert_on_spike: boolean;
  created_at: string;
  // Joined fields
  title?: string;
  platform?: Platform;
  price_idr?: number;
  image_url?: string;
  url?: string;
  opportunity_score?: number;
  margin_pct?: number;
  trend_score?: number;
}
