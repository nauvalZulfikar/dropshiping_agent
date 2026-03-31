"""
CS Bot — automated customer service via WhatsApp using Claude API.
Handles > 85% of queries. Escalates to human for risky cases.
"""
from typing import Optional

from anthropic import AsyncAnthropic

from core.config import ANTHROPIC_API_KEY
from core.db import execute, fetch
from core.logger import logger

client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

CS_SYSTEM_PROMPT = """Kamu adalah CS (customer service) toko online Indonesia yang ramah dan profesional.
Nama toko: [Toko Kita]

Aturan:
1. Jawab dalam bahasa Indonesia casual tapi sopan
2. Selalu jawab pertanyaan stok, harga, dan pengiriman dengan cepat
3. Jika customer marah/komplain, empati dulu baru tawarkan solusi
4. Jangan buat janji yang tidak bisa ditepati
5. Untuk pertanyaan di luar kapasitas (refund, retur, komplain berat), bilang akan diteruskan ke tim
6. Gunakan emoji secukupnya (1-2 per pesan)
7. Max 3 paragraf per jawaban, singkat dan jelas

Info standar:
- Pengiriman: 1-3 hari kerja (Jawa), 3-7 hari kerja (luar Jawa)
- COD tersedia di Shopee dan Tokopedia
- Retur: max 2x24 jam setelah barang diterima
- Jam operasional: 08:00-22:00 WIB"""


async def get_conversation_history(phone: str, limit: int = 10) -> list[dict]:
    rows = await fetch(
        """
        SELECT role, message FROM conversations
        WHERE customer_phone = $1
        ORDER BY created_at DESC LIMIT $2
        """,
        phone, limit,
    )
    # Reverse to chronological order
    messages = [{"role": r["role"], "content": r["message"]} for r in reversed(rows)]
    return messages


async def generate_reply(
    phone: str,
    platform: str,
    incoming_message: str,
) -> dict:
    from ai.escalation import should_escalate, handle_escalation

    # Save incoming message
    await execute(
        "INSERT INTO conversations (customer_phone, platform, role, message) VALUES ($1, $2, 'user', $3)",
        phone, platform, incoming_message,
    )

    # Check escalation
    escalation = await should_escalate(phone, incoming_message)
    if escalation["should_escalate"]:
        await execute(
            "UPDATE conversations SET escalated = TRUE WHERE customer_phone = $1 AND role = 'user' ORDER BY created_at DESC LIMIT 1",
            phone,
        )
        await handle_escalation(phone, platform, incoming_message, escalation["reason"])
        reply = "Terima kasih atas laporannya kak. Kami akan teruskan ke tim terkait dan menghubungi kembali dalam 1x24 jam. Mohon maaf atas ketidaknyamanannya 🙏"
    else:
        # Get conversation history
        history = await get_conversation_history(phone)

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=CS_SYSTEM_PROMPT,
            messages=history,
        )
        reply = response.content[0].text

    # Save bot reply
    await execute(
        "INSERT INTO conversations (customer_phone, platform, role, message) VALUES ($1, $2, 'assistant', $3)",
        phone, platform, reply,
    )

    logger.info(
        "cs_reply_generated",
        phone=phone[:6] + "****",
        escalated=escalation["should_escalate"] if 'escalation' in dir() else False,
    )

    return {"reply": reply, "escalated": escalation.get("should_escalate", False)}
