from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import uuid

from database import get_db

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _serialize(row: dict) -> dict:
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
async def list_suppliers(
    source: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None),
    max_price_idr: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Paginated supplier list with optional filters."""
    where = ["1=1"]
    params: dict = {"limit": limit, "offset": (page - 1) * limit}

    if source:
        where.append("s.source = :source")
        params["source"] = source
    if product_id:
        where.append("s.product_id = :product_id")
        params["product_id"] = product_id
    if min_rating is not None:
        where.append("s.rating >= :min_rating")
        params["min_rating"] = min_rating
    if max_price_idr is not None:
        where.append("s.price_idr <= :max_price_idr")
        params["max_price_idr"] = max_price_idr

    where_sql = " AND ".join(where)

    count_q = text(f"SELECT COUNT(*) FROM suppliers s WHERE {where_sql}")
    total = (await db.execute(count_q, params)).scalar()

    query = text(f"""
        SELECT
            s.id, s.product_id, s.source, s.title, s.url, s.image_url,
            s.price_idr, s.shipping_cost_idr, s.moq, s.seller_name,
            s.rating, s.scraped_at,
            p.canonical_name AS product_name
        FROM suppliers s
        LEFT JOIN products p ON p.id = s.product_id
        WHERE {where_sql}
        ORDER BY s.price_idr ASC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(query, params)
    rows = result.mappings().all()

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": [_serialize(dict(r)) for r in rows],
    }


@router.get("/{supplier_id}")
async def get_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    """Full supplier detail."""
    query = text("""
        SELECT
            s.*,
            p.canonical_name AS product_name,
            p.canonical_image_url AS product_image_url
        FROM suppliers s
        LEFT JOIN products p ON p.id = s.product_id
        WHERE s.id = :id
    """)
    result = await db.execute(query, {"id": supplier_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return _serialize(dict(row))


@router.get("/product/{product_id}/best")
@cache(expire=600)
async def best_suppliers_for_product(product_id: str, db: AsyncSession = Depends(get_db)):
    """Top 5 cheapest suppliers for a product (cached 10 min)."""
    query = text("""
        SELECT
            s.id, s.source, s.title, s.url, s.price_idr,
            s.shipping_cost_idr, s.moq, s.seller_name, s.rating,
            (s.price_idr + s.shipping_cost_idr) AS total_cost_idr
        FROM suppliers s
        WHERE s.product_id = :product_id
          AND s.price_idr IS NOT NULL
        ORDER BY total_cost_idr ASC
        LIMIT 5
    """)
    result = await db.execute(query, {"product_id": product_id})
    return {"items": [_serialize(dict(r)) for r in result.mappings().all()]}
