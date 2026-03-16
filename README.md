# Dropship Research Platform
## Indonesian Online Market Intelligence System

Automatically scrapes products from Tokopedia, Shopee, and AliExpress — scores them by **margin**, **sellability**, **trend**, and **competition** — so you instantly know which products to sell today in Indonesia.

> "Input nothing. Get a ranked list of the most profitable products to sell today."

---

## Features

- **Multi-platform scraping** — Tokopedia, Shopee, AliExpress (async Playwright + stealth)
- **5-Gate filter** — only shows products that pass all: margin ≥20%, sold ≥300/mo, trend ≥40, competition ≥35, supplier ≤40% of price
- **Opportunity Score** — composite score: margin×0.35 + sellability×0.30 + trend×0.20 + competition×0.15
- **Supplier matching** — CLIP image embeddings auto-link AliExpress suppliers to marketplace products
- **Price monitoring** — detects drops/spikes every 30 min and sends Telegram alerts
- **Daily digest** — Telegram message at 08:00 WIB with top 5 gate-passed products
- **Niche Explorer** — bubble chart of market size vs margin per category
- **Watchlist** — track specific products with per-product alert settings

---

## Prerequisites

- **Docker** & **Docker Compose** v2+
- **Supabase** project (free tier works) — for PostgreSQL + Auth
- **Node.js 18+** (only for local frontend dev outside Docker)
- **Python 3.11+** (only for local backend dev outside Docker)
- **Telegram Bot** (optional) — for daily digest and price alerts

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd dropship_agent
cp .env.example .env
```

Open `.env` and fill in:

| Variable | Where to get it |
|----------|----------------|
| `SUPABASE_URL` | Supabase → Project Settings → API |
| `SUPABASE_ANON_KEY` | Supabase → Project Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API |
| `SUPABASE_JWT_SECRET` | Supabase → Project Settings → API → JWT Secret |
| `DATABASE_URL` | Supabase → Project Settings → Database → Connection string (use **Transaction** mode) |
| `SECRET_KEY` | Run: `openssl rand -hex 32` |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_ID` | Your chat/group ID (send `/start` to [@userinfobot](https://t.me/userinfobot)) |

### 2. Apply database schema

In your Supabase project → **SQL Editor**, paste and run:

```bash
# Or via psql:
psql "$DATABASE_URL" -f scripts/init_db.sql
```

> Enable the **TimescaleDB** and **pgvector** extensions in Supabase → Database → Extensions first.

### 3. Seed product categories

```bash
pip install asyncpg python-dotenv
python scripts/seed_categories.py
```

### 4. Start all services

```bash
docker-compose up --build
```

First build takes ~5 minutes (installs Playwright + Chromium). On subsequent starts:

```bash
docker-compose up
```

---

## Access Points

| Service | URL | Notes |
|---------|-----|-------|
| **Dashboard** | http://localhost:3000 | Next.js frontend |
| **API** | http://localhost:8000 | FastAPI backend |
| **API Docs** | http://localhost:8000/docs | Swagger UI — all endpoints |
| **Flower** | http://localhost:5555 | Celery task monitor (admin/dropship) |
| **Redis** | localhost:6379 | Cache + message broker |

---

## Triggering a Manual Scrape

### Via UI
Go to http://localhost:3000/scraper → enter keyword → click **Run Scrape**.

### Via API
```bash
curl -X POST http://localhost:8000/api/scraper/trigger \
  -H "Content-Type: application/json" \
  -d '{"source": "tokopedia", "keyword": "tas wanita", "max_pages": 3}'
```

Response:
```json
{"task_id": "abc-123", "source": "tokopedia", "keyword": "tas wanita", "status": "queued"}
```

Check task status:
```bash
curl http://localhost:8000/api/scraper/status/abc-123
```

### Supported sources
| Source | Products | Suppliers |
|--------|----------|-----------|
| `tokopedia` | ✅ | — |
| `shopee` | ✅ | — |
| `aliexpress` | — | ✅ |

---

## Scheduled Automation

Celery Beat runs these automatically once services are up:

| Task | Schedule | Description |
|------|----------|-------------|
| Full marketplace scan | Every hour | 8 keywords × 3 platforms |
| Score all products | Every 2 hours | Recomputes all opportunity scores |
| Monitor watchlist prices | Every 30 min | Re-scrapes watched listings, records changes |
| Telegram daily digest | 08:00 WIB | Top 5 gate-passed products |
| Watchlist alerts | Every hour at :15 | Price drop ≥5% or sold spike ≥50% |
| Embed product images | Every 6 hours | CLIP embeddings for supplier matching |
| Match suppliers | Every 6 hours | Auto-links AliExpress suppliers to products |

---

## Running Smoke Tests

With services running:

```bash
python scripts/test_scrapers.py
```

Tests: health check → trigger Tokopedia scrape → wait for completion → verify DB rows → verify scores.

---

## Project Structure

```
dropship_agent/
├── backend/
│   ├── api/              # FastAPI routers (products, analytics, watchlist, scraper, suppliers)
│   ├── engines/          # Scoring: margin, sellability, opportunity, gate filter, deduplicator
│   ├── scrapers/         # Playwright scrapers: Tokopedia, Shopee, AliExpress
│   ├── tasks/            # Celery tasks: scrape, score, alert
│   ├── utils/            # Currency parsing, datetime utils, logger
│   ├── config.py         # Pydantic settings (loads .env)
│   ├── database.py       # Async SQLAlchemy engine
│   └── main.py           # FastAPI app + lifespan
├── frontend/
│   ├── app/              # Next.js 14 App Router pages
│   │   ├── page.tsx              # Dashboard
│   │   ├── products/             # Product list + detail
│   │   ├── niches/               # Niche bubble chart
│   │   ├── suppliers/            # Supplier browser
│   │   ├── watchlist/            # User watchlist
│   │   └── scraper/              # Scraper control panel
│   ├── components/nav.tsx        # Sidebar navigation
│   ├── lib/api-client.ts         # Axios + auth interceptor
│   └── types/index.ts            # TypeScript interfaces
├── scripts/
│   ├── init_db.sql       # Full PostgreSQL schema
│   ├── seed_categories.py
│   └── test_scrapers.py
├── .env.example          # All required variables (no values)
└── docker-compose.yml    # 6 services: backend, frontend, celery_worker, celery_beat, flower, redis
```

---

## Scoring Reference

### Opportunity Score (0–100)
```
opportunity_score = margin_score×0.35 + sellability_score×0.30 + trend_score×0.20 + competition_score×0.15
```

### 5-Gate Filter
A product must pass **all 5 gates** to be recommended:

| Gate | Threshold |
|------|-----------|
| 1. Margin | Net margin ≥ 20% |
| 2. Demand | Sold ≥ 300/month |
| 3. Trend | Google Trends score ≥ 40 (geo=ID) |
| 4. Competition | Competition score ≥ 35 |
| 5. Supplier | Supplier price ≤ 40% of sell price |

### Platform Fees Used
| Platform | Fee |
|----------|-----|
| Tokopedia | 2.5% + 1.5% payment |
| Shopee | 2.0% + 1.5% payment |
| Lazada | 2.5% + 1.5% payment |
| TikTok Shop | 3.0% + 1.5% payment |

---

## Build Status

- [x] Phase 1 — Foundation & Database
- [x] Phase 2 — Scrapers (Tokopedia, Shopee, AliExpress)
- [x] Phase 3 — Scoring Engines
- [x] Phase 4 — Backend API Layer
- [x] Phase 5 — Frontend Dashboard
- [x] Phase 6 — Automation & Notifications
- [x] Phase 7 — Polish & Deployment
