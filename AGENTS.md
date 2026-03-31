# AGENTS.md — Dropshipping Automation System

Ini adalah instruksi untuk Claude Code yang bekerja di project ini.
Baca file ini sebelum menyentuh kode apapun.

---

## Konteks Project

Lo sedang membangun **automated commerce engine** untuk dropshipping di Indonesia.
Owner project adalah seorang IT developer / data scientist / AI engineer.
Tujuan akhir: sistem yang bisa jalan < 2 jam intervensi manual per hari pada bulan ke-6.

Strategi utama: **affiliate-first** — promosikan produk affiliate dulu untuk
mengumpulkan data konversi real, lalu flip niche yang terbukti ke dropshipping
untuk capture full margin (30–40% vs komisi 3–10%).

---

## Struktur Folder

```
dropship-automation/
├── AGENTS.md                    # file ini
├── docker-compose.yml           # semua services
├── .env.example                 # template env vars (JANGAN commit .env asli)
│
├── core/                        # shared utilities
│   ├── db.py                    # PostgreSQL connection pool
│   ├── redis_client.py          # Redis client
│   ├── whatsapp.py              # Fonnte WA API wrapper
│   └── logger.py                # structured logging
│
├── affiliate/                   # Fase 0 — market intelligence
│   ├── involve_asia.py          # Involve Asia API client
│   ├── shopee_affiliate.py      # Shopee Affiliate API client
│   ├── utm_generator.py         # UTM link builder + DB logger
│   ├── content_generator.py     # AI-powered script/artikel generator
│   ├── niche_scorer.py          # scoring engine + decision logic
│   └── scheduler.py             # pull data tiap 6 jam
│
├── store/                       # Fase 1–2 — toko & operasional
│   ├── platforms/
│   │   ├── base.py              # abstract PlatformAdapter
│   │   ├── shopee.py            # ShopeeAdapter
│   │   ├── tokopedia.py         # TokopediaAdapter
│   │   └── tiktok_shop.py       # TikTokAdapter
│   ├── listing_generator.py     # AI listing title + desc + tags
│   ├── repricing_bot.py         # scrape kompetitor + update harga
│   └── inventory_sync.py        # cek stok supplier tiap 2 jam
│
├── fulfillment/                 # Fase 2 — order automation
│   ├── webhook_handler.py       # terima order baru dari platform
│   ├── order_processor.py       # Celery task: parse → kirim WA supplier
│   ├── resi_parser.py           # extract nomor resi dari reply WA supplier
│   └── tracking_updater.py     # push resi ke platform
│
├── ai/                          # Fase 2–3 — AI layer
│   ├── cs_bot.py                # CS bot (Claude API + conversation history)
│   ├── escalation.py            # trigger eskalasi ke manusia
│   ├── image_enhancer.py        # rembg + Real-ESRGAN pipeline
│   └── demand_forecast.py       # Prophet model + harbolnas regressors
│
├── analytics/                   # Fase 3 — insights
│   ├── customer_segments.py     # RFM clustering (scikit-learn)
│   ├── broadcast.py             # WA broadcast campaign via Fonnte
│   └── dashboard.py             # Streamlit internal dashboard
│
├── migrations/                  # SQL migration files
│   ├── 001_affiliate_tables.sql
│   ├── 002_store_tables.sql
│   ├── 003_order_tables.sql
│   └── 004_analytics_tables.sql
│
└── tests/
    ├── test_affiliate.py
    ├── test_fulfillment.py
    └── test_ai.py
```

---

## Tech Stack

| Layer | Tool | Versi |
|---|---|---|
| Language | Python | 3.11+ |
| API framework | FastAPI | latest |
| Task queue | Celery | latest |
| Message broker | Redis | 7+ |
| Database | PostgreSQL | 15+ |
| Scraping | Playwright | latest |
| AI / LLM | Anthropic Claude API | claude-sonnet-4-20250514 |
| Image processing | Rembg, Pillow | latest |
| Forecasting | Prophet | latest |
| ML | scikit-learn | latest |
| Dashboard | Streamlit | latest |
| WhatsApp | Fonnte API | REST |
| Container | Docker + Docker Compose | latest |

