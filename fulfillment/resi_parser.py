"""
Resi parser — extract tracking numbers from supplier WhatsApp replies.
Supports JNE, J&T, SiCepat, AnterAja formats.
"""
import re

from core.db import execute, fetch, fetchrow
from core.logger import logger

# Resi patterns per courier
RESI_PATTERNS = [
    # JNE: 12-15 digit alphanumeric
    (r"\b([A-Z]{4}\d{8,12})\b", "JNE"),
    # J&T: JP + 12 digits or JD + digits
    (r"\b(JP\d{12,13})\b", "J&T"),
    (r"\b(JD\d{10,12})\b", "J&T"),
    # SiCepat: 12 digit numeric starting with 00
    (r"\b(00\d{10,13})\b", "SiCepat"),
    # AnterAja: 10-15 digit alphanumeric
    (r"\b(\d{10,15})\b", "AnterAja"),
    # Generic: any 10-20 character alphanumeric that looks like tracking
    (r"\b([A-Z0-9]{10,20})\b", "unknown"),
]


def extract_resi(message: str) -> list[dict]:
    """Extract potential tracking numbers from a message."""
    results = []
    message_upper = message.upper().strip()

    for pattern, courier in RESI_PATTERNS:
        matches = re.findall(pattern, message_upper)
        for match in matches:
            if len(match) >= 10 and match not in [r["resi"] for r in results]:
                results.append({"resi": match, "courier": courier})

    return results


async def parse_and_update_resi(sender_phone: str, message: str) -> dict:
    """Parse resi from supplier WA reply and update the corresponding order."""
    # Find supplier by phone
    supplier = await fetchrow(
        "SELECT id, name FROM suppliers WHERE wa_phone = $1",
        sender_phone,
    )

    if not supplier:
        return {"resi_found": False, "reason": "unknown_sender"}

    supplier = dict(supplier)

    # Find pending orders for this supplier
    pending_orders = await fetch(
        """
        SELECT id, platform_order_id, platform
        FROM orders
        WHERE supplier_id = $1 AND status = 'sent_to_supplier' AND resi IS NULL
        ORDER BY sent_to_supplier_at ASC
        """,
        supplier["id"],
    )

    if not pending_orders:
        return {"resi_found": False, "reason": "no_pending_orders"}

    # Extract resi from message
    resi_candidates = extract_resi(message)

    if not resi_candidates:
        return {"resi_found": False, "reason": "no_resi_in_message"}

    # Match resi to oldest pending order (FIFO)
    resi = resi_candidates[0]["resi"]
    order = dict(pending_orders[0])

    await execute(
        "UPDATE orders SET resi = $1, status = 'shipped', shipped_at = NOW(), updated_at = NOW() WHERE id = $2",
        resi, order["id"],
    )

    logger.info(
        "resi_parsed_and_updated",
        order_id=order["id"],
        platform_order_id=order["platform_order_id"],
        resi=resi,
        supplier=supplier["name"],
    )

    # Queue tracking update to platform
    from fulfillment.tracking_updater import update_platform_tracking
    update_platform_tracking.delay(
        order["platform"],
        order["platform_order_id"],
        resi,
        resi_candidates[0]["courier"],
    )

    return {
        "resi_found": True,
        "resi": resi,
        "order_id": order["id"],
        "platform_order_id": order["platform_order_id"],
    }
