# AGENTS.md — Dropship Research Platform
## Indonesian Online Market Intelligence System

> **AGENTIC AI EXECUTION GUIDE**
> This document is the single source of truth for building this system autonomously.
> Read this file **completely** before writing a single line of code.
> Execute phases **in order**. Do not skip phases. Validate each phase before proceeding.

---

## 0. PRIME DIRECTIVES

1. **Complete every phase fully** before moving to the next.
2. **Never use mock/placeholder data** unless explicitly marked `[MOCK-OK]`. Always wire real logic.
3. **Always validate** at the end of each phase by running the checklist provided.
4. **Error = stop and fix**. Do not proceed with broken code.
5. **Follow the exact tech stack** specified. Do not substitute libraries without reason.
6. **All secrets go in `.env`**. Never hardcode credentials.
7. **Write modular code** — each service/module must be independently testable.
8. **Indonesian marketplace context**: all prices in IDR, all timestamps in WIB (UTC+7).

---

## 1. PROJECT OVERVIEW

### What We're Building
A full-stack product research platform for Indonesian dropshipping. The platform automatically scrapes products from Tokopedia, Shopee, AliExpress/1688, and TikTok Shop — then scores them by **margin** and **sellability** so the user instantly knows which products to sell.

### Core Value Proposition
> "Input nothing. Get a ranked list of the most profitable products to sell today in Indonesia."

### Key Outputs for the User
- Products ranked by **Opportunity Score** (composite of margin + sell speed + trend + competition)
- Real-time **margin calculation** per product (sell price − supplier price − platform fee − shipping)
- **Trend signal** from Google Trends + TikTok
- **Competitor analysis** per niche
- Automated **daily digest** via Telegram

---

## 2. TECH STACK (LOCKED — DO NOT DEVIATE)

```
Frontend:       Next.js 14 (App Router) + TypeScript + TailwindCSS + Recharts + shadcn/ui
Backend:        FastAPI (Python 3.11) + Pydantic v2
Database:       Supabase (PostgreSQL 15) + TimescaleDB extension
Cache / Queue:  Redis 7 + Celery 5 + Celery Beat
Scraping:       Playwright (async) + playwright-stealth + rotating proxies
Auth:           Supabase Auth (email/password + magic link)
AI / ML:        scikit-learn + Facebook Prophet + sentence-transformers (CLIP)
Vector DB:      pgvector (via Supabase)
Containerize:   Docker + Docker Compose
Monitoring:     Flower (Celery) + basic health endpoint
Notifications:  python-telegram-bot
```

---

## 3. REPOSITORY STRUCTURE

Create this exact folder structure before writing any code:

```
dropship-research/
├── AGENTS.md                        # This file
├── .env.example                     # All required env vars (no values)
├── .env                             # Actual values (gitignored)
├── .gitignore
├── docker-compose.yml               # Orchestrates all services
├── README.md
│
├── backend/                         # FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                      # FastAPI app entry point
│   ├── config.py                    # Settings from env vars
│   ├── database.py                  # Supabase/SQLAlchemy connection
│   │
│   ├── api/                         # Route handlers
│   │   ├── __init__.py
│   │   ├── products.py              # Product CRUD + search endpoints
│   │   ├── scraper.py               # Trigger scraper jobs
│   │   ├── analytics.py             # Margin, scores, trends
│   │   ├── watchlist.py             # User watchlist
│   │   └── health.py                # Health check
│   │
│   ├── scrapers/                    # Playwright scrapers per source
│   │   ├── __init__.py
│   │   ├── base_scraper.py          # Abstract base class
│   │   ├── tokopedia.py
│   │   ├── shopee.py
│   │   ├── lazada.py
│   │   ├── aliexpress.py
│   │   ├── source_1688.py
│   │   ├── tiktok_shop.py
│   │   └── proxy_manager.py         # Proxy rotation logic
│   │
│   ├── tasks/                       # Celery tasks
│   │   ├── __init__.py
│   │   ├── celery_app.py            # Celery app config
│   │   ├── scrape_tasks.py          # Scheduled scraping tasks
│   │   ├── score_tasks.py           # Scoring computation tasks
│   │   └── alert_tasks.py           # Telegram notification tasks
│   │
│   ├── engines/                     # Business logic
│   │   ├── __init__.py
│   │   ├── margin_calculator.py     # Margin computation per platform
│   │   ├── sellability_scorer.py    # Sellability score logic
│   │   ├── opportunity_scorer.py    # Composite opportunity score
│   │   ├── competition_analyzer.py  # Competitor analysis
│   │   ├── trend_engine.py          # Google Trends + pytrends
│   │   ├── supplier_matcher.py      # CLIP-based image matching
│   │   └── deduplicator.py          # Cross-platform dedup
│   │
│   ├── models/                      # Pydantic + DB models
│   │   ├── __init__.py
│   │   ├── product.py
│   │   ├── supplier.py
│   │   ├── score.py
│   │   └── user.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── currency.py              # IDR formatting helpers
│       ├── datetime_utils.py        # WIB timezone helpers
│       └── logger.py
│
├── frontend/                        # Next.js 14 application
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   │
│   ├── app/                         # App Router pages
│   │   ├── layout.tsx
│   │   ├── page.tsx                 # Dashboard / product feed
│   │   ├── products/
│   │   │   ├── page.tsx             # Product list with filters
│   │   │   └── [id]/page.tsx        # Product detail + price history
│   │   ├── niches/
│   │   │   └── page.tsx             # Niche explorer / heatmap
│   │   ├── watchlist/
│   │   │   └── page.tsx             # User watchlist
│   │   ├── suppliers/
│   │   │   └── page.tsx             # Supplier comparison
│   │   └── api/                     # Next.js API routes (thin proxy to FastAPI)
│   │       └── [...path]/route.ts
│   │
│   ├── components/
│   │   ├── ui/                      # shadcn components
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── TopBar.tsx
│   │   │   └── AlertCenter.tsx
│   │   ├── products/
│   │   │   ├── ProductCard.tsx
│   │   │   ├── ProductTable.tsx
│   │   │   ├── ProductFilters.tsx
│   │   │   └── OpportunityBadge.tsx
│   │   ├── charts/
│   │   │   ├── MarginHeatmap.tsx
│   │   │   ├── TrendChart.tsx
│   │   │   ├── PriceHistoryChart.tsx
│   │   │   └── NicheBubbleMap.tsx
│   │   └── margin/
│   │       └── MarginCalculatorPanel.tsx
│   │
│   ├── lib/
│   │   ├── api-client.ts            # Axios client to FastAPI
│   │   ├── supabase.ts              # Supabase browser client
│   │   └── utils.ts
│   │
│   └── types/
│       └── index.ts                 # Shared TypeScript types
│
├── ml/                              # ML models (run separately or in backend)
│   ├── trend_predictor/
│   │   ├── train.py
│   │   └── predict.py
│   └── sentiment/
│       └── review_analyzer.py
│
└── scripts/
    ├── init_db.sql                  # Initial DB schema + TimescaleDB setup
    ├── seed_categories.py           # Seed product category taxonomy
    └── test_scrapers.py             # Manual scraper smoke tests
```

