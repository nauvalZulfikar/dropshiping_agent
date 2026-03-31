"""
Niche scoring engine + decision logic.
Scores niches based on EPC, CVR, AOV, clicks, and trend.
Sends WA alert when a niche is ready to flip to dropship.
"""
from datetime import date, timedelta

from core.celery_app import celery_app
from core.config import SUPPLIER_WA_PHONE
from core.db import execute, fetch
from core.logger import logger
from core.whatsapp import send_niche_flip_alert


def calculate_score(
    epc: float,
    cvr: float,
    aov: int,
    clicks: int,
    trend: str,
) -> tuple[float, str]:
    score = 0.0

    if epc >= 5000:
        score += 35
    elif epc >= 2000:
        score += 25
    elif epc >= 800:
        score += 15

    if cvr >= 0.05:
        score += 25
    elif cvr >= 0.025:
        score += 18
    elif cvr >= 0.01:
        score += 10

    if aov >= 300000:
        score += 20
    elif aov >= 150000:
        score += 14

    if clicks >= 2000:
        score += 10
    elif clicks >= 500:
        score += 7

    if trend == "up":
        score += 10

    if score >= 65 and clicks >= 200:
        decision = "flip_to_dropship"
    elif score >= 45 and clicks >= 100:
        decision = "scale_affiliate"
    elif score >= 25:
        decision = "optimize"
    else:
        decision = "abandon"

    return score, decision


def _detect_trend(daily_values: list[float]) -> str:
    if len(daily_values) < 7:
        return "flat"

    first_half = sum(daily_values[:len(daily_values)//2]) / max(len(daily_values)//2, 1)
    second_half = sum(daily_values[len(daily_values)//2:]) / max(len(daily_values) - len(daily_values)//2, 1)

    if second_half > first_half * 1.15:
        return "up"
    elif second_half < first_half * 0.85:
        return "down"
    return "flat"


async def score_niche(niche: str) -> dict:
    end = date.today()
    start = end - timedelta(days=30)

    rows = await fetch(
        """
        SELECT ap.date, SUM(ap.clicks) as clicks, SUM(ap.conversions) as conversions,
               SUM(ap.gmv_idr) as gmv, SUM(ap.commission_idr) as commission,
               AVG(ap.avg_order_value) as aov
        FROM affiliate_performance ap
        JOIN affiliate_links al ON al.link_id = ap.link_id
        WHERE al.niche = $1 AND ap.date BETWEEN $2 AND $3
        GROUP BY ap.date
        ORDER BY ap.date
        """,
        niche, start, end,
    )

    if not rows:
        return {"niche": niche, "score": 0, "decision": "abandon", "error": "no_data"}

    total_clicks = sum(r["clicks"] for r in rows)
    total_conversions = sum(r["conversions"] for r in rows)
    total_commission = sum(r["commission"] for r in rows)
    avg_aov = int(sum(r["aov"] for r in rows) / len(rows)) if rows else 0

    epc = (total_commission / total_clicks) if total_clicks > 0 else 0
    cvr = (total_conversions / total_clicks) if total_clicks > 0 else 0

    daily_epcs = []
    for r in rows:
        if r["clicks"] > 0:
            daily_epcs.append(r["commission"] / r["clicks"])

    trend = _detect_trend(daily_epcs)
    score, decision = calculate_score(epc, cvr, avg_aov, total_clicks, trend)

    await execute(
        "INSERT INTO niche_scores (niche, epc, cvr, total_clicks, avg_order_value, trend, score, decision) "
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        niche, epc, cvr, total_clicks, avg_aov, trend, score, decision,
    )

    result = {
        "niche": niche,
        "epc": round(epc, 2),
        "cvr": round(cvr, 4),
        "total_clicks": total_clicks,
        "avg_order_value": avg_aov,
        "trend": trend,
        "score": score,
        "decision": decision,
    }

    if decision == "flip_to_dropship" and SUPPLIER_WA_PHONE:
        await send_niche_flip_alert(
            phone=SUPPLIER_WA_PHONE,
            niche=niche,
            score=score,
            epc=epc,
            cvr=cvr,
            aov=avg_aov,
            clicks=total_clicks,
        )
        logger.info("niche_flip_alert_sent", niche=niche, score=score)

    logger.info("niche_scored", **result)
    return result


@celery_app.task(name="affiliate.niche_scorer.score_all_niches")
def score_all_niches():
    import asyncio

    async def _run():
        niches_rows = await fetch(
            "SELECT DISTINCT niche FROM affiliate_links WHERE niche IS NOT NULL AND niche != ''"
        )
        results = []
        for row in niches_rows:
            result = await score_niche(row["niche"])
            results.append(result)
        return results

    return asyncio.run(_run())
