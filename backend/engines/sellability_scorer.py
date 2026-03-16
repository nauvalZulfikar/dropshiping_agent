"""
Sellability scorer engine.
Implements exact formulas from DROPSHIP_AGENTS.md §8.2.
All scores are 0-100.
"""
import math
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


# ------------------------------------------------------------------
# Main sellability score (0-100)
# Formula from AGENTS.md §8.2:
#   sold_score   = min(log10(sold_30d + 1) / log10(10001), 1) * 40
#   review_score = min(log10(review_count + 1) / log10(5001), 1) * 20
#   rating_score = (rating / 5.0) * 20
#   growth_score = min(max(sold_growth_pct, 0) / 100, 1) * 20
# ------------------------------------------------------------------

def compute_sellability(
    sold_30d: int,
    review_count: int,
    rating: Optional[float],
    sold_growth_pct: float = 0.0,
) -> float:
    """
    Compute sellability score (0-100) from demand signals.

    Args:
        sold_30d:        Units sold in last 30 days
        review_count:    Total number of reviews
        rating:          Product rating (0-5); None → treated as 0
        sold_growth_pct: % WoW growth in sold count; defaults to 0 if unknown
    """
    sold_score = min(
        _log10_safe(sold_30d + 1) / _log10_safe(10_001), 1.0
    ) * 40.0

    review_score = min(
        _log10_safe(review_count + 1) / _log10_safe(5_001), 1.0
    ) * 20.0

    rating_val = rating if rating is not None else 0.0
    rating_score = (rating_val / 5.0) * 20.0

    growth_score = min(max(sold_growth_pct, 0.0) / 100.0, 1.0) * 20.0

    total = sold_score + review_score + rating_score + growth_score
    return round(min(max(total, 0.0), 100.0), 2)


# ------------------------------------------------------------------
# Competition score (0-100)
# Scoring table from AGENTS.md §8.4
# ------------------------------------------------------------------

def compute_competition_score(seller_count: int) -> float:
    """
    Compute competition score (0-100) based on seller count.
    Higher score = less competition = better opportunity.

    Scoring table:
        < 3      → 95  (blue ocean)
        3-10     → 80
        10-30    → 60
        30-100   → 35
        100-500  → 15
        > 500    → 5   (red ocean)
    """
    if seller_count < 3:
        return 95.0
    if seller_count < 10:
        return 80.0
    if seller_count < 30:
        return 60.0
    if seller_count < 100:
        return 35.0
    if seller_count < 500:
        return 15.0
    return 5.0


# ------------------------------------------------------------------
# Supplier risk score (0-100, higher = safer supplier)
# Formula from AGENTS.md §8.5
# ------------------------------------------------------------------

def compute_supplier_risk_score(
    supplier_rating: Optional[float],
    supplier_orders: int = 0,
    shipping_days: Optional[int] = None,
    moq: int = 1,
) -> float:
    """
    Compute supplier reliability score (0-100).

    Components:
        rating_score  = (rating / 5.0) * 30
        volume_score  = min(log10(orders + 1) / log10(10001), 1) * 25
        shipping_score = max(0, (21 - days) / 21) * 25
        moq_score     = (1 if moq==1 else 0.7 if moq<=5 else 0.3 if moq<=20 else 0) * 20
    """
    rating_score = ((supplier_rating or 0.0) / 5.0) * 30.0

    volume_score = min(
        _log10_safe(supplier_orders + 1) / _log10_safe(10_001), 1.0
    ) * 25.0

    if shipping_days is not None:
        shipping_score = max(0.0, (21 - shipping_days) / 21.0) * 25.0
    else:
        shipping_score = 12.5  # neutral if unknown

    if moq == 1:
        moq_factor = 1.0
    elif moq <= 5:
        moq_factor = 0.7
    elif moq <= 20:
        moq_factor = 0.3
    else:
        moq_factor = 0.0
    moq_score = moq_factor * 20.0

    total = rating_score + volume_score + shipping_score + moq_score
    return round(min(max(total, 0.0), 100.0), 2)


# ------------------------------------------------------------------
# Product quality score (0-100)
# Formula from AGENTS.md §8.6
# ------------------------------------------------------------------

