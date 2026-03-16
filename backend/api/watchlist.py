from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import uuid

from config import settings
from database import get_db

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


class WatchlistAdd(BaseModel):
    listing_id: str
    note: Optional[str] = None
    alert_on_price_drop: bool = True
    alert_on_spike: bool = True


class WatchlistUpdate(BaseModel):
    note: Optional[str] = None
    alert_on_price_drop: Optional[bool] = None
    alert_on_spike: Optional[bool] = None


async def _get_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate user_id from Supabase JWT."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        from jose import jwt, JWTError
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
        return user_id
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


@router.get("")
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(_get_user_id),
):
    """Return user's watchlist with current scores."""
    query = text("""
        SELECT
            w.id, w.listing_id, w.note, w.alert_on_price_drop, w.alert_on_spike, w.created_at,
            pl.title, pl.platform, pl.price_idr, pl.image_url, pl.url,
            ps.opportunity_score, ps.margin_pct, ps.trend_score, ps.gate_passed
        FROM watchlists w
        JOIN product_listings pl ON pl.id = w.listing_id
        LEFT JOIN product_scores ps ON ps.listing_id = w.listing_id
        WHERE w.user_id = :user_id
        ORDER BY w.created_at DESC
    """)
    result = await db.execute(query, {"user_id": user_id})
    rows = result.mappings().all()
    return {
        "items": [
            {k: (str(v) if isinstance(v, uuid.UUID) else (v.isoformat() if hasattr(v, "isoformat") else v))
             for k, v in dict(r).items()}
            for r in rows
        ]
    }


@router.post("", status_code=201)
async def add_to_watchlist(
    body: WatchlistAdd,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(_get_user_id),
):
    """Add a product listing to user's watchlist."""
    # Verify listing exists
    check = await db.execute(
        text("SELECT id FROM product_listings WHERE id = :id"),
        {"id": body.listing_id},
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Listing not found")

    query = text("""
        INSERT INTO watchlists (user_id, listing_id, note, alert_on_price_drop, alert_on_spike)
        VALUES (:user_id, :listing_id, :note, :alert_price, :alert_spike)
        ON CONFLICT (user_id, listing_id) DO NOTHING
        RETURNING id
    """)
    result = await db.execute(query, {
        "user_id": user_id,
        "listing_id": body.listing_id,
        "note": body.note,
        "alert_price": body.alert_on_price_drop,
        "alert_spike": body.alert_on_spike,
    })
    await db.commit()
    row = result.first()
    return {"id": str(row[0]) if row else None, "message": "Added to watchlist"}


@router.patch("/{watchlist_id}")
async def update_watchlist(
    watchlist_id: str,
    body: WatchlistUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(_get_user_id),
):
    """Update alert preferences for a watchlist entry."""
    updates = {}
    if body.note is not None:
        updates["note"] = body.note
    if body.alert_on_price_drop is not None:
        updates["alert_on_price_drop"] = body.alert_on_price_drop
    if body.alert_on_spike is not None:
        updates["alert_on_spike"] = body.alert_on_spike

    if not updates:
        return {"message": "Nothing to update"}

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    query = text(f"""
        UPDATE watchlists
        SET {set_clause}
        WHERE id = :id AND user_id = :user_id
    """)
    await db.execute(query, {**updates, "id": watchlist_id, "user_id": user_id})
    await db.commit()
    return {"message": "Updated"}


@router.delete("/{watchlist_id}", status_code=204)
async def remove_from_watchlist(
    watchlist_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(_get_user_id),
):
    """Remove a product from user's watchlist."""
    query = text("DELETE FROM watchlists WHERE id = :id AND user_id = :user_id")
    await db.execute(query, {"id": watchlist_id, "user_id": user_id})
    await db.commit()
