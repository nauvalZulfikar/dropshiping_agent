"""
Competition analyzer engine.
Queries DB for seller count, price distribution, and market concentration
per product × platform. Writes results to competition_analysis table.
"""
from typing import Optional

import asyncpg

from utils.logger import get_logger

logger = get_logger(__name__)


async def analyze_competition(
    conn: asyncpg.Connection,
    product_id: str,
    platform: str,
) -> dict:
    """
    Analyze competition for a product on a given platform.
    Returns a dict of competition metrics, also upserts to competition_analysis.

    Metrics returned:
        seller_count, price_min_idr, price_max_idr, price_avg_idr,
        price_median_idr, price_spread_idr,
        top_seller_name, top_seller_sold_count,
        top_seller_market_share_pct, premium_seller_ratio,
        avg_competitor_rating
    """
    rows = await conn.fetch("""
        SELECT
            pl.seller_name,
            pl.seller_id,
            pl.seller_badge,
            pl.price_idr,
            pl.sold_30d,
            pl.rating
        FROM product_listings pl
        WHERE pl.product_id = $1
          AND pl.platform = $2
          AND pl.is_active = TRUE
        ORDER BY pl.sold_30d DESC NULLS LAST
    """, product_id, platform)

    if not rows:
        return {"seller_count": 0}

    prices = [r["price_idr"] for r in rows if r["price_idr"] and r["price_idr"] > 0]
    sold_counts = [r["sold_30d"] or 0 for r in rows]
    ratings = [r["rating"] for r in rows if r["rating"] is not None]

    seller_count = len(rows)
    price_min = min(prices) if prices else None
    price_max = max(prices) if prices else None
    price_avg = int(sum(prices) / len(prices)) if prices else None
    price_median = _median(prices) if prices else None
    price_spread = (price_max - price_min) if price_min and price_max else None

    total_sold = sum(sold_counts)
    top = rows[0]  # already sorted by sold_30d DESC
    top_seller_name = top["seller_name"]
    top_seller_sold = top["sold_30d"] or 0
    top_seller_share = round((top_seller_sold / total_sold) * 100, 2) if total_sold > 0 else 0.0

    # Premium sellers: official, star_seller, etc.
    premium_count = sum(
        1 for r in rows
        if r["seller_badge"] and r["seller_badge"].lower() in ("official", "star_seller", "power_seller")
    )
    premium_ratio = round((premium_count / seller_count) * 100, 2) if seller_count > 0 else 0.0

    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    result = {
        "product_id": product_id,
        "platform": platform,
        "seller_count": seller_count,
        "price_min_idr": price_min,
        "price_max_idr": price_max,
        "price_avg_idr": price_avg,
        "price_median_idr": price_median,
        "price_spread_idr": price_spread,
        "top_seller_name": top_seller_name,
        "top_seller_sold_count": top_seller_sold,
        "top_seller_market_share_pct": top_seller_share,
        "premium_seller_ratio": premium_ratio,
        "avg_competitor_rating": avg_rating,
    }

    # Upsert to competition_analysis
    await _upsert_competition(conn, result)

    return result


async def _upsert_competition(conn: asyncpg.Connection, data: dict):
    """Upsert competition_analysis row."""
    try:
        await conn.execute("""
            INSERT INTO competition_analysis (
                product_id, platform,
                seller_count,
                price_min_idr, price_max_idr, price_avg_idr, price_median_idr,
                top_seller_name, top_seller_sold_count,
                top_seller_market_share_pct, price_spread_idr,
                premium_seller_ratio, avg_competitor_rating,
                analyzed_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,NOW())
            ON CONFLICT DO NOTHING
        """,
        data["product_id"], data["platform"],
        data["seller_count"],
        data["price_min_idr"], data["price_max_idr"],
        data["price_avg_idr"], data["price_median_idr"],
        data["top_seller_name"], data["top_seller_sold_count"],
        data["top_seller_market_share_pct"], data["price_spread_idr"],
        data["premium_seller_ratio"], data["avg_competitor_rating"],
        )
    except Exception as exc:
        logger.debug(f"[Competition] Upsert failed: {exc}")


def _median(values: list[int]) -> int:
    if not values:
        return 0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) // 2
    return sorted_vals[mid]
