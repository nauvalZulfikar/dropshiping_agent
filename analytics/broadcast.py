"""
WhatsApp broadcast campaign via Fonnte.
Send targeted messages to customer segments.
"""
import asyncio
from typing import Optional

from core.celery_app import celery_app
from core.db import fetch
from core.logger import logger
from core.whatsapp import send_whatsapp


async def get_segment_phones(segment: str) -> list[str]:
    rows = await fetch(
        """
        SELECT DISTINCT customer_phone FROM customer_segments
        WHERE segment = $1
          AND customer_phone IS NOT NULL
          AND customer_phone != ''
        ORDER BY customer_phone
        """,
        segment,
    )
    return [r["customer_phone"] for r in rows]


async def broadcast_to_segment(
    segment: str,
    message: str,
    image_url: Optional[str] = None,
    delay_seconds: float = 2.0,
) -> dict:
    phones = await get_segment_phones(segment)

    if not phones:
        logger.warning("broadcast_no_recipients", segment=segment)
        return {"segment": segment, "sent": 0, "failed": 0, "error": "no_recipients"}

    sent = 0
    failed = 0

    for phone in phones:
        try:
            result = await send_whatsapp(phone, message, image_url)
            if result.get("status"):
                sent += 1
            else:
                failed += 1
        except Exception as e:
            logger.error("broadcast_send_failed", phone=phone[:6] + "****", error=str(e))
            failed += 1

        await asyncio.sleep(delay_seconds)

    logger.info(
        "broadcast_complete",
        segment=segment, total=len(phones), sent=sent, failed=failed,
    )

    return {"segment": segment, "total": len(phones), "sent": sent, "failed": failed}


async def broadcast_promo(
    message: str,
    segments: Optional[list[str]] = None,
    image_url: Optional[str] = None,
) -> list[dict]:
    if segments is None:
        segments = ["champions", "loyal", "potential"]

    results = []
    for segment in segments:
        result = await broadcast_to_segment(segment, message, image_url)
        results.append(result)

    return results


@celery_app.task(name="analytics.broadcast.send_broadcast")
def send_broadcast(message: str, segments: Optional[list[str]] = None, image_url: Optional[str] = None):
    return asyncio.run(broadcast_promo(message, segments, image_url))
