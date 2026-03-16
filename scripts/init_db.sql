-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Product categories taxonomy
CREATE TABLE categories (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  parent_id UUID REFERENCES categories(id),
  level INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Core products table (deduped across platforms)
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  canonical_name TEXT NOT NULL,
  canonical_image_url TEXT,
  image_embedding vector(512),       -- CLIP embedding for supplier matching
  category_id UUID REFERENCES categories(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Platform-specific product listings
CREATE TABLE product_listings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (platform IN ('tokopedia','shopee','lazada','tiktok_shop')),
  platform_product_id TEXT,
  title TEXT NOT NULL,
  url TEXT,
  image_url TEXT,
  price_idr BIGINT NOT NULL,
  original_price_idr BIGINT,
  sold_count INT DEFAULT 0,
  sold_30d INT DEFAULT 0,
  review_count INT DEFAULT 0,
  rating DECIMAL(3,2),
  seller_name TEXT,
  seller_id TEXT,
  seller_badge TEXT,                 -- official, star_seller, etc
  seller_city TEXT,
  stock INT,
  is_active BOOLEAN DEFAULT TRUE,
  scraped_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Time-series: price history
CREATE TABLE price_history (
  listing_id UUID NOT NULL REFERENCES product_listings(id) ON DELETE CASCADE,
  price_idr BIGINT NOT NULL,
  sold_count INT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Suppliers from AliExpress / 1688
CREATE TABLE suppliers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id UUID REFERENCES products(id) ON DELETE CASCADE,
  source TEXT NOT NULL CHECK (source IN ('aliexpress','1688','local')),
  source_product_id TEXT,
  title TEXT,
  url TEXT,
  image_url TEXT,
  price_usd DECIMAL(12,2),
  price_idr BIGINT,
  shipping_cost_idr BIGINT DEFAULT 0,
  shipping_days_estimate INT,
  moq INT DEFAULT 1,
  seller_name TEXT,
  rating DECIMAL(3,2),
  scraped_at TIMESTAMPTZ DEFAULT NOW()
);

-- Computed scores per product listing
CREATE TABLE product_scores (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  listing_id UUID UNIQUE REFERENCES product_listings(id) ON DELETE CASCADE,
  product_id UUID REFERENCES products(id),
  -- Margin fields
  best_supplier_id UUID REFERENCES suppliers(id),
  sell_price_idr BIGINT,
  supplier_price_idr BIGINT,
  platform_fee_idr BIGINT,
  shipping_est_idr BIGINT,
  gross_profit_idr BIGINT,
  margin_pct DECIMAL(5,2),           -- (gross_profit / sell_price) * 100
  -- Scores (0-100)
  margin_score DECIMAL(5,2),
  sellability_score DECIMAL(5,2),
  trend_score DECIMAL(5,2),
  competition_score DECIMAL(5,2),
  opportunity_score DECIMAL(5,2),    -- final composite score
  -- Additional scores
  supplier_risk_score DECIMAL(5,2),
  quality_score DECIMAL(5,2),
  listing_quality_score DECIMAL(5,2),
  timing_score DECIMAL(5,2),
  market_health_score DECIMAL(5,2),
  -- Gate filter
  gate_passed BOOLEAN DEFAULT FALSE,
  gates_failed TEXT[],
  -- Metadata
  score_version TEXT DEFAULT 'v1',
  computed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trend data from Google Trends
CREATE TABLE trend_signals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  keyword TEXT NOT NULL,
  platform TEXT DEFAULT 'google',
  trend_value INT,                   -- 0-100 from Google Trends
  geo TEXT DEFAULT 'ID',
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

-- User watchlist
CREATE TABLE watchlists (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL,             -- Supabase auth user id
  listing_id UUID REFERENCES product_listings(id) ON DELETE CASCADE,
  note TEXT,
  alert_on_price_drop BOOLEAN DEFAULT TRUE,
  alert_on_spike BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, listing_id)
);

-- Competition analysis per product
CREATE TABLE competition_analysis (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  product_id UUID REFERENCES products(id),
  platform TEXT NOT NULL,
  seller_count INT,
  price_min_idr BIGINT,
  price_max_idr BIGINT,
  price_avg_idr BIGINT,
  price_median_idr BIGINT,
  top_seller_name TEXT,
  top_seller_sold_count INT,
  top_seller_market_share_pct DECIMAL(5,2),
  price_spread_idr BIGINT,
  premium_seller_ratio DECIMAL(5,2),
  avg_competitor_rating DECIMAL(3,2),
  new_seller_entry_30d INT,
  ad_density_pct DECIMAL(5,2),
  analyzed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scraper job log
CREATE TABLE scraper_jobs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source TEXT NOT NULL,
  job_type TEXT NOT NULL,            -- full_scan, incremental, single_product
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending','running','success','failed','blocked')),
  items_scraped INT DEFAULT 0,
  items_failed INT DEFAULT 0,
  error_message TEXT,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraints required for upsert logic
CREATE UNIQUE INDEX idx_listings_upsert ON product_listings(product_id, platform, platform_product_id)
    WHERE platform_product_id IS NOT NULL;
CREATE UNIQUE INDEX idx_products_name ON products(canonical_name);

-- Enable pg_trgm for fuzzy title deduplication
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Indexes for performance
CREATE INDEX idx_listings_platform ON product_listings(platform);
CREATE INDEX idx_listings_price ON product_listings(price_idr);
CREATE INDEX idx_listings_sold ON product_listings(sold_30d DESC);
CREATE INDEX idx_scores_opportunity ON product_scores(opportunity_score DESC);
CREATE INDEX idx_scores_margin ON product_scores(margin_pct DESC);
CREATE INDEX idx_products_embedding ON products USING ivfflat (image_embedding vector_cosine_ops);
CREATE INDEX idx_products_trgm ON products USING gin (canonical_name gin_trgm_ops);
CREATE INDEX idx_price_history_listing ON price_history(listing_id, recorded_at DESC);
CREATE INDEX idx_trend_signals_keyword ON trend_signals(keyword, recorded_at DESC);