---

## Database Schema

### Affiliate tables

```sql
CREATE TABLE affiliate_links (
    id              SERIAL PRIMARY KEY,
    link_id         VARCHAR(16) UNIQUE NOT NULL,
    product_id      VARCHAR(100),
    product_name    VARCHAR(500),
    merchant        VARCHAR(100),       -- involve_asia | tiktok | shopee | accesstrade
    niche           VARCHAR(100),
    channel         VARCHAR(50),        -- tiktok | ig | youtube | blog
    campaign        VARCHAR(100),
    content_id      VARCHAR(100),
    affiliate_url   TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE affiliate_performance (
    id              SERIAL PRIMARY KEY,
    link_id         VARCHAR(16) REFERENCES affiliate_links(link_id),
    date            DATE NOT NULL,
    clicks          INTEGER DEFAULT 0,
    conversions     INTEGER DEFAULT 0,
    gmv_idr         BIGINT DEFAULT 0,
    commission_idr  BIGINT DEFAULT 0,
    avg_order_value BIGINT DEFAULT 0,
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(link_id, date)
);

CREATE TABLE niche_scores (
    id              SERIAL PRIMARY KEY,
    niche           VARCHAR(100),
    scored_at       TIMESTAMP DEFAULT NOW(),
    epc             DECIMAL(10,2),
    cvr             DECIMAL(6,4),
    total_clicks    INTEGER,
    avg_order_value BIGINT,
    trend           VARCHAR(10),        -- up | flat | down
    score           DECIMAL(5,1),
    decision        VARCHAR(50),        -- flip_to_dropship | scale_affiliate | optimize | abandon
    notes           TEXT
);

CREATE TABLE content_pieces (
    id              SERIAL PRIMARY KEY,
    content_id      VARCHAR(50) UNIQUE,
    channel         VARCHAR(50),
    niche           VARCHAR(100),
    product_ids     JSONB,
    script          TEXT,
    published_at    TIMESTAMP,
    views           INTEGER DEFAULT 0,
    likes           INTEGER DEFAULT 0,
    status          VARCHAR(20)         -- draft | published | archived
);
```

### Store & order tables