def compute_product_quality_score(
    avg_rating: Optional[float],
    review_count: int,
    review_recency_days: Optional[int] = None,
    negative_review_pct: float = 0.0,
) -> float:
    """
    Compute product quality score (0-100).

    Components:
        rating_score        = (avg_rating / 5.0) * 35
        review_volume_score = min(log10(review_count + 1) / log10(1001), 1) * 25
        recency_score       = max(0, (30 - recency_days) / 30) * 20
        negative_rate_score = max(0, 1 - neg_pct / 10) * 20
    """
    rating_score = ((avg_rating or 0.0) / 5.0) * 35.0

    review_volume_score = min(
        _log10_safe(review_count + 1) / _log10_safe(1_001), 1.0
    ) * 25.0

    if review_recency_days is not None:
        recency_score = max(0.0, (30 - review_recency_days) / 30.0) * 20.0
    else:
        recency_score = 10.0  # neutral if unknown

    negative_rate_score = max(0.0, 1.0 - negative_review_pct / 10.0) * 20.0

    total = rating_score + review_volume_score + recency_score + negative_rate_score
    return round(min(max(total, 0.0), 100.0), 2)


# ------------------------------------------------------------------
# Listing quality score (0-100)
# Formula from AGENTS.md §8.7
# ------------------------------------------------------------------

def compute_listing_quality_score(
    image_count: int = 0,
    description_length: int = 0,
    has_product_specs: bool = False,
    keyword_in_title_count: int = 0,
) -> float:
    """
    Compute listing quality score (0-100).

    Components:
        image_score = min(image_count / 5, 1) * 30
        title_score = (keyword_in_title_count / 3) * 25
        desc_score  = (1 if desc_len > 300 else desc_len / 300) * 25
        spec_score  = (1 if has_specs else 0) * 20
    """
    image_score = min(image_count / 5.0, 1.0) * 30.0

    title_score = min(keyword_in_title_count / 3.0, 1.0) * 25.0

    if description_length > 300:
        desc_factor = 1.0
    else:
        desc_factor = description_length / 300.0
    desc_score = desc_factor * 25.0

    spec_score = 20.0 if has_product_specs else 0.0

    total = image_score + title_score + desc_score + spec_score
    return round(min(max(total, 0.0), 100.0), 2)


# ------------------------------------------------------------------
# Timing score (0-100)
# Formula from AGENTS.md §8.8
# ------------------------------------------------------------------

def compute_timing_score(
    trend_score: float,
    days_to_harbolnas: int,
    seasonal_index: float = 1.0,
) -> float:
    """
    Compute timing score (0-100).
    timing_score = avg(trend_score, seasonal_index×50, harbolnas_proximity_score)
    """
    # Proximity to harbolnas: 0 days → 100, 30+ days → 0
    harbolnas_score = max(0.0, (30 - min(days_to_harbolnas, 30)) / 30.0) * 100.0

    seasonal_component = min(seasonal_index, 2.0) * 50.0

    timing = (trend_score + seasonal_component + harbolnas_score) / 3.0
    return round(min(max(timing, 0.0), 100.0), 2)


# ------------------------------------------------------------------
# Market health score (0-100)
# Formula from AGENTS.md §8.8
# ------------------------------------------------------------------

def compute_market_health_score(
    competition_score: float,
    price_spread_idr: Optional[int],
    avg_price_idr: Optional[int],
    review_velocity: float = 0.0,
) -> float:
    """
    Compute market health score (0-100).
    market_health = avg(competition_score, price_spread_normalized, review_velocity_score)
    """
    # Price spread normalized: lower spread → healthier market
    if price_spread_idr and avg_price_idr and avg_price_idr > 0:
        spread_ratio = price_spread_idr / avg_price_idr
        price_spread_norm = max(0.0, 100.0 - (spread_ratio * 50.0))
    else:
        price_spread_norm = 50.0  # neutral

    # Review velocity: reviews per day; cap at 10/day → 100
    review_velocity_score = min(review_velocity / 10.0, 1.0) * 100.0

    health = (competition_score + price_spread_norm + review_velocity_score) / 3.0
    return round(min(max(health, 0.0), 100.0), 2)


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _log10_safe(x: float) -> float:
    """log10 that never raises — returns 0 for x <= 0."""
    if x <= 0:
        return 0.0
    return math.log10(x)
