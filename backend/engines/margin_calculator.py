"""
Margin calculator engine.
Implements exact fee rates from DROPSHIP_AGENTS.md Section 9.
All prices in IDR (BIGINT). No floats stored as prices.
"""
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import asyncpg

from utils.logger import get_logger

logger = get_logger(__name__)

# ------------------------------------------------------------------
# Platform fee constants (conservative — use higher estimate)
# ------------------------------------------------------------------

PLATFORM_FEES: dict[str, float] = {
    "tokopedia":   0.025,   # 2.5% admin fee
    "shopee":      0.020,   # 2.0% admin fee
    "lazada":      0.025,   # 2.5% admin fee
    "tiktok_shop": 0.030,   # 3.0% admin fee
}
PAYMENT_FEE: float = 0.015  # 1.5% payment gateway (all platforms)


# ------------------------------------------------------------------
# Result dataclass
# ------------------------------------------------------------------

@dataclass
class MarginResult:
    sell_price_idr: int
    supplier_price_idr: int
    shipping_cost_idr: int
    platform_fee_idr: int
    gross_profit_idr: int
    net_profit_idr: int
    margin_pct: float           # net_profit / sell_price * 100
    gross_margin_pct: float     # (sell_price - cogs) / sell_price * 100
    supplier_price_ratio: float  # sell_price / supplier_price (target >2.5x)
    platform: str
    supplier_id: Optional[str] = None


# ------------------------------------------------------------------
# Core calculation
# ------------------------------------------------------------------

def calculate_margin(
    sell_price_idr: int,
    supplier_price_idr: int,
    shipping_cost_idr: int,
    platform: str,
) -> MarginResult:
    """
    Compute margin for a listing given supplier price.

    Formula (from AGENTS.md §8.1):
        gross_profit = sell_price - supplier_price - shipping_cost
        platform_fee = sell_price * (PLATFORM_FEES[platform] + PAYMENT_FEE)
        net_profit   = gross_profit - platform_fee
        margin_pct   = (net_profit / sell_price) * 100
    """
    if sell_price_idr <= 0:
        return _zero_margin(sell_price_idr, supplier_price_idr, shipping_cost_idr, platform)

    fee_rate = PLATFORM_FEES.get(platform, 0.025) + PAYMENT_FEE
    platform_fee_idr = int(sell_price_idr * fee_rate)

    cogs = supplier_price_idr + shipping_cost_idr
    gross_profit_idr = sell_price_idr - cogs
    net_profit_idr = gross_profit_idr - platform_fee_idr

    margin_pct = (net_profit_idr / sell_price_idr) * 100
    gross_margin_pct = (gross_profit_idr / sell_price_idr) * 100
    supplier_price_ratio = sell_price_idr / supplier_price_idr if supplier_price_idr > 0 else 0.0

    return MarginResult(
        sell_price_idr=sell_price_idr,
        supplier_price_idr=supplier_price_idr,
        shipping_cost_idr=shipping_cost_idr,
        platform_fee_idr=platform_fee_idr,
        gross_profit_idr=gross_profit_idr,
        net_profit_idr=net_profit_idr,
        margin_pct=round(margin_pct, 2),
        gross_margin_pct=round(gross_margin_pct, 2),
        supplier_price_ratio=round(supplier_price_ratio, 3),
        platform=platform,
    )


def margin_to_score(margin_pct: float) -> float:
    """
    Convert margin_pct to margin_score (0-100).
    Scoring table from AGENTS.md §8.1.
    """
    if margin_pct >= 50:
        return 100.0
    if margin_pct >= 40:
        return 90.0
    if margin_pct >= 30:
        return 75.0
    if margin_pct >= 20:
        return 55.0
    if margin_pct >= 10:
        return 30.0
    if margin_pct > 0:
        return 10.0
    return 0.0


# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------

async def find_best_supplier(
    conn: asyncpg.Connection,
    product_id: str,
) -> Optional[dict]:
    """
    Query suppliers table for this product, return cheapest valid option.
    'Valid' = price_idr > 0 and not None.
    """
    row = await conn.fetchrow("""
        SELECT id, price_idr, shipping_cost_idr, source, title, rating, moq
        FROM suppliers
        WHERE product_id = $1
          AND price_idr IS NOT NULL
          AND price_idr > 0
        ORDER BY (price_idr + COALESCE(shipping_cost_idr, 0)) ASC
        LIMIT 1
    """, product_id)
    return dict(row) if row else None


async def calculate_margin_for_listing(
    conn: asyncpg.Connection,
    listing_id: str,
) -> Optional[MarginResult]:
    """
    Load listing + best supplier from DB and compute margin.
    Returns None if no supplier found.
    """
    listing = await conn.fetchrow("""
        SELECT pl.id, pl.price_idr, pl.platform, pl.product_id
        FROM product_listings pl
        WHERE pl.id = $1
    """, listing_id)

    if not listing:
        logger.warning(f"[Margin] Listing {listing_id} not found")
        return None

    supplier = await find_best_supplier(conn, str(listing["product_id"]))
    if not supplier:
        return None

    result = calculate_margin(
        sell_price_idr=listing["price_idr"],
        supplier_price_idr=supplier["price_idr"],
        shipping_cost_idr=supplier.get("shipping_cost_idr") or 0,
        platform=listing["platform"],
    )
    result.supplier_id = str(supplier["id"])
    return result


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _zero_margin(sell: int, supplier: int, shipping: int, platform: str) -> MarginResult:
    return MarginResult(
        sell_price_idr=sell,
        supplier_price_idr=supplier,
        shipping_cost_idr=shipping,
        platform_fee_idr=0,
        gross_profit_idr=0,
        net_profit_idr=0,
        margin_pct=0.0,
        gross_margin_pct=0.0,
        supplier_price_ratio=0.0,
        platform=platform,
    )
