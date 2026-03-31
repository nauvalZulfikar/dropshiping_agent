"""
All dashboard query helpers.
Each function takes an asyncpg connection and returns data ready for display.
"""
from datetime import date, timedelta

import asyncpg
import pandas as pd


async def get_today_revenue(conn: asyncpg.Connection) -> int:
    val = await conn.fetchval(
        "SELECT COALESCE(SUM(sale_price_idr), 0) FROM orders WHERE created_at::date = CURRENT_DATE"
    )
    return int(val)


async def get_yesterday_revenue(conn: asyncpg.Connection) -> int:
    val = await conn.fetchval(
        "SELECT COALESCE(SUM(sale_price_idr), 0) FROM orders WHERE created_at::date = CURRENT_DATE - 1"
    )
    return int(val)


async def get_today_orders(conn: asyncpg.Connection) -> int:
    return await conn.fetchval(
        "SELECT COUNT(*) FROM orders WHERE created_at::date = CURRENT_DATE"
    )


async def get_yesterday_orders(conn: asyncpg.Connection) -> int:
    return await conn.fetchval(
        "SELECT COUNT(*) FROM orders WHERE created_at::date = CURRENT_DATE - 1"
    )


async def get_avg_margin_7d(conn: asyncpg.Connection) -> float:
    val = await conn.fetchval(
        """
        SELECT COALESCE(AVG(
            CASE WHEN sale_price_idr > 0
            THEN (sale_price_idr - cogs_idr - COALESCE(platform_fee_idr, 0))::float / sale_price_idr
            ELSE 0 END
        ), 0)
        FROM orders
        WHERE created_at >= CURRENT_DATE - 7
        """
    )
    return round(float(val), 4)


async def get_avg_margin_prev_7d(conn: asyncpg.Connection) -> float:
    val = await conn.fetchval(
        """
        SELECT COALESCE(AVG(
            CASE WHEN sale_price_idr > 0
            THEN (sale_price_idr - cogs_idr - COALESCE(platform_fee_idr, 0))::float / sale_price_idr
            ELSE 0 END
        ), 0)
        FROM orders
        WHERE created_at >= CURRENT_DATE - 14 AND created_at < CURRENT_DATE - 7
        """
    )
    return round(float(val), 4)


async def get_critical_stock_count(conn: asyncpg.Connection) -> int:
    return await conn.fetchval(
        "SELECT COUNT(*) FROM products WHERE stock <= 5 AND is_active = TRUE"
    )


async def get_revenue_30d(conn: asyncpg.Connection) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT created_at::date as date,
               SUM(sale_price_idr) as revenue,
               SUM(net_profit_idr) as net_profit
        FROM orders
        WHERE created_at >= CURRENT_DATE - 30
        GROUP BY date ORDER BY date
        """
    )
    return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame(columns=["date", "revenue", "net_profit"])


async def get_recent_orders(conn: asyncpg.Connection, limit: int = 20) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT o.created_at, o.platform, p.name as product, o.city,
               o.sale_price_idr as price, o.status
        FROM orders o
        LEFT JOIN products p ON p.id = o.product_id
        ORDER BY o.created_at DESC LIMIT $1
        """,
        limit,
    )
    return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()


async def get_niche_leaderboard(conn: asyncpg.Connection) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT niche, epc, cvr, total_clicks, avg_order_value as aov,
               trend, score, decision
        FROM niche_scores
        WHERE id IN (SELECT MAX(id) FROM niche_scores GROUP BY niche)
        ORDER BY epc DESC
        """
    )
    return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()


async def get_epc_trend_14d(conn: asyncpg.Connection) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT ap.date, al.niche,
               CASE WHEN SUM(ap.clicks) > 0
               THEN SUM(ap.commission_idr)::float / SUM(ap.clicks) ELSE 0 END as epc
        FROM affiliate_performance ap
        JOIN affiliate_links al ON al.link_id = ap.link_id
        WHERE ap.date >= CURRENT_DATE - 14
        GROUP BY ap.date, al.niche
        ORDER BY ap.date
        """
    )
    return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()


async def get_active_orders(conn: asyncpg.Connection) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT o.id, o.platform, p.name as product, o.buyer_name,
               o.city, o.courier, o.status, o.updated_at,
               EXTRACT(EPOCH FROM (NOW() - o.created_at)) / 3600 as hours_since_created,
               o.resi
        FROM orders o
        LEFT JOIN products p ON p.id = o.product_id
        WHERE o.status NOT IN ('delivered', 'returned')
        ORDER BY o.created_at DESC
        """
    )
    return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()


async def get_supplier_performance(conn: asyncpg.Connection) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT s.name,
               COALESCE(AVG(s.avg_delivery_day), 0) as avg_delivery_days,
               COUNT(o.id) FILTER (WHERE o.status = 'delivered')::float /
                   NULLIF(COUNT(o.id), 0) * 100 as fulfillment_rate,
               s.return_rate * 100 as return_rate_pct,
               COUNT(o.id) FILTER (WHERE o.created_at >= CURRENT_DATE - 30) as orders_this_month
        FROM suppliers s
        LEFT JOIN orders o ON o.supplier_id = s.id
        GROUP BY s.id, s.name, s.avg_delivery_day, s.return_rate
        ORDER BY fulfillment_rate ASC NULLS LAST
        """
    )
    return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()