```sql
CREATE TABLE products (
    id              SERIAL PRIMARY KEY,
    sku             VARCHAR(100) UNIQUE,
    name            VARCHAR(500),
    niche           VARCHAR(100),
    supplier_id     INTEGER REFERENCES suppliers(id),
    supplier_sku    VARCHAR(100),
    supplier_url    TEXT,
    cogs_idr        INTEGER,
    floor_margin    DECIMAL(4,2) DEFAULT 0.15,
    current_price   INTEGER,
    stock           INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    platform_ids    JSONB,              -- {"shopee": "xxx", "tokopedia": "yyy"}
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE suppliers (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200),
    wa_phone        VARCHAR(20),
    platform_url    TEXT,
    avg_response_min INTEGER,
    avg_delivery_day INTEGER,
    return_rate     DECIMAL(4,2),
    is_active       BOOLEAN DEFAULT TRUE,
    notes           TEXT
);

CREATE TABLE orders (
    id              SERIAL PRIMARY KEY,
    platform        VARCHAR(50),        -- shopee | tokopedia | tiktok
    platform_order_id VARCHAR(100) UNIQUE,
    product_id      INTEGER REFERENCES products(id),
    supplier_id     INTEGER REFERENCES suppliers(id),
    buyer_name      VARCHAR(200),
    buyer_phone     VARCHAR(20),
    shipping_address TEXT,
    city            VARCHAR(100),
    postal_code     VARCHAR(10),
    courier         VARCHAR(50),
    courier_service VARCHAR(50),
    quantity        INTEGER DEFAULT 1,
    sale_price_idr  INTEGER,
    cogs_idr        INTEGER,
    platform_fee_idr INTEGER,
    net_profit_idr  INTEGER,
    status          VARCHAR(50),        -- new | sent_to_supplier | shipped | delivered | returned
    resi            VARCHAR(100),
    sent_to_supplier_at TIMESTAMP,
    shipped_at      TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE conversations (
    id              SERIAL PRIMARY KEY,
    customer_phone  VARCHAR(20),
    platform        VARCHAR(50),
    role            VARCHAR(10),        -- user | assistant
    message         TEXT,
    escalated       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## Environment Variables

Semua config lewat `.env`. Jangan hardcode apapun.

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dropship
REDIS_URL=redis://localhost:6379/0

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# WhatsApp (Fonnte)
FONNTE_API_KEY=...
SUPPLIER_WA_PHONE=628xxx          # nomor WA supplier utama

# Affiliate platforms
INVOLVE_ASIA_API_KEY=...
INVOLVE_ASIA_SECRET=...
SHOPEE_AFFILIATE_TOKEN=...

# Platform APIs
SHOPEE_PARTNER_ID=...
SHOPEE_PARTNER_KEY=...
SHOPEE_SHOP_ID=...

# App config
ENVIRONMENT=development           # development | production
LOG_LEVEL=INFO
FLOOR_MARGIN=0.15                 # minimum gross margin 15%
REPRICING_INTERVAL_HOURS=6
INVENTORY_SYNC_INTERVAL_HOURS=2
```

---

## Coding Rules

### Wajib diikuti di semua file:

**1. Async-first**
Semua I/O (DB query, HTTP call, WA API) harus async.
```python
# BENAR
async def get_product(product_id: int) -> Product:
    async with db.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM products WHERE id = $1", product_id)

# SALAH — blocking di event loop
def get_product(product_id: int) -> Product:
    return db.execute("SELECT * FROM products WHERE id = $1", product_id)
```

**2. Typed everywhere**
Semua function harus punya type hints. Gunakan Pydantic models untuk data structures.
```python
from pydantic import BaseModel

class Order(BaseModel):
    platform_order_id: str
    buyer_name: str
    sale_price_idr: int
    status: str
```

**3. Structured logging**
Gunakan `core/logger.py`, jangan `print()`.
```python
from core.logger import logger

logger.info("order_processed", order_id=order.id, supplier=supplier.name)
logger.error("supplier_wa_failed", order_id=order.id, error=str(e))
```

**4. Config dari env, bukan hardcode**
```python
import os
FLOOR_MARGIN = float(os.getenv("FLOOR_MARGIN", "0.15"))
```

**5. Semua Celery task harus idempotent**
Task yang dijalankan dua kali harus aman — gunakan `ON CONFLICT DO NOTHING` atau check dulu sebelum insert.

**6. Error handling explicit**
Jangan swallow exceptions. Log dulu, baru handle.
```python
try:
    result = await send_whatsapp(phone, message)
except WaApiException as e:
    logger.error("wa_send_failed", phone=phone, error=str(e))
    await notify_admin_fallback(order_id, message)
    raise
```

**7. Jangan commit secrets**
File `.env` ada di `.gitignore`. Kalau perlu contoh, tulis ke `.env.example` dengan nilai dummy.

---

## Claude API Usage

Model yang digunakan: `claude-sonnet-4-20250514`

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic()  # baca ANTHROPIC_API_KEY dari env otomatis

# CS Bot — ada conversation history
response = await client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=500,
    system=CS_SYSTEM_PROMPT,
    messages=conversation_history  # list of {"role": ..., "content": ...}
)

# Listing generator / content gen — single turn
response = await client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1500,
    messages=[{"role": "user", "content": prompt}]
)

