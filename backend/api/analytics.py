from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/margin-heatmap")
@cache(expire=1800)
async def margin_heatmap(db: AsyncSession = Depends(get_db)):
    """Returns {category, platform, avg_margin}[] for heatmap visualization (cached 30 min)."""
    query = text("""
        SELECT
            c.name AS category,
            pl.platform,
            ROUND(AVG(ps.margin_pct)::numeric, 2) AS avg_margin,
            COUNT(pl.id) AS product_count
        FROM product_listings pl
        JOIN product_scores ps ON ps.listing_id = pl.id
        JOIN products p ON p.id = pl.product_id
        JOIN categories c ON c.id = p.category_id
        WHERE ps.margin_pct IS NOT NULL
        GROUP BY c.name, pl.platform
        ORDER BY avg_margin DESC
    """)
    result = await db.execute(query)
    return {"items": [dict(r) for r in result.mappings().all()]}


@router.get("/niche-map")
@cache(expire=1800)
async def niche_map(db: AsyncSession = Depends(get_db)):
    """Returns {niche, market_size_idr, avg_margin, seller_count}[] for bubble chart (cached 30 min)."""
    query = text("""
        SELECT
            c.name AS niche,
            c.slug,
            SUM(pl.sold_30d * pl.price_idr) AS market_size_idr,
            ROUND(AVG(ps.margin_pct)::numeric, 2) AS avg_margin,
            COUNT(DISTINCT pl.seller_name) AS seller_count,
            ROUND(AVG(ps.trend_score)::numeric, 2) AS avg_trend_score,
            COUNT(pl.id) AS listing_count
        FROM product_listings pl
        JOIN product_scores ps ON ps.listing_id = pl.id
        JOIN products p ON p.id = pl.product_id
        JOIN categories c ON c.id = p.category_id
        WHERE pl.is_active = TRUE
        GROUP BY c.name, c.slug
        ORDER BY market_size_idr DESC NULLS LAST
    """)
    result = await db.execute(query)
    return {"items": [dict(r) for r in result.mappings().all()]}


@router.get("/price-history/{listing_id}")
async def price_history(listing_id: str, db: AsyncSession = Depends(get_db)):
    """30-day price + sold count time series for a listing."""
    query = text("""
        SELECT price_idr, sold_count, recorded_at
        FROM price_history
        WHERE listing_id = :id
          AND recorded_at >= NOW() - INTERVAL '30 days'
        ORDER BY recorded_at ASC
    """)
    result = await db.execute(query, {"id": listing_id})
    rows = result.mappings().all()
    return {
        "items": [
            {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(r).items()}
            for r in rows
        ]
    }


@router.get("/trends")
@cache(expire=600)
async def top_trends(db: AsyncSession = Depends(get_db)):
    """Top trending keywords in Indonesia today (cached 10 min)."""
    query = text("""
        SELECT keyword, MAX(trend_value) AS peak_value, COUNT(*) AS data_points
        FROM trend_signals
        WHERE geo = 'ID'
          AND recorded_at >= NOW() - INTERVAL '24 hours'
        GROUP BY keyword
        ORDER BY peak_value DESC
        LIMIT 20
    """)
    result = await db.execute(query)
    return {"items": [dict(r) for r in result.mappings().all()]}


@router.get("/platform-comparison/{product_id}")
@cache(expire=900)
async def platform_comparison(product_id: str, db: AsyncSession = Depends(get_db)):
    """Same product price comparison across platforms (cached 15 min)."""
    query = text("""
        SELECT
            pl.platform,
            pl.title,
            pl.price_idr,
            pl.sold_30d,
            pl.rating,
            pl.url,
            ps.margin_pct,
            ps.opportunity_score
        FROM product_listings pl
        LEFT JOIN product_scores ps ON ps.listing_id = pl.id
        WHERE pl.product_id = :product_id
          AND pl.is_active = TRUE
        ORDER BY pl.platform
    """)
    result = await db.execute(query, {"product_id": product_id})
    return {"items": [dict(r) for r in result.mappings().all()]}


@router.get("/summary")
@cache(expire=300)
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Aggregate stats for the dashboard header (cached 5 min)."""
    query = text("""
        SELECT
            COUNT(DISTINCT pl.id)                                           AS total_listings,
            COUNT(DISTINCT pl.id) FILTER (WHERE ps.gate_passed = TRUE)     AS gate_passed_count,
            COUNT(DISTINCT pl.product_id)                                   AS unique_products,
            ROUND(AVG(ps.margin_pct)::numeric, 2)                          AS avg_margin_pct,
            ROUND(AVG(ps.opportunity_score)::numeric, 2)                   AS avg_opportunity_score,
            COUNT(DISTINCT pl.platform)                                     AS platforms_tracked
        FROM product_listings pl
        LEFT JOIN product_scores ps ON ps.listing_id = pl.id
        WHERE pl.is_active = TRUE
    """)
    result = await db.execute(query)
    row = result.mappings().first()
    return dict(row) if row else {}