async def get_product_table(
    conn: asyncpg.Connection,
    platform: str | None = None,
    niche: str | None = None,
    active_only: bool = True,
) -> pd.DataFrame:
    conditions = []
    args = []
    idx = 1

    if active_only:
        conditions.append("p.is_active = TRUE")
    if niche:
        conditions.append(f"p.niche = ${idx}")
        args.append(niche)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    rows = await conn.fetch(
        f"""
        SELECT p.sku, p.name, p.niche, p.stock, p.current_price as price,
               p.cogs_idr as cogs,
               CASE WHEN p.current_price > 0
               THEN ((p.current_price - p.cogs_idr)::float / p.current_price * 100) ELSE 0 END as margin_pct,
               COALESCE(sales.qty, 0) as sold_30d,
               COALESCE(sales.rev, 0) as revenue_30d
        FROM products p
        LEFT JOIN (
            SELECT product_id, SUM(quantity) as qty, SUM(sale_price_idr) as rev
            FROM orders WHERE created_at >= CURRENT_DATE - 30
            GROUP BY product_id
        ) sales ON sales.product_id = p.id
        {where}
        ORDER BY revenue_30d DESC
        """,
        *args,
    )
    return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()


async def get_top_products_revenue(conn: asyncpg.Connection, days: int = 30, limit: int = 10) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT p.name, SUM(o.sale_price_idr) as revenue
        FROM orders o
        JOIN products p ON p.id = o.product_id
        WHERE o.created_at >= CURRENT_DATE - $1
        GROUP BY p.name
        ORDER BY revenue DESC
        LIMIT $2
        """,
        days, limit,
    )
    return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()


async def get_cs_stats_today(conn: asyncpg.Connection) -> dict:
    total = await conn.fetchval(
        "SELECT COUNT(*) FROM conversations WHERE created_at::date = CURRENT_DATE"
    )
    unique_customers = await conn.fetchval(
        "SELECT COUNT(DISTINCT customer_phone) FROM conversations WHERE created_at::date = CURRENT_DATE"
    )
    escalated = await conn.fetchval(
        "SELECT COUNT(*) FROM conversations WHERE created_at::date = CURRENT_DATE AND escalated = TRUE"
    )
    total_user = await conn.fetchval(
        "SELECT COUNT(*) FROM conversations WHERE created_at::date = CURRENT_DATE AND role = 'user'"
    )
    resolution_rate = ((total_user - escalated) / total_user * 100) if total_user > 0 else 100

    return {
        "total_messages": total,
        "unique_customers": unique_customers,
        "escalated": escalated,
        "resolution_rate": round(resolution_rate, 1),
    }


async def get_escalations_recent(conn: asyncpg.Connection, limit: int = 20) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT created_at, customer_phone, platform,
               LEFT(message, 80) as preview
        FROM conversations
        WHERE escalated = TRUE AND role = 'user'
        ORDER BY created_at DESC
        LIMIT $1
        """,
        limit,
    )
    df = pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    if not df.empty and "customer_phone" in df.columns:
        df["customer_phone"] = df["customer_phone"].apply(
            lambda x: x[:4] + "****" + x[-4:] if len(x) > 8 else x
        )
    return df


async def get_intent_distribution(conn: asyncpg.Connection, days: int = 7) -> pd.DataFrame:
    rows = await conn.fetch(
        """
        SELECT message FROM conversations
        WHERE role = 'user' AND created_at >= CURRENT_DATE - $1
        """,
        days,
    )

    intent_map = {
        "stok/ready": ["ready", "stok", "tersedia", "available"],
        "pengiriman": ["kirim", "sampai", "estimasi", "tracking", "resi"],
        "harga": ["harga", "diskon", "kurang", "promo", "murah"],
        "COD": ["cod", "bayar ditempat"],
        "retur": ["retur", "kembalikan", "refund", "tukar"],
        "komplain": ["kecewa", "palsu", "tipu", "rusak", "cacat"],
        "variasi": ["warna", "ukuran", "variasi", "varian"],
        "terima kasih": ["makasih", "terima kasih", "thanks"],
    }

    counts = {intent: 0 for intent in intent_map}
    for row in rows:
        msg = row["message"].lower()
        for intent, keywords in intent_map.items():
            if any(kw in msg for kw in keywords):
                counts[intent] += 1
                break

    df = pd.DataFrame(list(counts.items()), columns=["intent", "count"])
    return df.sort_values("count", ascending=False)