reply = response.content[0].text
```

Semua prompt disimpan sebagai konstanta di atas file, bukan inline di dalam function.

---

## Niche Scoring Logic

Decision engine di `affiliate/niche_scorer.py`:

| Metrik | Threshold | Poin |
|---|---|---|
| EPC ≥ Rp 5.000 | 35 | excellent |
| EPC ≥ Rp 2.000 | 25 | good |
| EPC ≥ Rp 800 | 15 | ok |
| CVR ≥ 5% | 25 | excellent |
| CVR ≥ 2.5% | 18 | good |
| CVR ≥ 1% | 10 | ok |
| AOV ≥ Rp 300k | 20 | — |
| AOV ≥ Rp 150k | 14 | — |
| Klik ≥ 2.000 | 10 | — |
| Klik ≥ 500 | 7 | — |
| Trend naik | 10 | — |

**Decision:**
- Score ≥ 65 + klik ≥ 200 → `flip_to_dropship` → kirim alert WA ke owner
- Score ≥ 45 + klik ≥ 100 → `scale_affiliate`
- Score ≥ 25 → `optimize`
- Score < 25 → `abandon`

---

## Repricing Logic

Di `store/repricing_bot.py`:

```
1. Scrape harga top 10 kompetitor untuk keyword produk
2. Hitung P20 (percentile ke-20 dari harga kompetitor)
3. Optimal price = max(floor_price, P20 × 0.98)
   floor_price = COGS / (1 - floor_margin - 0.08)  # 0.08 = fee Shopee
4. Update hanya kalau selisih > Rp 1.000 (hindari flicker)
5. Bulatkan ke ribuan terdekat
```

---

## WhatsApp Message Formats

### Order ke supplier
```
🛒 ORDER BARU #{order_id}

Produk: {product_name}
Variasi: {variant}
Qty: {quantity}

📦 KIRIM KE:
Nama: {buyer_name}
HP: {buyer_phone}
Alamat: {shipping_address}
Kota: {city} {postal_code}

Kurir: {courier} ({courier_service})
📌 Mohon kirim hari ini. Resi balas ke sini ya.
```

### Alert stok kritis ke owner
```
⚠️ STOK KRITIS
Produk: {product_name}
Sisa stok: {stock} pcs
Supplier: {supplier_name}
Action: Restock atau nonaktifkan listing
```

### Alert niche siap flip
```
🚀 NICHE SIAP DI-FLIP KE DROPSHIP
Niche: {niche}
Score: {score}/100
EPC: Rp {epc:,}
CVR: {cvr:.1%}
AOV: Rp {aov:,}
Total klik: {clicks:,}
Action: Cari supplier → buka toko di niche ini
```

---

## Eskalasi CS Bot

Bot otomatis handle > 85% query. Eskalasi ke owner jika:
- Keyword risiko: `tipu`, `palsu`, `lapor`, `somasi`, `refund paksa`
- Nilai order > Rp 500.000
- Customer yang sama komplain > 2× dalam 7 hari
- Request retur setelah 2×24 jam sejak barang diterima

Saat eskalasi: simpan flag `escalated = TRUE` di tabel `conversations`, lalu kirim WA notif ke owner dengan context percakapan terakhir.

---

## Docker Compose

```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db, redis]

  worker:
    build: .
    command: celery -A core.celery_app worker --loglevel=info
    env_file: .env
    depends_on: [db, redis]

  beat:
    build: .
    command: celery -A core.celery_app beat --loglevel=info
    env_file: .env
    depends_on: [redis]

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: dropship
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine

  dashboard:
    build: .
    command: streamlit run analytics/dashboard.py --server.port 8501
    ports: ["8501:8501"]
    env_file: .env
    depends_on: [db]

volumes:
  pgdata:
