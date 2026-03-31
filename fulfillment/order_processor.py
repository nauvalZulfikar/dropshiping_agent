"""
Order processor — Celery task that processes new orders.
1. Fetch order detail from platform
2. Match to product in DB
3. Save order to DB
4. Send WA to supplier
5. Decrement stock
"""
import asyncio

from core.celery_app import celery_app
from core.db import execute, fetchrow
from core.logger import logger
from core.whatsapp import send_order_to_supplier
from store.inventory_sync import sync_product_stock


async def _process_order(platform: str, platform_order_id: str) -> dict:
    # Get platform adapter
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
        logger.error("unknown_platform", platform=platform)
        return {"error": f"Unknown platform: {platform}"}

    # Fetch orders from platform
    orders = await adapter.get_orders(status="new")
    target = None
    for o in orders:
        if o.platform_order_id == platform_order_id:
            target = o
            break

    if not target:
        logger.warning("order_not_found_on_platform", platform=platform, order_id=platform_order_id)
        return {"error": "Order not found on platform"}

    # Match product by SKU
    product = await fetchrow(
        "SELECT id, name, supplier_id, cogs_idr, current_price FROM products WHERE sku = $1",
        target.product_sku,
    )

    if not product:
        logger.warning("product_not_found", sku=target.product_sku)
        return {"error": f"Product not found for SKU: {target.product_sku}"}

    product = dict(product)

    # Get supplier info
    supplier = await fetchrow(
        "SELECT id, name, wa_phone FROM suppliers WHERE id = $1",
        product["supplier_id"],
    )
    supplier = dict(supplier) if supplier else {"id": None, "name": "Unknown", "wa_phone": ""}

    # Calculate financials
    platform_fee = int(target.sale_price_idr * 0.08)
    net_profit = target.sale_price_idr - (product["cogs_idr"] * target.quantity) - platform_fee

    # Save order to DB
    order_id = await execute(
        """
        INSERT INTO orders (
            platform, platform_order_id, product_id, supplier_id,
            buyer_name, buyer_phone, shipping_address, city, postal_code,
            courier, courier_service, quantity,
            sale_price_idr, cogs_idr, platform_fee_idr, net_profit_idr,
            status
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, 'new')
        ON CONFLICT (platform_order_id) DO NOTHING
        RETURNING id
        """,
        platform, platform_order_id, product["id"], supplier["id"],
        target.buyer_name, target.buyer_phone, target.shipping_address,
        target.city, target.postal_code, target.courier, target.courier_service,
        target.quantity, target.sale_price_idr,
        product["cogs_idr"] * target.quantity, platform_fee, net_profit,
    )

    if not order_id:
        logger.info("order_already_exists", platform_order_id=platform_order_id)
        return {"status": "duplicate"}

    # Send WA to supplier
    if supplier["wa_phone"]:
        await send_order_to_supplier(
            phone=supplier["wa_phone"],
            order_id=int(order_id.split()[-1]) if isinstance(order_id, str) else 0,
            product_name=product["name"],
            variant="",
            quantity=target.quantity,
            buyer_name=target.buyer_name,
            buyer_phone=target.buyer_phone,
            shipping_address=target.shipping_address,
            city=target.city,
            postal_code=target.postal_code,
            courier=target.courier,
            courier_service=target.courier_service,
        )

        await execute(
            "UPDATE orders SET status = 'sent_to_supplier', sent_to_supplier_at = NOW() WHERE platform_order_id = $1",
            platform_order_id,
        )

    # Decrement stock + check critical
    await execute(
        "UPDATE products SET stock = stock - $1, updated_at = NOW() WHERE id = $2 AND stock >= $1",
        target.quantity, product["id"],
    )
    await sync_product_stock(product["id"])

    logger.info(
        "order_processed",
        platform=platform, order_id=platform_order_id,
        product=product["name"], net_profit=net_profit,
    )

    return {
        "status": "processed",
        "platform_order_id": platform_order_id,
        "product": product["name"],
        "net_profit": net_profit,
    }


@celery_app.task(name="fulfillment.order_processor.process_new_order", bind=True, max_retries=3)
def process_new_order(self, platform: str, platform_order_id: str):
    try:
        return asyncio.run(_process_order(platform, platform_order_id))
    except Exception as exc:
        logger.error("order_processing_failed", platform=platform, order_id=platform_order_id, error=str(exc))
        self.retry(exc=exc, countdown=60)
