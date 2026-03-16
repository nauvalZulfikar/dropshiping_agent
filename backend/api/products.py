from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import uuid

from database import get_db
from tasks.celery_app import celery_app

router = APIRouter(prefix="/products", tags=["products"])

# Full column list for listing queries
_LISTING_SELECT = """
    pl.id, pl.title, pl.platform, pl.url, pl.image_url,
    pl.price_idr, pl.sold_30d, pl.rating, pl.review_count,
    pl.seller_name, pl.seller_city, pl.seller_badge, pl.seller_count,
    pl.product_id, pl.is_active, pl.created_at, pl.updated_at,
    ps.opportunity_score, ps.margin_pct, ps.sellability_score,
    ps.trend_score, ps.competition_score, ps.gate_passed,
    ps.gates_failed, ps.computed_at
"""

# Whitelist for sort columns (prevents SQL injection)
_SORT_COLS = {
    "opportunity_score": "ps.opportunity_score",
    "margin_pct": "ps.margin_pct",
    "sold_30d": "pl.sold_30d",
    "trend_score": "ps.trend_score",
    "price_idr": "pl.price_idr",
    "created_at": "pl.created_at",
}


def _serialize(row: dict) -> dict:
    """Convert UUID and datetime objects to JSON-safe strings."""
    out = {}
    for k, v in row.items():
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@router.get("")
async def list_products(
    platform: Optional[str] = Query(None),
    category_slug: Optional[str] = Query(None),
    min_margin: Optional[float] = Query(None),
    max_price: Optional[int] = Query(None),
    min_score: Optional[float] = Query(None),
    gate_passed: Optional[bool] = Query(None),
    sort_by: str = Query("opportunity_score"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Paginated product list with filters, scores, and gate filter."""
    if sort_by not in _SORT_COLS:
        sort_by = "opportunity_score"
    sort_col = _SORT_COLS[sort_by]
    offset = (page - 1) * limit

    where_clauses = ["pl.is_active = TRUE"]
    params: dict = {"limit": limit, "offset": offset}

    if platform:
        where_clauses.append("pl.platform = :platform")
        params["platform"] = platform
    if min_margin is not None:
        where_clauses.append("ps.margin_pct >= :min_margin")
        params["min_margin"] = min_margin
    if max_price is not None:
        where_clauses.append("pl.price_idr <= :max_price")
        params["max_price"] = max_price
    if min_score is not None:
        where_clauses.append("ps.opportunity_score >= :min_score")
        params["min_score"] = min_score
    if gate_passed is not None:
        where_clauses.append("ps.gate_passed = :gate_passed")
        params["gate_passed"] = gate_passed
    if category_slug:
        where_clauses.append("""
            pl.product_id IN (
                SELECT p.id FROM products p
                JOIN categories c ON c.id = p.category_id
                WHERE c.slug = :category_slug
            )
        """)
        params["category_slug"] = category_slug

    where_sql = " AND ".join(where_clauses)

    count_q = text(f"""
        SELECT COUNT(*) FROM product_listings pl
        LEFT JOIN product_scores ps ON ps.listing_id = pl.id
        WHERE {where_sql}
    """)
    count_result = await db.execute(count_q, params)
    total = count_result.scalar()

    query = text(f"""
        SELECT {_LISTING_SELECT}
        FROM product_listings pl
        LEFT JOIN product_scores ps ON ps.listing_id = pl.id
        WHERE {where_sql}
        ORDER BY {sort_col} DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(query, params)
    rows = result.mappings().all()

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit if total else 0,
        "items": [_serialize(dict(r)) for r in rows],
    }


@router.get("/top")
@cache(expire=900)
async def top_products(db: AsyncSession = Depends(get_db)):
    """Top 20 products by opportunity score (cached 15 min)."""
    query = text(f"""
        SELECT {_LISTING_SELECT}
        FROM product_listings pl
        LEFT JOIN product_scores ps ON ps.listing_id = pl.id
        WHERE pl.is_active = TRUE
          AND ps.opportunity_score IS NOT NULL
          AND ps.gate_passed = TRUE
        ORDER BY ps.opportunity_score DESC
        LIMIT 20
    """)
    result = await db.execute(query)
    return {"items": [_serialize(dict(r)) for r in result.mappings().all()]}


@router.get("/trending")
@cache(expire=600)
async def trending_products(db: AsyncSession = Depends(get_db)):
    """Products with highest trend_score in last 24h (cached 10 min)."""
    query = text(f"""
        SELECT {_LISTING_SELECT}
        FROM product_listings pl
        LEFT JOIN product_scores ps ON ps.listing_id = pl.id
        WHERE pl.is_active = TRUE
          AND ps.trend_score IS NOT NULL
          AND ps.computed_at >= NOW() - INTERVAL '24 hours'
        ORDER BY ps.trend_score DESC
        LIMIT 20
    """)
    result = await db.execute(query)
    return {"items": [_serialize(dict(r)) for r in result.mappings().all()]}


@router.get("/{listing_id}")
async def get_product(listing_id: str, db: AsyncSession = Depends(get_db)):
    """Full product detail: listing + scores + price history + suppliers + competition."""
    listing_q = text(f"""
        SELECT {_LISTING_SELECT}
        FROM product_listings pl
        LEFT JOIN product_scores ps ON ps.listing_id = pl.id
        WHERE pl.id = :id
    """)
    result = await db.execute(listing_q, {"id": listing_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    listing = _serialize(dict(row))

    history_q = text("""
        SELECT price_idr, sold_count, recorded_at
        FROM price_history
        WHERE listing_id = :id
          AND recorded_at >= NOW() - INTERVAL '30 days'
        ORDER BY recorded_at ASC
    """)
    history = await db.execute(history_q, {"id": listing_id})

    suppliers_q = text("""
        SELECT
            s.id, s.title, s.url, s.price_idr, s.shipping_cost_idr,
            s.moq, s.seller_name, s.rating, s.source
        FROM suppliers s
        JOIN products p ON p.id = s.product_id
        JOIN product_listings pl ON pl.product_id = p.id
        WHERE pl.id = :listing_id
        ORDER BY s.price_idr ASC
    """)
    suppliers_result = await db.execute(suppliers_q, {"listing_id": listing_id})
    suppliers = [_serialize(dict(r)) for r in suppliers_result.mappings().all()]

    # Competition analysis
    competition_q = text("""
        SELECT seller_count, avg_price_idr, price_std_dev,
               top_seller_name, top_seller_share_pct, analysis_date
        FROM competition_analysis
        WHERE product_id = :product_id
        ORDER BY analysis_date DESC
        LIMIT 1
    """)
    product_id = listing.get("product_id")
    competition = {}
    if product_id:
        comp_result = await db.execute(competition_q, {"product_id": str(product_id)})
        comp_row = comp_result.mappings().first()
        if comp_row:
            competition = _serialize(dict(comp_row))

    # Platform comparison (same product across platforms)
    platform_comparison = []
    if product_id:
        platform_q = text(f"""
            SELECT {_LISTING_SELECT}
            FROM product_listings pl
            LEFT JOIN product_scores ps ON ps.listing_id = pl.id
            WHERE pl.product_id = :product_id
              AND pl.is_active = TRUE
            ORDER BY ps.opportunity_score DESC NULLS LAST
        """)
        plat_result = await db.execute(platform_q, {"product_id": str(product_id)})
        platform_comparison = [_serialize(dict(r)) for r in plat_result.mappings().all()]

    return {
        "listing": listing,
        "price_history": [_serialize(dict(r)) for r in history.mappings().all()],
        "suppliers": suppliers,
        "competition": competition,
        "platform_comparison": platform_comparison,
    }


@router.post("/{listing_id}/score")
async def trigger_score(listing_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger on-demand scoring for a single listing."""
    # Verify listing exists
    check_q = text("SELECT id FROM product_listings WHERE id = :id")
    result = await db.execute(check_q, {"id": listing_id})
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")

    celery_app.send_task(
        "tasks.score_tasks.score_single_listing",
        args=[listing_id],
    )
    return {"status": "queued", "listing_id": listing_id}
