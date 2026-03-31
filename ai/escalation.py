"""
Escalation logic for CS bot.
Triggers human intervention for risky situations.
"""
from core.config import SUPPLIER_WA_PHONE
from core.db import fetch, fetchval
from core.logger import logger
from core.whatsapp import send_whatsapp

RISK_KEYWORDS = ["tipu", "palsu", "lapor", "somasi", "refund paksa", "penipuan", "scam", "polisi"]
HIGH_VALUE_THRESHOLD = 500000  # Rp 500.000
REPEAT_COMPLAINT_THRESHOLD = 2
REPEAT_COMPLAINT_DAYS = 7


async def should_escalate(phone: str, message: str) -> dict:
    message_lower = message.lower()

    # 1. Risk keywords
    for keyword in RISK_KEYWORDS:
        if keyword in message_lower:
            return {"should_escalate": True, "reason": f"risk_keyword: {keyword}"}

    # 2. High value order
    recent_order = await fetchval(
        """
        SELECT sale_price_idr FROM orders
        WHERE buyer_phone = $1
        ORDER BY created_at DESC LIMIT 1
        """,
        phone,
    )
    if recent_order and int(recent_order) > HIGH_VALUE_THRESHOLD:
        # Only escalate high-value if message contains complaint keywords
        complaint_words = ["kecewa", "komplain", "masalah", "rusak", "salah", "retur", "kembalikan"]
        if any(w in message_lower for w in complaint_words):
            return {"should_escalate": True, "reason": f"high_value_complaint: Rp {recent_order:,}"}

    # 3. Repeat complaints (>2 in 7 days)
    complaint_count = await fetchval(
        """
        SELECT COUNT(*) FROM conversations
        WHERE customer_phone = $1
          AND role = 'user'
          AND escalated = TRUE
          AND created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
        """,
        phone,
    )
    if complaint_count and int(complaint_count) >= REPEAT_COMPLAINT_THRESHOLD:
        return {"should_escalate": True, "reason": f"repeat_complaints: {complaint_count} in 7 days"}

    # 4. Return request after 2x24h
    retur_words = ["retur", "kembalikan", "tukar", "return"]
    if any(w in message_lower for w in retur_words):
        delivered_order = await fetchval(
            """
            SELECT id FROM orders
            WHERE buyer_phone = $1
              AND status = 'delivered'
              AND shipped_at < CURRENT_TIMESTAMP - INTERVAL '48 hours'
            ORDER BY shipped_at DESC LIMIT 1
            """,
            phone,
        )
        if delivered_order:
            return {"should_escalate": True, "reason": "late_return_request"}

    return {"should_escalate": False, "reason": None}


async def handle_escalation(phone: str, platform: str, message: str, reason: str) -> None:
    if not SUPPLIER_WA_PHONE:
        logger.warning("escalation_no_admin_phone")
        return

    # Get recent conversation context
    recent = await fetch(
        """
        SELECT role, message, created_at FROM conversations
        WHERE customer_phone = $1
        ORDER BY created_at DESC LIMIT 5
        """,
        phone,
    )

    context_lines = []
    for r in reversed(recent):
        role = "Customer" if r["role"] == "user" else "Bot"
        context_lines.append(f"{role}: {r['message'][:100]}")
    context = "\n".join(context_lines)

    masked_phone = phone[:4] + "****" + phone[-4:] if len(phone) > 8 else phone

    alert = (
        f"ESKALASI CS BOT\n\n"
        f"Customer: {masked_phone}\n"
        f"Platform: {platform}\n"
        f"Alasan: {reason}\n\n"
        f"Konteks percakapan:\n{context}\n\n"
        f"Pesan terakhir:\n{message[:200]}"
    )

    await send_whatsapp(SUPPLIER_WA_PHONE, alert)
    logger.info("escalation_alert_sent", phone=masked_phone, reason=reason)
