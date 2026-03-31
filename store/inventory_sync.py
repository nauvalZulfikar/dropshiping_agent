"""
Inventory sync — check supplier stock every 2 hours.
Deactivates listings when stock runs out, sends WA alert for critical stock.
"""
import asyncio

from core.celery_app import celery_app
from core.config import SUPPLIER_WA_PHONE
from core.db import execute, fetch
from core.logger import logger
from core.whatsapp import send_stock_alert


async def sync_product_stock(product_id: int) -> dict:
    row = await fetch(
        """
        SELECT p.id, p.name, p.stock, p.is_active, p.supplier_id,
               s.name as supplier_name, s.wa_phone as supplier_phone
        FROM products p
        LEFT JOIN suppliers s ON s.id = p.supplier_id
        WHERE p.id = $1
        """,
        product_id,
    )
    if not row:
        return {"product_id": product_id, "error": "not_found"}

    product = dict(row[0])
    stock = product["stock"]
    action = "none"

    # Deactivate if stock = 0
    if stock <= 0 and product["is_active"]:
        await execute(
            "UPDATE products SET is_active = FALSE, updated_at = NOW() WHERE id = $1",
            product_id,
        )
        action = "deactivated"
        logger.warning("product_deactivated_no_stock", product_id=product_id, name=product["name"])

    # Alert if stock critical (≤ 5)
    if 0 < stock <= 5 and SUPPLIER_WA_PHONE:
        await send_stock_alert(
            phone=SUPPLIER_WA_PHONE,
            product_name=product["name"],
            stock=stock,
            supplier_name=product["supplier_name"] or "Unknown",
        )
        action = "alert_sent"
        logger.info("stock_alert_sent", product_id=product_id, stock=stock)

    return {
        "product_id": product_id,
        "name": product["name"],
        "stock": stock,
        "action": action,
    }


async def decrement_stock(product_id: int, quantity: int = 1) -> int:
    new_stock = await execute(
        "UPDATE products SET stock = stock - $1, updated_at = NOW() WHERE id = $2 AND stock >= $1 RETURNING stock",
        quantity, product_id,
    )
    if not new_stock:
        logger.error("stock_decrement_failed", product_id=product_id, quantity=quantity)
        return -1

    logger.info("stock_decremented", product_id=product_id, quantity=quantity)
    return int(new_stock.split()[-1]) if isinstance(new_stock, str) else 0


@celery_app.task(name="store.inventory_sync.sync_all_inventory")
def sync_all_inventory():
    async def _run():
        products = await fetch("SELECT id FROM products WHERE is_active = TRUE")
        results = []
        for p in products:
            result = await sync_product_stock(p["id"])
            results.append(result)

        deactivated = sum(1 for r in results if r.get("action") == "deactivated")
        alerted = sum(1 for r in results if r.get("action") == "alert_sent")

        logger.info(
            "inventory_sync_complete",
            total=len(results), deactivated=deactivated, alerted=alerted,
        )

        return {
            "total_checked": len(results),
            "deactivated": deactivated,
            "alerts_sent": alerted,
        }

    return asyncio.run(_run())
