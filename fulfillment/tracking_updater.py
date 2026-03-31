"""
Tracking updater — push resi to marketplace platform after supplier confirms shipping.
"""
import asyncio

from core.celery_app import celery_app
from core.db import execute
from core.logger import logger


async def _update_tracking(platform: str, platform_order_id: str, resi: str, courier: str) -> dict:
    try:
        if platform == "shopee":
            from store.platforms.shopee import ShopeeAdapter
            adapter = ShopeeAdapter()
        elif platform == "tokopedia":
            from core.config import SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY, SHOPEE_SHOP_ID
            from store.platforms.tokopedia import TokopediaAdapter
            adapter = TokopediaAdapter(SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY, SHOPEE_SHOP_ID)
        elif platform == "tiktok":
            from store.platforms.tiktok_shop import TikTokAdapter
            adapter = TikTokAdapter("", "", "", "")
        else:
            return {"error": f"Unknown platform: {platform}"}

        result = await adapter.update_tracking(platform_order_id, resi, courier)

        await execute(
            "UPDATE orders SET status = 'shipped', shipped_at = NOW(), updated_at = NOW() WHERE platform_order_id = $1",
            platform_order_id,
        )

        logger.info(
            "tracking_pushed_to_platform",
            platform=platform, order_id=platform_order_id, resi=resi,
        )

        return {"status": "updated", "platform": platform, "resi": resi}

    except Exception as e:
        logger.error(
            "tracking_push_failed",
            platform=platform, order_id=platform_order_id, error=str(e),
        )
        return {"error": str(e)}


@celery_app.task(name="fulfillment.tracking_updater.update_platform_tracking", bind=True, max_retries=3)
def update_platform_tracking(self, platform: str, platform_order_id: str, resi: str, courier: str):
    try:
        return asyncio.run(_update_tracking(platform, platform_order_id, resi, courier))
    except Exception as exc:
        logger.error("tracking_update_retry", platform=platform, order_id=platform_order_id, error=str(exc))
        self.retry(exc=exc, countdown=120)
