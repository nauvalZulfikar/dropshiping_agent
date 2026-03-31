"""
Affiliate data scheduler.
Pulls data from all affiliate platforms every 6 hours via Celery beat.
"""
import asyncio
from datetime import date, timedelta

from core.celery_app import celery_app
from core.db import execute
from core.logger import logger


async def _pull_involve_asia():
    from affiliate.involve_asia import get_conversions, get_clicks

    end = date.today()
    start = end - timedelta(days=7)

    conversions = await get_conversions(start, end)
    clicks = await get_clicks(start, end)

    for conv in conversions:
        sub_id = conv.sub_id or ""
        if not sub_id:
            continue

        await execute(
            """
            INSERT INTO affiliate_performance (link_id, date, conversions, gmv_idr, commission_idr, avg_order_value)
            VALUES ($1, $2, 1, $3, $4, $3)
            ON CONFLICT (link_id, date) DO UPDATE
            SET conversions = affiliate_performance.conversions + 1,
                gmv_idr = affiliate_performance.gmv_idr + $3,
                commission_idr = affiliate_performance.commission_idr + $4,
                updated_at = NOW()
            """,
            sub_id, conv.conversion_date, conv.sale_amount, conv.commission,
        )

    for click in clicks:
        sub_id = click.sub_id or ""
        if not sub_id:
            continue

        await execute(
            """
            INSERT INTO affiliate_performance (link_id, date, clicks)
            VALUES ($1, $2, $3)
            ON CONFLICT (link_id, date) DO UPDATE
            SET clicks = $3,
                updated_at = NOW()
            """,
            sub_id, click.date, click.clicks,
        )

    logger.info("involve_asia_synced", conversions=len(conversions), clicks=len(clicks))


async def _pull_shopee_affiliate():
    from affiliate.shopee_affiliate import get_performance

    records = await get_performance()

    for rec in records:
        await execute(
            """
            INSERT INTO affiliate_performance (link_id, date, clicks, conversions, gmv_idr, commission_idr)
            VALUES ('shopee_agg', $1, $2, $3, $4, $5)
            ON CONFLICT (link_id, date) DO UPDATE
            SET clicks = $2, conversions = $3, gmv_idr = $4, commission_idr = $5,
                updated_at = NOW()
            """,
            rec.date, rec.clicks, rec.conversions, rec.gmv_idr, rec.commission_idr,
        )

    logger.info("shopee_affiliate_synced", records=len(records))


async def _pull_all():
    errors = []

    try:
        await _pull_involve_asia()
    except Exception as e:
        logger.error("involve_asia_sync_failed", error=str(e))
        errors.append(f"involve_asia: {e}")

    try:
        await _pull_shopee_affiliate()
    except Exception as e:
        logger.error("shopee_affiliate_sync_failed", error=str(e))
        errors.append(f"shopee: {e}")

    return {"errors": errors, "status": "done" if not errors else "partial"}


@celery_app.task(name="affiliate.scheduler.pull_all_affiliate_data")
def pull_all_affiliate_data():
    return asyncio.run(_pull_all())
