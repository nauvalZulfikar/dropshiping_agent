"""
5-Gate filter from DROPSHIP_AGENTS.md §13.

Before displaying a product as "recommended", it must pass ALL 5 gates.
Products failing any gate are hidden from the main feed
(accessible via "All Products" with filter removed).

Gate 1 — Margin:      net_margin_pct >= 20%
Gate 2 — Demand:      sold_30d >= 300 units
Gate 3 — Trend:       trend_score >= 40 AND not declining
Gate 4 — Competition: competition_score >= 35 (≤ 100 sellers)
Gate 5 — Supplier:    supplier_price <= 40% of sell_price
"""
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# Gate thresholds — match AGENTS.md §13 exactly
GATE_1_MIN_MARGIN_PCT = 20.0
GATE_2_MIN_SOLD_30D = 300
GATE_3_MIN_TREND_SCORE = 40.0
GATE_4_MIN_COMPETITION_SCORE = 35.0
GATE_5_MAX_SUPPLIER_RATIO = 0.40  # supplier_price / sell_price


def passes_all_gates(
    net_margin_pct: float,
    sold_30d: int,
    trend_score: float,
    trend_direction: str,
    competition_score: float,
    supplier_price_idr: int,
    sell_price_idr: int,
) -> bool:
    """
    Returns True only if all 5 gates pass.
    Exact implementation of §13 passes_all_gates().
    """
    return evaluate_gates(
        net_margin_pct=net_margin_pct,
        sold_30d=sold_30d,
        trend_score=trend_score,
        trend_direction=trend_direction,
        competition_score=competition_score,
        supplier_price_idr=supplier_price_idr,
        sell_price_idr=sell_price_idr,
    )["passed"]


def evaluate_gates(
    net_margin_pct: float,
    sold_30d: int,
    trend_score: float,
    trend_direction: str,
    competition_score: float,
    supplier_price_idr: int,
    sell_price_idr: int,
) -> dict:
    """
    Evaluate all 5 gates and return detailed result.

    Returns:
        {
            "passed": bool,
            "failed_gates": list[str],   # names of failed gates
            "gate_results": dict,        # per-gate bool
        }
    """
    gate1 = net_margin_pct >= GATE_1_MIN_MARGIN_PCT
    gate2 = sold_30d >= GATE_2_MIN_SOLD_30D
    gate3 = trend_score >= GATE_3_MIN_TREND_SCORE and trend_direction != "declining"
    gate4 = competition_score >= GATE_4_MIN_COMPETITION_SCORE

    if sell_price_idr and sell_price_idr > 0 and supplier_price_idr > 0:
        supplier_ratio = supplier_price_idr / sell_price_idr
        gate5 = supplier_ratio <= GATE_5_MAX_SUPPLIER_RATIO
    else:
        gate5 = False  # no supplier = can't pass gate 5

    gate_results = {
        "gate1_margin": gate1,
        "gate2_demand": gate2,
        "gate3_trend": gate3,
        "gate4_competition": gate4,
        "gate5_supplier": gate5,
    }

    gate_names = {
        "gate1_margin": "margin",
        "gate2_demand": "demand",
        "gate3_trend": "trend",
        "gate4_competition": "competition",
        "gate5_supplier": "supplier",
    }

    failed_gates = [gate_names[k] for k, v in gate_results.items() if not v]
    passed = len(failed_gates) == 0

    return {
        "passed": passed,
        "failed_gates": failed_gates,
        "gate_results": gate_results,
    }


def gate_fail_reason(gate_name: str) -> str:
    """Human-readable reason for each gate failure (for UI display)."""
    reasons = {
        "margin":      "Net margin < 20% — not profitable after fees",
        "demand":      "Sold < 300/month — market too small or product dying",
        "trend":       "Trend score < 40 or declining — losing search interest",
        "competition": "Too many sellers (> 100) — too crowded to enter",
        "supplier":    "Supplier price > 40% of sell price — insufficient markup",
    }
    return reasons.get(gate_name, "Unknown gate failure")
