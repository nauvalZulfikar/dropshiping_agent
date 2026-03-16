"""Celery tasks for Telegram alerts and daily digest."""
import asyncio
import logging

import telegram

from tasks.celery_app import celery_app
from config import settings

logger = logging.getLogger(__name__)


async def _send_telegram(message: str):
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram not configured — skipping notification")
        return
    bot = telegram.Bot(token=settings.telegram_bot_token)
    await bot.send_message(
        chat_id=settings.telegram_chat_id,
        text=message,
        parse_mode="HTML",
    )


def send_telegram(message: str):
    asyncio.run(_send_telegram(message))


@celery_app.task(name="tasks.alert_tasks.send_daily_digest")
def send_daily_digest():
    """Send top 5 products by opportunity score to Telegram at 08:00 WIB."""
    return asyncio.run(_daily_digest_async())


async def _daily_digest_async():
    import asyncpg
    from config import settings

    conn = await asyncpg.connect(settings.database_url)
    try:
        rows = await conn.fetch("""
            SELECT pl.title, pl.platform, pl.price_idr, pl.url,
                   ps.margin_pct, ps.opportunity_score
            FROM product_listings pl
            JOIN product_scores ps ON ps.listing_id = pl.id
            WHERE pl.is_active = TRUE AND ps.gate_passed = TRUE
            ORDER BY ps.opportunity_score DESC
            LIMIT 5
        """)
    finally:
        await conn.close()

    if not rows:
        await _send_telegram("📊 <b>Dropship Daily Digest</b>\n\nBelum ada produk yang memenuhi semua 5 gate hari ini.")
        return {"sent": False, "reason": "no qualifying products"}

    lines = ["📊 <b>Dropship Daily Digest</b> — Top 5 Produk Hari Ini\n"]
    for i, r in enumerate(rows, 1):
        price_fmt = f"Rp {r['price_idr']:,}".replace(",", ".")
        lines.append(
            f"{i}. <b>{r['title'][:60]}</b>\n"
            f"   Platform: {r['platform'].title()} | Harga: {price_fmt}\n"
            f"   Margin: {r['margin_pct']:.1f}% | Score: {r['opportunity_score']:.1f}/100\n"
            f"   🔗 {r['url'] or 'N/A'}\n"
        )

    await _send_telegram("\n".join(lines))
    return {"sent": True, "products": len(rows)}


@celery_app.task(name="tasks.alert_tasks.send_watchlist_alerts")
def send_watchlist_alerts():
    """Check watchlisted products for price drops / spikes and send alerts."""
    return asyncio.run(_watchlist_alerts_async())


async def _watchlist_alerts_async():
    import asyncpg
    from config import settings

    conn = await asyncpg.connect(settings.database_url)
    try:
        rows = await conn.fetch("""
            SELECT
                w.user_id,
                w.alert_on_price_drop,
                w.alert_on_spike,
                pl.id          AS listing_id,
                pl.title,
                pl.platform,
                pl.price_idr   AS current_price,
                pl.sold_30d    AS current_sold,
                pl.url,
                ps.opportunity_score,
                ph_prev.price_idr  AS prev_price,
                ph_prev.sold_count AS prev_sold
            FROM watchlists w
            JOIN product_listings pl ON pl.id = w.listing_id
            LEFT JOIN product_scores ps ON ps.listing_id = w.listing_id
            LEFT JOIN LATERAL (
                SELECT price_idr, sold_count
                FROM price_history
                WHERE listing_id = w.listing_id
                ORDER BY recorded_at DESC
                LIMIT 1 OFFSET 1
            ) ph_prev ON TRUE
            WHERE pl.is_active = TRUE
        """)
    finally:
        await conn.close()

    alerts_sent = 0
    for r in rows:
        curr_price = r["current_price"]
        prev_price = r["prev_price"]
        curr_sold  = r["current_sold"] or 0
        prev_sold  = r["prev_sold"] or 0
        title      = (r["title"] or "")[:60]
        platform   = (r["platform"] or "").title()
        url        = r["url"] or ""

        # --- Price drop alert ---
        if r["alert_on_price_drop"] and prev_price and curr_price and prev_price > 0:
            drop_pct = (prev_price - curr_price) / prev_price * 100
            if drop_pct >= 5:
                old_fmt = f"Rp {prev_price:,.0f}".replace(",", ".")
                new_fmt = f"Rp {curr_price:,.0f}".replace(",", ".")
                msg = (
                    f"🔻 <b>Price Drop Alert!</b>\n"
                    f"<b>{title}</b>\n"
                    f"Platform: {platform}\n"
                    f"Harga turun {drop_pct:.1f}%: {old_fmt} → {new_fmt}\n"
                    f"🔗 {url}"
                )
                await _send_telegram(msg)
                alerts_sent += 1

        # --- Sold spike alert (>50% increase in sold_30d vs prev snapshot) ---
        if r["alert_on_spike"] and prev_sold and prev_sold > 0:
            spike_pct = (curr_sold - prev_sold) / prev_sold * 100
            if spike_pct >= 50:
                msg = (
                    f"📈 <b>Sales Spike Alert!</b>\n"
                    f"<b>{title}</b>\n"
                    f"Platform: {platform}\n"
                    f"Penjualan naik {spike_pct:.0f}%: "
                    f"{prev_sold:,} → {curr_sold:,} terjual (30d)\n"
                    f"Score: {r['opportunity_score']:.1f}/100\n"
                    f"🔗 {url}"
                )
                await _send_telegram(msg)
                alerts_sent += 1

    return {"alerts_sent": alerts_sent, "checked": len(rows)}