```

---

## Urutan Build (ikuti ini, jangan skip fase)

### Fase 0 — Fondasi (build duluan)
1. `docker-compose.yml` + `Dockerfile`
2. `migrations/` — semua SQL schema
3. `core/db.py` + `core/redis_client.py` + `core/logger.py`
4. `core/whatsapp.py` — Fonnte wrapper
5. `affiliate/involve_asia.py` — API client
6. `affiliate/utm_generator.py`
7. `affiliate/scheduler.py` — pull data tiap 6 jam
8. `affiliate/niche_scorer.py` — decision engine + alert

### Fase 1–2 — Store & Automation
9. `store/platforms/base.py` + `store/platforms/shopee.py`
10. `store/listing_generator.py`
11. `store/repricing_bot.py`
12. `store/inventory_sync.py`
13. `fulfillment/webhook_handler.py`
14. `fulfillment/order_processor.py`
15. `fulfillment/resi_parser.py`

### Fase 2–3 — AI Layer
16. `ai/cs_bot.py` + `ai/escalation.py`
17. `ai/image_enhancer.py`
18. `ai/demand_forecast.py`
19. `analytics/customer_segments.py`
20. `analytics/dashboard.py`

---

## Testing

Setiap modul harus punya unit test minimal untuk happy path dan satu error case.

```bash
# Jalankan semua test
pytest tests/ -v

# Test spesifik modul
pytest tests/test_affiliate.py -v
pytest tests/test_fulfillment.py -v
```

Untuk test yang butuh API eksternal (Involve Asia, Shopee, WA), gunakan mock:
```python
from unittest.mock import AsyncMock, patch

@patch("affiliate.involve_asia.InvolveAsiaClient.get_conversions")
async def test_niche_scorer(mock_get):
    mock_get.return_value = pd.DataFrame([...])
    ...
