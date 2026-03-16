"""
Opportunity scorer — the main composite scoring engine.

Weights from AGENTS.md §8.8:
    opportunity_score = (
        margin_score      * 0.35 +
        sellability_score * 0.30 +
        trend_score       * 0.20 +
        competition_score * 0.15
    )

This module orchestrates all sub-scorers and writes the final
product_scores row to the database.
"""
import asyncio
from typing import Optional

import asyncpg

from engines.margin_calculator import (
    calculate_margin_for_listing,
    margin_to_score,
)
from engines.sellability_scorer import (
    compute_sellability,
    compute_competition_score,
    compute_supplier_risk_score,
    compute_product_quality_score,
    compute_listing_quality_score,
    compute_timing_score,
    compute_market_health_score,
)
from engines.competition_analyzer import analyze_competition
from engines.gate_filter import passes_all_gates, evaluate_gates
from engines.trend_engine import compute_trend_score
from utils.datetime_utils import days_to_next_sale_event, seasonal_index
from utils.logger import get_logger

logger = get_logger(__name__)

# Composite score weights (must sum to 1.0)
WEIGHTS = {
    "margin_score":      0.35,
    "sellability_score": 0.30,
    "trend_score":       0.20,
    "competition_score": 0.15,
}


async def compute_opportunity_score(listing_id: str, db_url: Optional[str] = None) -> dict:
    """
    Full opportunity scoring pipeline for a single listing.

    Steps:
    1. Load listing data from DB
    2. Compute margin (requires supplier)
    3. Compute sellability
    4. Fetch trend score for the product keyword
    5. Compute competition score
    6. Calculate composite opportunity_score
    7. Compute auxiliary scores (timing, quality, market_health, supplier_risk)
    8. Evaluate gate filter
    9. Upsert product_scores row
    10. Return score dict
    """
    from config import settings
    url = db_url or settings.database_url

    conn = await asyncpg.connect(url)
    try:
        # 1. Load listing
        listing = await conn.fetchrow("""
            SELECT pl.id, pl.product_id, pl.platform, pl.price_idr,
                   pl.sold_30d, pl.sold_count, pl.review_count, pl.rating,
                   pl.seller_id, pl.title, pl.image_url
            FROM product_listings pl
            WHERE pl.id = $1 AND pl.is_active = TRUE
        """, listing_id)

        if not listing:
            logger.warning(f"[Scorer] Listing {listing_id} not found or inactive")
            return {}

        product_id = str(listing["product_id"])

        # 2. Margin
        margin_result = await calculate_margin_for_listing(conn, listing_id)
        if margin_result:
            margin_score = margin_to_score(margin_result.margin_pct)
            margin_pct = margin_result.margin_pct
            supplier_price_idr = margin_result.supplier_price_idr
            platform_fee_idr = margin_result.platform_fee_idr
            shipping_est_idr = margin_result.shipping_cost_idr
            gross_profit_idr = margin_result.net_profit_idr
            best_supplier_id = margin_result.supplier_id
            supplier_price_ratio = margin_result.supplier_price_ratio
        else:
            # No supplier found — margin score 0 but still score other dimensions
            margin_score = 0.0
            margin_pct = 0.0
            supplier_price_idr = 0
            platform_fee_idr = 0
            shipping_est_idr = 0
            gross_profit_idr = 0
            best_supplier_id = None
            supplier_price_ratio = 0.0

        # 3. Sellability
        sold_growth_pct = await _compute_sold_growth(conn, listing_id)
        sellability_score = compute_sellability(
            sold_30d=listing["sold_30d"] or 0,
            review_count=listing["review_count"] or 0,
            rating=listing["rating"],
            sold_growth_pct=sold_growth_pct,
        )

        # 4. Trend score
        keyword = _extract_search_keyword(listing["title"])
        try:
            trend_data = await compute_trend_score(keyword)
            trend_score = trend_data["trend_score"]
            trend_direction = trend_data["trend_direction"]
            trend_breakout = trend_data["trend_breakout"]
        except Exception as exc:
            logger.warning(f"[Scorer] Trend fetch failed for '{keyword}': {exc}")
            trend_score = 0.0
            trend_direction = "stable"
            trend_breakout = False

        # 5. Competition score
        comp_data = await analyze_competition(conn, product_id, listing["platform"])
        seller_count = comp_data.get("seller_count", 999)
        competition_score = compute_competition_score(seller_count)

        # 6. Composite opportunity score
        opportunity_score = (
            margin_score      * WEIGHTS["margin_score"] +
            sellability_score * WEIGHTS["sellability_score"] +
            trend_score       * WEIGHTS["trend_score"] +
            competition_score * WEIGHTS["competition_score"]
        )
        opportunity_score = round(min(max(opportunity_score, 0.0), 100.0), 2)

        # 7. Auxiliary scores
        supplier_risk_score = 0.0
        if best_supplier_id:
            sup = await conn.fetchrow(
                "SELECT rating, moq, shipping_days_estimate FROM suppliers WHERE id = $1",
                best_supplier_id
            )
            if sup:
                supplier_risk_score = compute_supplier_risk_score(
                    supplier_rating=sup["rating"],
                    shipping_days=sup["shipping_days_estimate"],
                    moq=sup["moq"] or 1,
                )

        quality_score = compute_product_quality_score(
            avg_rating=listing["rating"],
            review_count=listing["review_count"] or 0,
        )

        listing_quality_score = compute_listing_quality_score()  # minimal data at this stage

        days_harbolnas = days_to_next_sale_event()
        seas_index = seasonal_index()
        timing_score = compute_timing_score(
            trend_score=trend_score,
            days_to_harbolnas=days_harbolnas,
            seasonal_index=seas_index,
        )

        market_health_score = compute_market_health_score(
            competition_score=competition_score,
            price_spread_idr=comp_data.get("price_spread_idr"),
            avg_price_idr=comp_data.get("price_avg_idr"),
        )

        # 8. Gate filter
        gates_result = evaluate_gates(
            net_margin_pct=margin_pct,
            sold_30d=listing["sold_30d"] or 0,
            trend_score=trend_score,
            trend_direction=trend_direction,
            competition_score=competition_score,
            supplier_price_idr=supplier_price_idr,
            sell_price_idr=listing["price_idr"],
        )

        # 9. Upsert product_scores
        await _upsert_scores(conn, {
            "listing_id": listing_id,
            "product_id": product_id,
            "best_supplier_id": best_supplier_id,
            "sell_price_idr": listing["price_idr"],
            "supplier_price_idr": supplier_price_idr,
            "platform_fee_idr": platform_fee_idr,
            "shipping_est_idr": shipping_est_idr,
            "gross_profit_idr": gross_profit_idr,
            "margin_pct": margin_pct,
            "margin_score": margin_score,
            "sellability_score": sellability_score,
            "trend_score": trend_score,
            "competition_score": competition_score,
            "opportunity_score": opportunity_score,
            "supplier_risk_score": supplier_risk_score,
            "quality_score": quality_score,
            "listing_quality_score": listing_quality_score,
            "timing_score": timing_score,
            "market_health_score": market_health_score,
            "gate_passed": gates_result["passed"],
            "gates_failed": gates_result["failed_gates"],
        })

        logger.info(
            f"[Scorer] {listing_id[:8]}... "
            f"opp={opportunity_score:.1f} margin={margin_pct:.1f}% "
            f"sell={sellability_score:.1f} trend={trend_score:.1f} "
            f"comp={competition_score:.1f} gate={'✅' if gates_result['passed'] else '❌'}"
        )

        return {
            "listing_id": listing_id,
            "opportunity_score": opportunity_score,
            "margin_pct": margin_pct,
            "margin_score": margin_score,
            "sellability_score": sellability_score,
            "trend_score": trend_score,
            "competition_score": competition_score,
            "gate_passed": gates_result["passed"],
            "gates_failed": gates_result["failed_gates"],
        }

    finally:
        await conn.close()


# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------

async def _upsert_scores(conn: asyncpg.Connection, data: dict):
    """Insert or update the product_scores row for a listing."""
    await conn.execute("""
        INSERT INTO product_scores (
            listing_id, product_id, best_supplier_id,
            sell_price_idr, supplier_price_idr, platform_fee_idr,
            shipping_est_idr, gross_profit_idr, margin_pct,
            margin_score, sellability_score, trend_score,
            competition_score, opportunity_score,
            supplier_risk_score, quality_score, listing_quality_score,
            timing_score, market_health_score,
            gate_passed, gates_failed,
            score_version, computed_at
        ) VALUES (
            $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,
            $15,$16,$17,$18,$19,$20,$21,'v1',NOW()
        )
        ON CONFLICT (listing_id) DO UPDATE SET
            best_supplier_id     = EXCLUDED.best_supplier_id,
            sell_price_idr       = EXCLUDED.sell_price_idr,
            supplier_price_idr   = EXCLUDED.supplier_price_idr,
            platform_fee_idr     = EXCLUDED.platform_fee_idr,
            shipping_est_idr     = EXCLUDED.shipping_est_idr,
            gross_profit_idr     = EXCLUDED.gross_profit_idr,
            margin_pct           = EXCLUDED.margin_pct,
            margin_score         = EXCLUDED.margin_score,
            sellability_score    = EXCLUDED.sellability_score,
            trend_score          = EXCLUDED.trend_score,
            competition_score    = EXCLUDED.competition_score,
            opportunity_score    = EXCLUDED.opportunity_score,
            supplier_risk_score  = EXCLUDED.supplier_risk_score,
            quality_score        = EXCLUDED.quality_score,
            listing_quality_score= EXCLUDED.listing_quality_score,
            timing_score         = EXCLUDED.timing_score,
            market_health_score  = EXCLUDED.market_health_score,
            gate_passed          = EXCLUDED.gate_passed,
            gates_failed         = EXCLUDED.gates_failed,
            score_version        = 'v1',
            computed_at          = NOW()
    """,
    data["listing_id"], data["product_id"], data["best_supplier_id"],
    data["sell_price_idr"], data["supplier_price_idr"], data["platform_fee_idr"],
    data["shipping_est_idr"], data["gross_profit_idr"], data["margin_pct"],
    data["margin_score"], data["sellability_score"], data["trend_score"],
    data["competition_score"], data["opportunity_score"],
    data["supplier_risk_score"], data["quality_score"], data["listing_quality_score"],
    data["timing_score"], data["market_health_score"],
    data["gate_passed"], data["gates_failed"],
    )


