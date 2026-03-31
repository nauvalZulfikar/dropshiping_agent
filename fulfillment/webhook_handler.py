"""
Webhook handler — receives new orders from marketplace platforms.
Parses order data and queues processing via Celery.
"""
from fastapi import APIRouter, Request, HTTPException

from core.db import execute, fetchrow
from core.logger import logger

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/shopee/order")
async def shopee_order_webhook(request: Request):
    body = await request.json()
    event = body.get("code")

    if event != 3:  # 3 = order status update
        return {"status": "ignored", "event": event}

    order_sn = body.get("data", {}).get("ordersn", "")
    if not order_sn:
        raise HTTPException(400, "Missing order_sn")

    existing = await fetchrow(
        "SELECT id FROM orders WHERE platform_order_id = $1", order_sn
    )
    if existing:
        logger.info("shopee_webhook_duplicate", order_sn=order_sn)
        return {"status": "duplicate"}

    # Queue order processing
    from fulfillment.order_processor import process_new_order
    process_new_order.delay("shopee", order_sn)

    logger.info("shopee_webhook_received", order_sn=order_sn)
    return {"status": "queued", "order_sn": order_sn}


@router.post("/tokopedia/order")
async def tokopedia_order_webhook(request: Request):
    body = await request.json()
    order_id = str(body.get("order_id", ""))

    if not order_id:
        raise HTTPException(400, "Missing order_id")

    existing = await fetchrow(
        "SELECT id FROM orders WHERE platform_order_id = $1", order_id
    )
    if existing:
        logger.info("tokopedia_webhook_duplicate", order_id=order_id)
        return {"status": "duplicate"}

    from fulfillment.order_processor import process_new_order
    process_new_order.delay("tokopedia", order_id)

    logger.info("tokopedia_webhook_received", order_id=order_id)
    return {"status": "queued", "order_id": order_id}


@router.post("/tiktok/order")
async def tiktok_order_webhook(request: Request):
    body = await request.json()
    event_type = body.get("type")

    if event_type != 1:  # 1 = order creation
        return {"status": "ignored", "type": event_type}

    order_id = body.get("data", {}).get("order_id", "")
    if not order_id:
        raise HTTPException(400, "Missing order_id")

    existing = await fetchrow(
        "SELECT id FROM orders WHERE platform_order_id = $1", order_id
    )
    if existing:
        logger.info("tiktok_webhook_duplicate", order_id=order_id)
        return {"status": "duplicate"}

    from fulfillment.order_processor import process_new_order
    process_new_order.delay("tiktok", order_id)

    logger.info("tiktok_webhook_received", order_id=order_id)
    return {"status": "queued", "order_id": order_id}


@router.post("/fonnte/incoming")
async def fonnte_incoming_webhook(request: Request):
    """Handle incoming WhatsApp messages (supplier resi replies)."""
    body = await request.json()
    sender = body.get("sender", "")
    message = body.get("message", "")

    if not sender or not message:
        return {"status": "ignored"}

    # Check if this is a supplier replying with resi
    from fulfillment.resi_parser import parse_and_update_resi
    result = await parse_and_update_resi(sender, message)

    logger.info("wa_incoming", sender=sender, message_len=len(message), resi_found=result.get("resi_found", False))
    return {"status": "processed", **result}