```

---

## Dashboard Spec (`analytics/dashboard.py`)

Streamlit app, port 8501. Sidebar navigasi ke 5 halaman.
Semua query langsung ke PostgreSQL. Timezone display: `Asia/Jakarta` di semua timestamp.
Tombol Refresh manual di sidebar — tidak perlu auto-refresh otomatis.

### Halaman 1 — Overview (default)

**KPI row (4 kolom):**
- Revenue Hari Ini — `SUM(sale_price_idr)` orders hari ini, delta vs kemarin (%)
- Order Masuk — `COUNT(*)` orders hari ini, delta vs kemarin
- Gross Margin Rata-rata — avg 7 hari, delta vs 7 hari sebelumnya
- Stok Kritis — count products WHERE stock ≤ 5 AND is_active, selalu merah kalau > 0

**Alert box (tampil hanya kalau kondisi terpenuhi):**
- `st.error` kalau ada produk stok 0
- `st.warning` kalau ada order status `new` > 2 jam belum diproses
- `st.warning` kalau gross margin < 15%

**Chart:** revenue + net profit overlay, 30 hari terakhir, line chart.

**Tabel order terbaru:** 20 baris, kolom: waktu, platform, produk, kota buyer, harga, status. Status pakai color badge (new=biru, sent=kuning, shipped=hijau, returned=merah).

---

### Halaman 2 — Affiliate Intelligence

**KPI row (4 kolom):**
EPC rata-rata 7 hari · Total klik bulan ini · Total komisi bulan ini · Jumlah niche aktif.

**Tabel Niche Leaderboard:** kolom: niche, EPC, CVR (%), AOV, total klik, trend (↑→↓), score, keputusan.
Sort default: EPC descending.
Warna baris: `flip_to_dropship`=hijau, `scale_affiliate`=biru, `optimize`=kuning, `abandon`=merah muda.

**Chart EPC trend 14 hari:** multi-line, satu line per niche, tampilkan 5 niche EPC tertinggi saja.

**Tabel konten performance:** kolom: content ID, channel, niche, klik, konversi, CVR, komisi. Filter by channel via `st.selectbox`.

---

### Halaman 3 — Orders & Fulfillment

**KPI row (4 kolom):**
Order hari ini · Pending diproses · Sedang dikirim · Return rate 30 hari.

**Funnel chart (horizontal bar):** new → sent_to_supplier → shipped → delivered → returned, tampilkan count tiap stage.

**Tabel order aktif** (status bukan delivered/returned):
- Highlight merah: `sent_to_supplier` tapi belum ada resi > 12 jam
- Highlight kuning: `new` > 2 jam belum diproses

**Tabel supplier performance:** avg fulfillment time, fulfillment rate (%), return rate (%), total order bulan ini. Sort: fulfillment rate ascending — yang bermasalah paling atas.

---

### Halaman 4 — Products & Inventory

**Filter bar:** platform (all/shopee/tokopedia/tiktok) · niche · status (aktif/nonaktif/semua).

**Tabel produk:** kolom: SKU, nama, niche, stok, harga, COGS, margin (%), terjual 30 hari, revenue 30 hari.
- Highlight merah: stok ≤ 5
- Highlight kuning: margin < 20%
- Highlight hijau: terjual > 50 dalam 30 hari (best seller)

**Chart top 10 produk by revenue (30 hari):** horizontal bar chart, sorted descending.

---

### Halaman 5 — CS Bot Analytics

**KPI row (4 kolom):**
Total pesan hari ini · Total customer unik hari ini · Resolution rate (% tanpa eskalasi) · Eskalasi hari ini.

**Chart resolution rate trend 7 hari:** line chart, tambahkan garis horizontal target 85%.

**Chart volume pesan harian 14 hari:** bar chart overlay — total pesan (biru) vs eskalasi (merah).

**Tabel eskalasi terbaru:** kolom: waktu, customer phone (masked: 08xx\*\*\*\*xxxx), platform, preview pesan (80 karakter pertama).

---

### Sidebar

Navigasi ke 5 halaman via `st.radio`. Tampilkan waktu sekarang WIB dan environment (development/production). Tombol Refresh manual untuk clear cache dan rerun.

---

### Query helpers (`analytics/queries.py`)

Semua query dashboard dikumpulkan di `queries.py`, tidak inline di `dashboard.py`:

```python
async def get_today_revenue(conn) -> int: ...
async def get_today_orders(conn) -> int: ...
async def get_avg_margin_7d(conn) -> float: ...
async def get_critical_stock_count(conn) -> int: ...
async def get_revenue_30d(conn) -> pd.DataFrame: ...        # date, revenue, net_profit
async def get_recent_orders(conn, limit=20) -> pd.DataFrame: ...
async def get_niche_leaderboard(conn) -> pd.DataFrame: ...
async def get_epc_trend_14d(conn) -> pd.DataFrame: ...     # date, niche, epc
async def get_active_orders(conn) -> pd.DataFrame: ...
async def get_supplier_performance(conn) -> pd.DataFrame: ...
async def get_product_table(conn, platform=None, niche=None, active_only=True) -> pd.DataFrame: ...
async def get_top_products_revenue(conn, days=30, limit=10) -> pd.DataFrame: ...
async def get_cs_stats_today(conn) -> dict: ...
async def get_escalations_recent(conn, limit=20) -> pd.DataFrame: ...
```

---

### Seed data untuk development

Buat `scripts/seed_dev_data.py` yang generate data dummy realistis:
- 90 hari order history, 5 niche, 30 produk, 3 supplier
- Affiliate performance dengan EPC bervariasi per niche
- Order dengan mix status berbeda-beda
- Conversation history dengan mix resolved + escalated

Jalankan dengan: `python scripts/seed_dev_data.py`

---

## Catatan Penting

- **Indonesia-specific:** semua harga dalam IDR (integer, bukan float). Tanggal pakai `Asia/Jakarta` timezone.
- **Harbolnas dates:** 1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.7, 8.8, 9.9, 10.10, 11.11, 12.12 — ini event belanja besar, harus jadi regressor di demand forecast.
- **Payday:** tanggal 1, 2, 25, 26, 27 setiap bulan — demand biasanya naik.
- **COD:** mayoritas buyer Indo pakai COD. Platform yang handle COD: Shopee, Tokopedia, TikTok Shop. Jangan assume semua transaksi prepaid.
- **Supplier WA:** supplier Indo hampir semua komunikasi via WhatsApp, bukan email. Semua notif order harus via WA, bukan email.
- **Platform fee Shopee:** estimasi 6–8% dari harga jual (tergantung kategori + program). Gunakan 8% untuk kalkulasi konservatif.

---

## Dashboard Spec (`analytics/dashboard.py`)

Streamlit app, port 8501. Sidebar navigasi ke 5 halaman.
Auto-refresh setiap 5 menit via `st.rerun()` + `time.sleep()` di background thread.
Semua query langsung ke PostgreSQL — tidak ada caching di layer app (PostgreSQL cukup untuk volume awal).
Timezone display: `Asia/Jakarta` di semua timestamp.

---

### Halaman 1 — Overview (default/home)

**KPI row (4 kolom `st.metric`):**
| Metric | Query | Delta |
|---|---|---|
| Revenue Hari Ini | `SUM(sale_price_idr)` orders hari ini | vs kemarin (%) |
| Order Masuk | `COUNT(*)` orders hari ini | vs kemarin |
| Gross Margin Rata-rata | `AVG((sale_price_idr - cogs_idr - platform_fee_idr) / sale_price_idr)` 7 hari | vs 7 hari sebelumnya |
| Stok Kritis | `COUNT(*)` products WHERE stock ≤ 5 AND is_active | — (selalu merah kalau > 0) |

**Chart — Revenue 30 hari:**
`st.line_chart` dari `SUM(sale_price_idr)` GROUP BY date, 30 hari terakhir.
Overlay garis tipis untuk net profit (revenue - cogs - fee).

**Tabel — Order terbaru (20 baris):**
Kolom: waktu, platform, produk, buyer kota, harga jual, status.
Status pakai color badge: `new` = biru, `sent_to_supplier` = kuning, `shipped` = hijau, `returned` = merah.

**Alert box (tampil hanya kalau ada kondisi kritis):**
- Stok 0 → `st.error("⚠️ {n} produk kehabisan stok — listing dinonaktifkan")`
- Order pending > 3 jam tidak diproses → `st.warning`
- Margin di bawah 15% di 5 order terakhir → `st.warning`

---

### Halaman 2 — Affiliate Intelligence

**KPI row (4 kolom):**
EPC rata-rata 7 hari · Total klik bulan ini · Total komisi bulan ini · Niche aktif yang di-track.

**Tabel Niche Leaderboard:**
Kolom: niche, EPC, CVR (%), AOV, total klik, trend (↑↓→), score, decision.
Sort default: EPC descending.
Warnai baris: `flip_to_dropship` = hijau, `scale_affiliate` = biru, `optimize` = kuning, `abandon` = merah muda.

**Chart — EPC trend per niche (14 hari):**
`st.line_chart` multi-series, satu line per niche.
Hanya tampilkan 5 niche dengan EPC tertinggi supaya tidak crowded.

**Tabel Konten Performance:**
Kolom: content_id, channel, niche, klik, konversi, CVR, komisi.
Filter by channel (TikTok / IG / YouTube / Blog) via `st.selectbox`.

---

### Halaman 3 — Orders & Fulfillment

**KPI row:**
Order hari ini · Pending diproses · Sedang dikirim · Return rate 30 hari.

**Funnel chart (st.bar_chart horizontal):**
`new` → `sent_to_supplier` → `shipped` → `delivered` → `returned`
Tampilkan count di tiap stage.

**Tabel order aktif (status bukan `delivered` / `returned`):**
Kolom: order ID, platform, produk, buyer, kota, kurir, status, waktu terakhir update.
Highlight baris merah kalau `sent_to_supplier` tapi belum ada resi > 12 jam.
Highlight kuning kalau `new` > 2 jam belum diproses (automation mungkin gagal).

**Supplier performance table:**
Kolom: nama supplier, avg delivery days, fulfillment rate (%), return rate (%), order bulan ini.
Sort: fulfillment rate ascending (yang jelek paling atas).

---

### Halaman 4 — Products & Inventory

**Filter bar:** platform (all/shopee/tokopedia/tiktok) · niche · status (active/inactive).

**Tabel produk:**
Kolom: SKU, nama, niche, stok, harga jual, COGS, margin (%), terjual 30 hari, revenue 30 hari.
Highlight merah: stok ≤ 5.
Highlight kuning: margin < 20%.
Highlight hijau: terjual > 50 dalam 30 hari (best seller).

**Chart — Top 10 produk by revenue (30 hari):**
`st.bar_chart` horizontal, sorted descending.

**Price history (expandable per produk):**
Klik produk → expand → tampilkan `st.line_chart` harga 14 hari terakhir dari log repricing.

---

### Halaman 5 — CS Bot Analytics

**KPI row:**
Total pesan hari ini · Resolution rate (% tanpa eskalasi) · Avg response time · Eskalasi hari ini.

**Pie chart — Intent distribution:**
Top 8 intent yang paling sering muncul (dari conversation log, di-cluster manual atau pakai keyword matching).

**Tabel eskalasi terbaru:**
Kolom: waktu, customer phone (masked: 08xx****xxxx), pesan terakhir, alasan eskalasi, status (resolved/open).

**Response time trend (7 hari):**
`st.line_chart` avg response time bot per hari dalam detik.

---

### Sidebar

```python
st.sidebar.title("Dropship Dashboard")
page = st.sidebar.radio("Navigasi", [
    "Overview",
    "Affiliate Intelligence",
    "Orders & Fulfillment",
    "Products & Inventory",
    "CS Bot Analytics",
])
st.sidebar.divider()
st.sidebar.caption(f"Last updated: {datetime.now(tz).strftime('%H:%M:%S WIB')}")
st.sidebar.caption(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
```

---

### Query helpers yang harus ada di `analytics/queries.py`

```python
# Semua query dashboard dikumpulkan di sini, bukan inline di dashboard.py

async def get_today_revenue(conn) -> int: ...
async def get_today_orders(conn) -> int: ...
async def get_avg_margin_7d(conn) -> float: ...
async def get_critical_stock_count(conn) -> int: ...
async def get_revenue_30d(conn) -> pd.DataFrame: ...        # columns: date, revenue, net_profit
async def get_recent_orders(conn, limit=20) -> pd.DataFrame: ...
async def get_niche_leaderboard(conn) -> pd.DataFrame: ...
async def get_epc_trend_14d(conn) -> pd.DataFrame: ...     # columns: date, niche, epc
async def get_active_orders(conn) -> pd.DataFrame: ...
async def get_supplier_performance(conn) -> pd.DataFrame: ...
async def get_product_table(conn, platform=None, niche=None, active_only=True) -> pd.DataFrame: ...
async def get_top_products_revenue(conn, days=30, limit=10) -> pd.DataFrame: ...
async def get_cs_stats_today(conn) -> dict: ...
async def get_escalations_recent(conn, limit=20) -> pd.DataFrame: ...
async def get_intent_distribution(conn, days=7) -> pd.DataFrame: ...
```

---

### Seed data untuk development

Buat `scripts/seed_dev_data.py` yang generate data dummy realistis:
- 90 hari order history, 5 niche, 30 produk, 3 supplier
- Affiliate performance dengan EPC bervariasi per niche
- Beberapa order dengan status berbeda-beda
- Conversation history dengan mix resolved + escalated

Jalankan dengan: `python scripts/seed_dev_data.py`
Sehingga dashboard bisa langsung keliatan ada isinya tanpa harus tunggu data real.