---

## 4. ENVIRONMENT VARIABLES

Create `.env.example` with ALL these keys (no values). Then create `.env` with real values.

```bash
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres

# Redis
REDIS_URL=redis://redis:6379/0

# FastAPI
SECRET_KEY=
API_PORT=8000
ENVIRONMENT=development

# Proxies (comma-separated list of proxy:port:user:pass)
PROXY_LIST=

# Telegram Bot
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Next.js
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

# Optional: Bright Data / Oxylabs
BRIGHTDATA_USERNAME=
BRIGHTDATA_PASSWORD=
BRIGHTDATA_HOST=
```

---

## 5. DATABASE SCHEMA

Run `scripts/init_db.sql` as the first migration. Create these tables exactly:

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS timescaledb;

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

-- Time-series: price history (hypertable)
CREATE TABLE price_history (
  listing_id UUID NOT NULL REFERENCES product_listings(id) ON DELETE CASCADE,
  price_idr BIGINT NOT NULL,
  sold_count INT,
  recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SELECT create_hypertable('price_history', 'recorded_at');

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
SELECT create_hypertable('trend_signals', 'recorded_at');

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

-- Indexes for performance
CREATE INDEX idx_listings_platform ON product_listings(platform);
CREATE INDEX idx_listings_price ON product_listings(price_idr);
CREATE INDEX idx_listings_sold ON product_listings(sold_30d DESC);
CREATE INDEX idx_scores_opportunity ON product_scores(opportunity_score DESC);
CREATE INDEX idx_scores_margin ON product_scores(margin_pct DESC);
CREATE INDEX idx_products_embedding ON products USING ivfflat (image_embedding vector_cosine_ops);
```

---

## 6. DOCKER COMPOSE

`docker-compose.yml` must define these services:

```yaml
version: '3.9'
services:

  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [redis]
    volumes: ["./backend:/app"]
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    env_file: .env
    depends_on: [backend]
    volumes: ["./frontend:/app", "/app/node_modules"]
    command: npm run dev

  celery_worker:
    build: ./backend
    env_file: .env
    depends_on: [redis, backend]
    command: celery -A tasks.celery_app worker --loglevel=info --concurrency=4

  celery_beat:
    build: ./backend
    env_file: .env
    depends_on: [redis]
    command: celery -A tasks.celery_app beat --loglevel=info

  flower:
    build: ./backend
    ports: ["5555:5555"]
    env_file: .env
    depends_on: [redis]
    command: celery -A tasks.celery_app flower --port=5555

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: ["redis_data:/data"]

volumes:
  redis_data:
```

---

## 7. PHASE-BY-PHASE BUILD PLAN

---

### PHASE 1 — Foundation & Database
**Goal**: Project skeleton + DB running + health check passing

#### Steps:
1. Create full folder structure as defined in Section 3.
2. Create `.env.example` and `.env` files.
3. Write `docker-compose.yml` exactly as specified in Section 6.
4. Write `scripts/init_db.sql` with full schema from Section 5.
5. Write `backend/database.py`:
   - SQLAlchemy async engine connecting to `DATABASE_URL`
   - `get_db()` dependency function for FastAPI
   - On startup, test connection and log success
6. Write `backend/config.py` using `pydantic_settings.BaseSettings`, loading all env vars.
7. Write `backend/main.py`:
   - FastAPI app with CORS enabled for `localhost:3000`
   - Mount routers: `/api/products`, `/api/scraper`, `/api/analytics`, `/api/health`
   - Startup event: test DB connection
8. Write `backend/api/health.py`:
   - `GET /api/health` → returns `{"status": "ok", "db": "connected", "redis": "connected"}`
9. Write `backend/requirements.txt` with all needed packages.
10. Write `backend/Dockerfile`.
11. Initialize Next.js 14 frontend in `frontend/` with TypeScript + Tailwind + shadcn/ui.
12. Write `frontend/lib/api-client.ts` — Axios instance pointing to `NEXT_PUBLIC_API_URL`.
13. Run `docker-compose up` and confirm all services start without errors.

#### ✅ Phase 1 Checklist:
- [ ] `docker-compose up` starts all 6 services without error
- [ ] `GET http://localhost:8000/api/health` returns `{"status":"ok"}`
- [ ] `http://localhost:3000` loads Next.js default page
- [ ] Database schema applied (run init_db.sql)
- [ ] Redis connected (visible in health endpoint)

---

### PHASE 2 — Scrapers
**Goal**: Working scrapers for Tokopedia, Shopee, AliExpress that save real data to DB

#### Steps:

**2.1 Base Scraper**
- Write `backend/scrapers/base_scraper.py`:
  - Abstract base class `BaseScraper` with methods: `scrape_search(keyword, max_pages)`, `scrape_product(url)`, `_get_page(url)`, `_random_delay()`
  - Uses Playwright async API
  - Integrates `playwright-stealth` to avoid bot detection
  - `_get_page()` uses `proxy_manager.get_proxy()` for each request

**2.2 Proxy Manager**
- Write `backend/scrapers/proxy_manager.py`:
  - Loads proxy list from `PROXY_LIST` env var (comma-separated `host:port:user:pass`)
  - `get_proxy()` → returns next proxy in round-robin rotation
  - `mark_failed(proxy)` → moves to failed list for 10 minutes
  - If no proxies configured, returns `None` (direct connection)

**2.3 Tokopedia Scraper**
- Write `backend/scrapers/tokopedia.py` — class `TokopediaScraper(BaseScraper)`:
  - `scrape_search(keyword, max_pages=3)`:
    - URL: `https://www.tokopedia.com/search?st=product&q={keyword}&navsource=home&srp_component_id=02.01.00.00`
    - Extract per product card: `title`, `price`, `sold_count`, `shop_name`, `shop_location`, `rating`, `review_count`, `image_url`, `product_url`, `badge`
    - Handle pagination
    - Returns `List[dict]`
  - `scrape_product(url)`:
    - Extract full product detail: all above fields + `stock`, `description`, `category_breadcrumb`, `sold_total`
  - Save results to `product_listings` table with `platform='tokopedia'`

**2.4 Shopee Scraper**
- Write `backend/scrapers/shopee.py` — class `ShopeeScraper(BaseScraper)`:
  - `scrape_search(keyword, max_pages=3)`:
    - URL: `https://shopee.co.id/search?keyword={keyword}`
    - Extract: `title`, `price`, `price_before_discount`, `sold`, `rating`, `review_count`, `shop_name`, `shop_location`, `image`, `url`, `liked_count`
    - Note: Shopee is SPA — wait for network idle + `page.wait_for_selector`
  - Save to `product_listings` with `platform='shopee'`

**2.5 AliExpress Scraper**
- Write `backend/scrapers/aliexpress.py` — class `AliExpressScraper(BaseScraper)`:
  - `scrape_search(keyword, max_results=20)`:
    - URL: `https://www.aliexpress.com/wholesale?SearchText={keyword}`
    - Extract: `title`, `price_usd`, `shipping_cost_usd`, `rating`, `review_count`, `seller_name`, `image_url`, `product_url`, `moq`
    - Convert USD to IDR using rate from `utils/currency.py` (fetch from Bank Indonesia API or fallback hardcoded rate)
  - Save to `suppliers` table with `source='aliexpress'`

**2.6 Google Trends Integration**
- Write `backend/engines/trend_engine.py`:
  - Function `get_trend_score(keyword: str) -> int`:
    - Use `pytrends` library
    - `pytrends.build_payload([keyword], geo='ID', timeframe='today 3-m')`
    - Return latest interest value (0-100)
    - Cache result in Redis for 6 hours
  - Function `get_related_queries(keyword: str) -> List[str]`:
    - Returns rising related queries for keyword in Indonesia

**2.7 Celery Scraping Tasks**
- Write `backend/tasks/celery_app.py` — configure Celery with Redis broker.
- Write `backend/tasks/scrape_tasks.py`:
  - `@celery_app.task scrape_tokopedia(keyword, max_pages=3)` — calls scraper, saves to DB, logs to `scraper_jobs`
  - `@celery_app.task scrape_shopee(keyword, max_pages=3)` — same
  - `@celery_app.task scrape_aliexpress(keyword, max_results=20)` — same
  - `@celery_app.task full_scan(keywords: List[str])` — calls all 3 scrapers per keyword in parallel using `group()`
- Write `backend/tasks/celery_app.py` Celery Beat schedule:
  ```python
  beat_schedule = {
    'scrape-trending-hourly': {
        'task': 'tasks.scrape_tasks.full_scan',
        'schedule': crontab(minute=0),  # every hour
        'args': [["tas wanita", "sepatu pria", "skincare", "elektronik murah", "aksesoris hp"]]
    },
  }
  ```

**2.8 Scraper API Endpoints**
- Write `backend/api/scraper.py`:
  - `POST /api/scraper/trigger` — body: `{source, keyword, max_pages}` — enqueues Celery task, returns `{task_id}`
  - `GET /api/scraper/status/{task_id}` — returns Celery task status
  - `GET /api/scraper/jobs` — returns last 20 scraper job logs from DB

#### ✅ Phase 2 Checklist:
- [ ] `POST /api/scraper/trigger` with `{"source":"tokopedia","keyword":"tas wanita"}` returns task_id
- [ ] After task completes, `product_listings` table has rows with `platform='tokopedia'`
- [ ] Shopee scraper saves rows with `platform='shopee'`
- [ ] AliExpress scraper saves rows to `suppliers` table
- [ ] `get_trend_score("tas wanita")` returns a number 0-100
- [ ] Celery Flower at `localhost:5555` shows tasks running

---

### PHASE 3 — Scoring Engines
**Goal**: Every product in DB gets a computed Opportunity Score

#### Steps:

**3.1 Margin Calculator**
- Write `backend/engines/margin_calculator.py`:
  - Platform fee rates (hardcoded constants, can be overridden):
    ```python
    PLATFORM_FEES = {
        'tokopedia': 0.025,   # 2.5% admin fee
        'shopee':    0.020,   # 2.0% admin fee
        'lazada':    0.025,
        'tiktok_shop': 0.030,
    }
    PAYMENT_FEE = 0.015  # 1.5% payment gateway
    ```
  - Function `calculate_margin(listing: ProductListing, supplier: Supplier) -> MarginResult`:
    - `gross_profit = listing.price_idr - supplier.price_idr - supplier.shipping_cost_idr`
    - `platform_fee = listing.price_idr * (PLATFORM_FEES[platform] + PAYMENT_FEE)`
    - `net_profit = gross_profit - platform_fee`
    - `margin_pct = (net_profit / listing.price_idr) * 100`
    - Returns `MarginResult` Pydantic model with all fields
  - Function `find_best_supplier(product_id: UUID) -> Optional[Supplier]`:
    - Query `suppliers` table for this product, return cheapest valid option

**3.2 Sellability Scorer**
- Write `backend/engines/sellability_scorer.py`:
  - Function `compute_sellability(listing: ProductListing) -> float`:
    - Normalize `sold_30d`: log scale, max = 10,000 → score 0-40 pts
    - `review_count`: log scale, max = 5,000 → score 0-20 pts
    - `rating`: 0-5 → score 0-20 pts  
    - `sold_growth_rate`: % change sold_7d vs prev_7d → 0-20 pts
    - Total: 0-100
  - Function `compute_competition(product_id, platform) -> float`:
    - Count active sellers for same product on platform
    - < 5 sellers → 90 pts (low comp), 5-20 → 60 pts, 20-100 → 30 pts, > 100 → 10 pts

**3.3 Opportunity Scorer**
- Write `backend/engines/opportunity_scorer.py`:
  - Function `compute_opportunity_score(listing_id: UUID) -> float`:
    ```python
    weights = {
        'margin_score': 0.35,
        'sellability_score': 0.30,
        'trend_score': 0.20,
        'competition_score': 0.15,
    }
    ```
  - Fetches all sub-scores, computes weighted average
  - Saves result to `product_scores` table
  - Returns final score 0-100

**3.4 Batch Scoring Task**
- Write `backend/tasks/score_tasks.py`:
  - `@celery_app.task score_all_products()` — iterates all unscored listings, calls `compute_opportunity_score()`
  - Add to Celery Beat: run every 2 hours
  - `@celery_app.task score_single_listing(listing_id)` — on-demand scoring for new scrapes

**3.5 Supplier Matcher (Image-Based)**
- Write `backend/engines/supplier_matcher.py`:
  - Use `sentence-transformers` with `clip-ViT-B-32` model
  - Function `embed_image(image_url: str) -> np.ndarray` — download image, compute CLIP embedding
  - Function `match_supplier_to_product(product_id: UUID)`:
    - Get product's canonical image embedding from `products.image_embedding`
    - Search `suppliers` table images using pgvector cosine similarity
    - Return top 3 most similar suppliers
  - On new product saved, enqueue embedding task

#### ✅ Phase 3 Checklist:
- [ ] `product_scores` table has rows for all listings
- [ ] `opportunity_score` values range between 0-100 (not all zeros, not all 100)
- [ ] `margin_pct` correctly reflects sell price minus supplier minus fees
- [ ] `score_all_products` Celery task runs without error
- [ ] Products with high sold_30d have higher sellability_score than products with low sold_30d

---

### PHASE 4 — Backend API Layer
**Goal**: Full REST API serving all data the frontend needs

#### Steps:

**4.1 Products API**
- Write `backend/api/products.py`:
  - `GET /api/products` — paginated product list with filters:
    - Query params: `platform`, `category_slug`, `min_margin`, `max_price`, `min_score`, `sort_by` (opportunity_score|margin_pct|sold_30d|trend_score), `page`, `limit`
    - JOIN `product_listings` + `product_scores` + `suppliers`
    - Return full product data with scores
  - `GET /api/products/{listing_id}` — full product detail:
    - Include price history (last 30 days)
    - Include all suppliers with margin calculation
    - Include competition analysis
    - Include trend chart data
  - `GET /api/products/top` — top 20 by opportunity score today
  - `GET /api/products/trending` — products with highest trend_score spike in last 24h

**4.2 Analytics API**
- Write `backend/api/analytics.py`:
  - `GET /api/analytics/margin-heatmap` — returns `{category, platform, avg_margin}[]` for heatmap
  - `GET /api/analytics/niche-map` — returns `{niche, market_size_idr, avg_margin, seller_count}[]`
  - `GET /api/analytics/price-history/{listing_id}` — 30-day price + sold count time series
  - `GET /api/analytics/trends` — top trending keywords in Indonesia today (from `trend_signals`)
  - `GET /api/analytics/platform-comparison/{product_id}` — same product across platforms side-by-side

**4.3 Watchlist API**
- Write `backend/api/watchlist.py` (requires Supabase auth middleware):
  - `GET /api/watchlist` — user's watchlist with current scores
  - `POST /api/watchlist` — add product to watchlist
  - `DELETE /api/watchlist/{id}` — remove from watchlist
  - `PATCH /api/watchlist/{id}` — update alert preferences

**4.4 API Models (Pydantic)**
- Write all response models in `backend/models/`:
  - `ProductListingResponse` — full listing with scores
  - `MarginResult` — detailed margin breakdown
  - `CompetitionAnalysis` — competitor data
  - `PriceHistoryPoint` — time series point
  - `NicheMapItem` — for bubble chart

#### ✅ Phase 4 Checklist:
- [ ] `GET /api/products?min_margin=20&sort_by=opportunity_score` returns sorted results
- [ ] `GET /api/products/{id}` returns price history array
- [ ] `GET /api/analytics/margin-heatmap` returns category × platform matrix
- [ ] All endpoints respond in < 500ms (use Redis caching for heavy queries)
- [ ] Pagination works correctly (page/limit params)

---

### PHASE 5 — Frontend Dashboard
**Goal**: Full working dashboard connected to real backend data

#### Steps:

**5.1 Layout & Navigation**
- Write `frontend/app/layout.tsx`:
  - Dark theme by default
  - Sidebar navigation: Dashboard, Products, Niches, Watchlist, Suppliers
  - TopBar with: search bar, notification bell (alert count), user avatar
- Write `frontend/components/layout/Sidebar.tsx` — collapsible sidebar with icons
- Write `frontend/components/layout/TopBar.tsx`

**5.2 Dashboard Page (Home)**
- Write `frontend/app/page.tsx` — main dashboard:
  - **Top Stats Row**: Total Products Tracked | Avg Margin Today | Top Opportunity Score | New Products (24h)
  - **Opportunity Feed**: Grid of top 12 `ProductCard` components sorted by opportunity_score
  - **Trending Keywords**: Horizontal scrollable chips with trend values
  - **Quick Margin Heatmap Preview**: Mini heatmap (top 5 categories × 3 platforms)
  - All data fetched from API on load, with `loading` skeleton states

**5.3 Product Card Component**
- Write `frontend/components/products/ProductCard.tsx`:
  - Product image (thumbnail)
  - Title (truncated to 2 lines)
  - Platform badge (Tokopedia/Shopee color-coded)
  - Sell price (IDR formatted)
  - Margin % — color coded: green > 30%, yellow 15-30%, red < 15%
  - Opportunity score — circular gauge (0-100)
  - Sold 30d count
  - "Add to Watchlist" button
  - Click → navigate to product detail

**5.4 Products Page**
- Write `frontend/app/products/page.tsx`:
  - Full-width data table using `ProductTable` component
  - Left sidebar filters: Platform (multi-select), Category (tree select), Min Margin (slider), Sort By (select)
  - Columns: #, Product, Platform, Price, Supplier Price, Margin%, Sold 30d, Score, Actions
  - Pagination controls
  - Export CSV button

**5.5 Product Detail Page**
- Write `frontend/app/products/[id]/page.tsx`:
  - Large product image + title + badges
  - **Margin Breakdown Panel**: sell price → platform fee → shipping → supplier cost → net profit (visual waterfall)
  - **Price History Chart**: dual-line chart (sell price + supplier price) over 30 days using Recharts
  - **Trend Chart**: Google Trends interest value over 90 days
  - **Supplier Comparison Table**: all matched suppliers with price, shipping, MOQ, source link
  - **Competition Analysis**: seller count, price range, top 3 sellers bar chart
  - **Platform Comparison**: same product price on Tokopedia vs Shopee vs Lazada

**5.6 Margin Heatmap**
- Write `frontend/components/charts/MarginHeatmap.tsx`:
  - X-axis: platforms (Tokopedia, Shopee, Lazada, TikTok Shop)
  - Y-axis: top 15 product categories
  - Cell color: red (low margin) → yellow → green (high margin)
  - Cell value: `avg_margin%`
  - Hover tooltip: avg margin, product count, top product

**5.7 Niche Explorer Page**
- Write `frontend/app/niches/page.tsx`:
  - Bubble chart (D3.js or Recharts ScatterChart):
    - X: avg_margin_pct
    - Y: total_market_size (sum of sold × price)
    - Bubble size: number of active listings
    - Color: trend_score
  - Click bubble → drill down to products in that niche
  - Table below bubble chart with sortable niche metrics

**5.8 Watchlist Page**
- Write `frontend/app/watchlist/page.tsx`:
  - Table of watched products with current score, price, 7d price change
  - Alert toggle per product
  - Remove from watchlist action
  - "Score changed since added" delta indicator

**5.9 Alert Center Component**
- Write `frontend/components/layout/AlertCenter.tsx`:
  - Slide-in panel from right
  - Shows latest price drops, score spikes, new competitors
  - Mark as read functionality
  - Real-time via Supabase Realtime subscription

#### ✅ Phase 5 Checklist:
- [ ] Dashboard loads and shows real products from API
- [ ] Product cards display correct margin color coding
- [ ] Product detail page shows price history chart with real data points
- [ ] Margin heatmap renders with colored cells (not all same color)
- [ ] Niche bubble chart renders with multiple bubbles
- [ ] Filters on products page actually filter the results
- [ ] Loading skeletons appear while data fetches

---

### PHASE 6 — Automation & Notifications
**Goal**: System runs itself — auto-scrape, auto-score, auto-alert

#### Steps:

**6.1 Telegram Bot**
- Write `backend/tasks/alert_tasks.py`:
  - `send_telegram(message: str)` — sends to `TELEGRAM_CHAT_ID`
  - `@celery_app.task send_daily_digest()`:
    - Runs every day at 08:00 WIB
    - Queries top 5 products by opportunity_score
    - Formats message with product name, margin%, score, platform link
    - Sends to Telegram
  - `@celery_app.task send_watchlist_alerts()`:
    - Runs every hour
    - Checks if any watched products had: price drop > 5%, sold spike > 50%, new competitor
    - Sends targeted alert per user (if Telegram chat_id stored in user profile)

**6.2 Auto Price Monitoring**
- Add to `backend/tasks/scrape_tasks.py`:
  - `@celery_app.task monitor_price_changes()`:
    - Runs every 30 minutes
    - For each listing in any user's watchlist, re-scrape current price
    - If price changed > 2%, insert new row to `price_history`
    - If price dropped > 5%, enqueue `send_watchlist_alerts`

**6.3 Beat Schedule — Complete**
- In `backend/tasks/celery_app.py`, define complete beat schedule:
  ```python
  beat_schedule = {
    'full-scan-hourly': {
        'task': 'tasks.scrape_tasks.full_scan',
        'schedule': crontab(minute=0),
        'args': [["tas wanita", "sepatu pria", "skincare", "aksesoris hp", "mainan anak", "peralatan dapur", "jam tangan murah", "kaos polos"]]
    },
    'score-all-2h': {
        'task': 'tasks.score_tasks.score_all_products',
        'schedule': crontab(minute=0, hour='*/2'),
    },
    'monitor-prices-30m': {
        'task': 'tasks.scrape_tasks.monitor_price_changes',
        'schedule': crontab(minute='*/30'),
    },
    'daily-digest-8am': {
        'task': 'tasks.alert_tasks.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),  # WIB
    },
    'watchlist-alerts-hourly': {
        'task': 'tasks.alert_tasks.send_watchlist_alerts',
        'schedule': crontab(minute=15),
    },
  }
  ```

#### ✅ Phase 6 Checklist:
- [ ] Celery Beat scheduler starts without error
- [ ] `send_daily_digest` task runs and sends Telegram message (test manually)
- [ ] `price_history` table gets new rows after `monitor_price_changes` runs
- [ ] Flower dashboard shows all scheduled tasks

---

### PHASE 7 — Polish, Performance & Deployment
**Goal**: Production-ready, fast, no crashes

#### Steps:

**7.1 API Caching**
- Add Redis cache decorators to heavy API endpoints:
  - `GET /api/analytics/margin-heatmap` — cache 1 hour
  - `GET /api/products/top` — cache 15 minutes
  - `GET /api/analytics/niche-map` — cache 1 hour
  - Use `fastapi-cache2` with Redis backend

**7.2 Frontend Performance**
- Add `loading.tsx` skeleton files for all pages
- Implement React Query (`@tanstack/react-query`) for all data fetching:
  - Stale time: 5 minutes for product lists
  - Stale time: 30 seconds for scores
- Add `Suspense` boundaries around heavy chart components

**7.3 Error Handling**
- Backend: global exception handler in FastAPI returning consistent `{error, message, code}` JSON
- Scraper: wrap all Playwright operations in try/except, log to `scraper_jobs`, never let one scraper crash the worker
- Frontend: `Error Boundary` components around each dashboard section

**7.4 README.md**
- Write complete `README.md`:
  - Project description
  - Prerequisites: Docker, Node 18+, Python 3.11+
  - Setup instructions (clone → copy .env.example → fill .env → docker-compose up)
  - How to trigger manual scrape
  - How to access: Frontend, API docs, Flower

**7.5 Final Integration Test**
- Run `scripts/test_scrapers.py`:
  - Trigger Tokopedia scrape for "tas wanita"
  - Wait for task to complete
  - Verify products saved to DB
  - Verify scores computed
  - Verify products appear on dashboard

#### ✅ Phase 7 Checklist:
- [ ] `docker-compose up` from fresh clone starts everything correctly
- [ ] `http://localhost:3000` shows real products with real scores
- [ ] `http://localhost:8000/docs` shows all API endpoints documented
- [ ] `http://localhost:5555` Flower shows workers active
- [ ] No console errors in browser
- [ ] API responses under 500ms for main product list
- [ ] README has complete setup instructions

---

## 8. SCORING LOGIC REFERENCE

Scoring is the most critical business logic. Implement exactly as documented here.

---

### 8.1 Margin Score (0-100)
```
margin_pct = (net_profit / sell_price) * 100

margin_score:
  margin_pct >= 50% → 100
  margin_pct >= 40% → 90
  margin_pct >= 30% → 75
  margin_pct >= 20% → 55
  margin_pct >= 10% → 30
  margin_pct < 10%  → 10
  margin_pct <= 0%  → 0
```

**Sub-fields to compute and store:**
- `gross_margin_pct`  = (sell_price − cogs) / sell_price × 100
- `net_margin_pct`    = (sell_price − cogs − platform_fee − shipping) / sell_price × 100
- `gross_profit_idr`  = sell_price − supplier_price − shipping_cost
- `supplier_price_ratio` = sell_price / supplier_price  (target: > 2.5×)

---

### 8.2 Sellability Score (0-100)
```
sold_score     = min(log10(sold_30d + 1) / log10(10001), 1) * 40
review_score   = min(log10(review_count + 1) / log10(5001), 1) * 20
rating_score   = (rating / 5.0) * 20
growth_score   = min(max(sold_growth_pct, 0) / 100, 1) * 20

sellability_score = sold_score + review_score + rating_score + growth_score
```

**Additional demand signals to capture and store (used in UI, not in score formula):**
- `sales_velocity`       = sold_30d / 30  (units/day)
- `sales_growth_wow`     = (sold_7d − prev_sold_7d) / prev_sold_7d × 100  (% WoW)
- `wishlist_count`       = liked/saved count from platform
- `review_recency_days`  = days since most recent review posted
- `photo_review_pct`     = reviews with buyer photos / total reviews × 100
- `stock_level`          = current stock integer (scrape if available)

---

### 8.3 Trend Score (0-100)
```
google_trend_value = pytrends interest 0-100 (geo=ID)
tiktok_signal      = 0 or 1 (product found trending on TikTok today)

trend_score = (google_trend_value * 0.7) + (tiktok_signal * 30)
```

**Additional trend fields to store:**
- `trend_direction`      = 'rising' | 'stable' | 'declining'  (compare 30d vs 90d avg)
- `trend_breakout`       = boolean — did this keyword spike > 50% in last 7 days?
- `seasonal_index`       = 0.5–2.0 multiplier based on historical monthly pattern
- `days_to_harbolnas`    = integer days until next major sale event (11.11, 12.12, Lebaran, Harnas)

Seasonal event calendar (hardcode in `utils/datetime_utils.py`):
```python
SALE_EVENTS = [
  "01-01",  # New Year
  "02-14",  # Valentine
  "04-10",  # Lebaran (approximate, update yearly)
  "05-02",  # Hari Pendidikan
  "08-17",  # HUT RI
  "10-10",  # 10.10 Harbolnas
  "11-11",  # 11.11 Harbolnas
  "12-12",  # 12.12 Harbolnas
  "12-25",  # Christmas
]
```

---

### 8.4 Competition Score (0-100)
```
seller_count on platform for same product:
  < 3   → 95 (blue ocean)
  3-10  → 80
  10-30 → 60
  30-100 → 35
  100-500 → 15
  > 500  → 5  (red ocean)
```

**Additional competition fields to store in `competition_analysis` table:**
- `top_seller_market_share_pct` = top_seller_sold / total_market_sold × 100  (target: < 40%)
- `price_spread_idr`            = max_price − min_price in this product niche
- `premium_seller_ratio`        = count(star/official sellers) / total_sellers × 100
- `avg_competitor_rating`       = mean rating of top 10 sellers for this product
- `new_seller_entry_30d`        = count of sellers who listed this product in last 30 days
- `ad_density_pct`              = sponsored listings / total first-page listings × 100

---

### 8.5 Supplier Risk Score (0-100, higher = safer supplier)
```
rating_score     = (supplier_rating / 5.0) * 30
volume_score     = min(log10(supplier_orders + 1) / log10(10001), 1) * 25
shipping_score   = max(0, (21 - shipping_days) / 21) * 25   # faster = higher
moq_score        = (1 if moq == 1 else 0.7 if moq <= 5 else 0.3 if moq <= 20 else 0) * 20

supplier_risk_score = rating_score + volume_score + shipping_score + moq_score
```

**Fields to store per supplier:**
- `moq`                   = minimum order quantity
- `shipping_days_estimate` = transit days CN → ID
- `shipping_cost_ratio`   = shipping_cost / net_profit × 100  (target: < 20%)
- `product_weight_grams`  = weight in grams (affects shipping cost)
- `local_available`       = boolean — can this be sourced domestically?
- `supplier_rating`       = AliExpress/1688 seller rating 0-5
- `supplier_order_count`  = total fulfilled orders on platform

---

### 8.6 Product Quality Score (0-100)
```
rating_score         = (avg_rating / 5.0) * 35
review_volume_score  = min(log10(review_count + 1) / log10(1001), 1) * 25
recency_score        = max(0, (30 - review_recency_days) / 30) * 20   # recent = higher
negative_rate_score  = max(0, 1 - (negative_review_pct / 10)) * 20   # low neg = higher

quality_score = rating_score + review_volume_score + recency_score + negative_rate_score
```

**Fields to store:**
- `avg_rating`             = float 0–5
- `review_count`           = integer
- `negative_review_pct`    = % of 1–2 star reviews  (target: < 5%)
- `photo_review_pct`       = % of reviews with buyer photos  (target: > 30%)
- `review_recency_days`    = days since last review
- `return_complaint_rate`  = % buyers who complained/returned  (scrape if available)
- `qa_count`               = number of active Q&A on listing  (high = interested buyers)

---

### 8.7 Listing Quality Score (0-100)
```
image_score      = min(image_count / 5, 1) * 30
title_score      = (keyword_in_title_count / 3) * 25   # top 3 keywords present
desc_score       = (1 if description_length > 300 else description_length / 300) * 25
spec_score       = (1 if has_product_specs else 0) * 20

listing_quality_score = image_score + title_score + desc_score + spec_score
```

**Fields to store:**
- `image_count`              = number of product images
- `has_video`                = boolean
- `description_length`       = character count of product description
- `has_product_specs`        = boolean (size table, material, etc.)
- `keyword_relevance_score`  = how well title matches top search keywords (0–1)
- `price_position`           = 'below_median' | 'median' | 'above_median' vs competitors

---

### 8.8 Opportunity Score (Final Composite)
```
opportunity_score = (
    margin_score      * 0.35 +
    sellability_score * 0.30 +
    trend_score       * 0.20 +
    competition_score * 0.15
)
```

**Additional composite scores to compute and store (not in opportunity_score formula but displayed in UI):**

| Score | Formula | Purpose |
|-------|---------|---------|
| `market_health_score` | avg(competition_score, price_spread_normalized, review_velocity_score) | Is this niche worth entering? |
| `supplier_risk_score` | See 8.5 | Sourcing reliability |
| `product_quality_score` | See 8.6 | Product trust signal |
| `listing_quality_score` | See 8.7 | SEO + conversion potential |
| `timing_score` | avg(trend_score, seasonal_index×50, harbolnas_proximity_score) | Is NOW the right time? |

All scores stored in `product_scores` table. Add columns: `supplier_risk_score`, `quality_score`, `listing_quality_score`, `timing_score`, `market_health_score`.

---

## 9. PLATFORM FEE REFERENCE (Indonesia, 2024)

| Platform    | Admin Fee | Payment Fee | Total Deduction |
|-------------|-----------|-------------|-----------------|
| Tokopedia   | 1.8–2.5%  | 1.5%        | ~4%             |
| Shopee      | 2.0%      | 2.0%        | ~4%             |
| Lazada      | 2.5%      | 1.5%        | ~4%             |
| TikTok Shop | 3.0%      | 1.5%        | ~4.5%           |

Use conservative estimates. Always calculate with **higher fee** to protect margin estimates.

---

## 10. KNOWN SCRAPING CHALLENGES & SOLUTIONS

| Challenge | Platform | Solution |
|-----------|----------|----------|
| Bot detection | Shopee | playwright-stealth + random delays 2-5s + viewport randomization |
| Rate limiting | Tokopedia | Max 1 req/3s per proxy, rotate proxy every 10 requests |
| SPA rendering | Shopee, TikTok | `page.wait_for_load_state('networkidle')` + specific selector wait |
| CAPTCHA | AliExpress | Detect CAPTCHA page, mark proxy as blocked, switch proxy, retry |
| Price formatting | All | Strip Rp, `.`, `,` → convert to integer IDR |
| Sold count format | Tokopedia | "1,2rb terjual" → parse as 1200 |
| Sold count format | Shopee | "1.2K sold" → parse as 1200 |

---

## 11. ANTI-PATTERNS TO AVOID

- ❌ Do NOT use `time.sleep()` — use `asyncio.sleep()` in all async scrapers
- ❌ Do NOT store prices as floats — always `BIGINT` in IDR (integer rupiah)
- ❌ Do NOT fetch proxy on every request — use `proxy_manager` rotation
- ❌ Do NOT run Playwright synchronously in Celery tasks — use `asyncio.run()`
- ❌ Do NOT cache user-specific data (watchlists) in Redis
- ❌ Do NOT expose raw DB errors to frontend — always wrap in proper HTTP responses
- ❌ Do NOT use `SELECT *` in production queries — always select specific columns
- ❌ Do NOT block the FastAPI event loop with sync operations — use `run_in_executor`

---

## 12. DEFINITION OF DONE

The system is complete when ALL of the following are true:

1. ✅ `docker-compose up` starts all services cleanly from a fresh clone
2. ✅ Tokopedia scraper successfully scrapes search results and saves to DB
3. ✅ Shopee scraper successfully scrapes and saves to DB
4. ✅ AliExpress scraper finds supplier prices for products
5. ✅ Opportunity scores computed for all scraped products
6. ✅ Dashboard shows real products ranked by opportunity score
7. ✅ Margin heatmap shows categories with varying colors (real data)
8. ✅ Product detail page shows price history chart
9. ✅ Filtering products by min_margin returns correct subset
10. ✅ Watchlist saves and persists across page refresh
11. ✅ Telegram daily digest sends successfully
12. ✅ Celery Beat runs scheduled tasks automatically
13. ✅ No unhandled exceptions in any service logs
14. ✅ API docs accessible at `/docs`
15. ✅ README documents complete setup flow

---

## 13. QUICK DECISION FILTER — 5 GATES

Before displaying a product as "recommended" in the UI, it **must pass all 5 gates**. Products that fail any gate should be hidden from the main feed (but still accessible via "All Products" with filter removed).

Implement this as `engines/gate_filter.py`:

```python
def passes_all_gates(score: ProductScore, listing: ProductListing, supplier: Supplier) -> bool:
    gate1 = score.net_margin_pct >= 20                          # Gate 1: Margin
    gate2 = listing.sold_30d >= 300                             # Gate 2: Demand
    gate3 = score.trend_score >= 40 and score.trend_direction != 'declining'  # Gate 3: Trend
    gate4 = score.competition_score >= 35                       # Gate 4: Competition (≤ 100 sellers)
    gate5 = (supplier.price_idr / listing.price_idr) <= 0.40   # Gate 5: Supplier price ≤ 40% of sell
    return all([gate1, gate2, gate3, gate4, gate5])
```

| Gate | Condition | Fail Reason |
|------|-----------|-------------|
| **Gate 1 — Margin** | `net_margin_pct >= 20%` | Not profitable after all fees |
| **Gate 2 — Demand** | `sold_30d >= 300 units` | Market too small or product dying |
| **Gate 3 — Trend** | `trend_score >= 40` AND not declining | Keyword losing interest |
| **Gate 4 — Competition** | `competition_score >= 35` (≤ 100 sellers) | Too crowded to enter |
| **Gate 5 — Supplier** | `supplier_price <= 40% of sell_price` | Not enough markup headroom |

Store `gate_passed` boolean in `product_scores` table. Add column:
```sql
ALTER TABLE product_scores ADD COLUMN gate_passed BOOLEAN DEFAULT FALSE;
ALTER TABLE product_scores ADD COLUMN gates_failed TEXT[];  -- array of failed gate names
```

---

## 14. FULL METRICS REFERENCE TABLE

This is the master list of every metric the system must collect, compute, and store. The agentic AI must ensure **every field below exists** either in the database schema or as a computed value in the scoring engine.

### 14.1 Demand & Velocity Metrics
| Metric | DB Column | Source | Compute Method |
|--------|-----------|--------|---------------|
| Sold Count 30d | `product_listings.sold_30d` | Scraper | Direct from listing |
| Sales Velocity | `product_scores.sales_velocity` | Computed | `sold_30d / 30` |
| Sales Growth WoW | `product_scores.sales_growth_wow` | Computed | `(sold_7d − prev_sold_7d) / prev_sold_7d × 100` |
| Wishlist Count | `product_listings.wishlist_count` | Scraper | Liked/saved from platform |
| Review Recency Days | `product_scores.review_recency_days` | Scraper | Days since latest review |
| Stock Level | `product_listings.stock` | Scraper | Current stock integer |
| Order Frequency Signal | `product_scores.order_frequency` | Computed | `sold_30d / review_count` ratio |

### 14.2 Margin & Profit Metrics
| Metric | DB Column | Source | Compute Method |
|--------|-----------|--------|---------------|
| Gross Margin % | `product_scores.gross_margin_pct` | Computed | `(sell − cogs) / sell × 100` |
| Net Margin % | `product_scores.net_margin_pct` | Computed | `(sell − cogs − fees − ship) / sell × 100` |
| Gross Profit IDR | `product_scores.gross_profit_idr` | Computed | `sell − supplier − shipping` |
| Platform Fee IDR | `product_scores.platform_fee_idr` | Computed | `sell × platform_rate` |
| Supplier Price Ratio | `product_scores.supplier_price_ratio` | Computed | `sell / supplier` |
| Shipping Cost Ratio | `product_scores.shipping_cost_ratio` | Computed | `shipping / net_profit × 100` |
| Break-even Units | `product_scores.breakeven_units` | Computed | Fixed costs / net_profit_per_unit |

### 14.3 Competition Metrics
| Metric | DB Column | Source | Compute Method |
|--------|-----------|--------|---------------|
| Active Seller Count | `competition_analysis.seller_count` | Scraper | Count sellers per product |
| Top Seller Market Share | `competition_analysis.top_seller_market_share_pct` | Computed | top_sold / total_sold × 100 |
| Price Spread IDR | `competition_analysis.price_spread_idr` | Computed | max_price − min_price |
| Premium Seller Ratio | `competition_analysis.premium_seller_ratio` | Scraper | star/official count / total |
| New Seller Entry 30d | `competition_analysis.new_seller_entry_30d` | Scraper | New sellers this month |
| Ad Density % | `competition_analysis.ad_density_pct` | Scraper | Sponsored / total listings × 100 |
| Avg Competitor Rating | `competition_analysis.avg_competitor_rating` | Scraper | Mean rating top 10 sellers |

### 14.4 Trend & Timing Metrics
| Metric | DB Column | Source | Compute Method |
|--------|-----------|--------|---------------|
| Google Trends Score | `product_scores.google_trend_value` | pytrends | Interest 0-100 geo=ID |
| Trend Direction | `product_scores.trend_direction` | Computed | Compare 30d vs 90d avg |
| Trend Breakout | `product_scores.trend_breakout` | Computed | Spike > 50% in last 7d |
| TikTok Viral Signal | `product_scores.tiktok_signal` | Scraper | Boolean trending today |
| Seasonal Index | `product_scores.seasonal_index` | Computed | Historical monthly multiplier |
| Days to Harbolnas | `product_scores.days_to_harbolnas` | Computed | Days to next sale event |

### 14.5 Product Quality Metrics
| Metric | DB Column | Source | Compute Method |
|--------|-----------|--------|---------------|
| Average Rating | `product_listings.rating` | Scraper | Platform rating 0-5 |
| Review Count | `product_listings.review_count` | Scraper | Total reviews |
| Negative Review % | `product_scores.negative_review_pct` | Scraper | 1-2 star / total × 100 |
| Photo Review % | `product_scores.photo_review_pct` | Scraper | Reviews with photos / total |
| Review Recency Days | `product_scores.review_recency_days` | Scraper | Days since last review |
| Return/Complaint Rate | `product_scores.return_rate` | Scraper | If available from platform |
| Q&A Count | `product_scores.qa_count` | Scraper | Active questions on listing |

### 14.6 Supplier Metrics
| Metric | DB Column | Source | Compute Method |
|--------|-----------|--------|---------------|
| Supplier Price IDR | `suppliers.price_idr` | Scraper | Converted from USD |
| MOQ | `suppliers.moq` | Scraper | Min order quantity |
| Shipping Days | `suppliers.shipping_days_estimate` | Scraper | Transit days CN→ID |
| Shipping Cost IDR | `suppliers.shipping_cost_idr` | Scraper | Shipping fee |
| Supplier Rating | `suppliers.rating` | Scraper | AliExpress/1688 rating |
| Supplier Order Count | `suppliers.supplier_order_count` | Scraper | Total fulfilled orders |
| Local Available | `suppliers.local_available` | Manual/Scraper | Boolean domestic source |
| Product Weight (g) | `suppliers.weight_grams` | Scraper | Affects shipping cost |

### 14.7 Listing Quality Metrics
| Metric | DB Column | Source | Compute Method |
|--------|-----------|--------|---------------|
| Image Count | `product_scores.image_count` | Scraper | Number of product images |
| Has Video | `product_scores.has_video` | Scraper | Boolean |
| Description Length | `product_scores.description_length` | Scraper | Character count |
| Has Product Specs | `product_scores.has_specs` | Scraper | Boolean spec table present |
| Keyword Relevance | `product_scores.keyword_relevance_score` | Computed | Title vs top keywords match |
| Price Position | `product_scores.price_position` | Computed | vs market median |

---

*End of AGENTS.md — Total estimated build: 3-5 agentic sessions*