async def _compute_sold_growth(conn: asyncpg.Connection, listing_id: str) -> float:
    """
    Compute WoW sold growth %: (sold_7d - prev_sold_7d) / prev_sold_7d * 100.
    Uses price_history sold_count deltas. Returns 0 if insufficient data.
    """
    rows = await conn.fetch("""
        SELECT sold_count, recorded_at
        FROM price_history
        WHERE listing_id = $1
          AND recorded_at >= NOW() - INTERVAL '14 days'
          AND sold_count IS NOT NULL
        ORDER BY recorded_at DESC
        LIMIT 14
    """, listing_id)

    if len(rows) < 2:
        return 0.0

    # Most recent week vs prior week
    recent = [r["sold_count"] for r in rows[:7]]
    prior = [r["sold_count"] for r in rows[7:]]

    if not prior or sum(prior) == 0:
        return 0.0

    recent_avg = sum(recent) / len(recent)
    prior_avg = sum(prior) / len(prior)
    return ((recent_avg - prior_avg) / prior_avg) * 100.0


def _extract_search_keyword(title: str) -> str:
    """
    Extract a short keyword from a product title for trend lookup.
    Takes first 2-3 meaningful words.
    """
    stop_words = {"dengan", "dan", "untuk", "dari", "atau", "yang", "ke", "di", "the", "and", "for", "with"}
    words = [w for w in title.lower().split() if w not in stop_words and len(w) > 2]
    return " ".join(words[:3]) if words else title[:30]
