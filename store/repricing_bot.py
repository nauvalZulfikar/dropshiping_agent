"""
Repricing bot — scrape competitor prices and update product pricing.
Logic:
1. Scrape harga top 10 kompetitor
2. Hitung P20 (percentile 20)
3. Optimal price = max(floor_price, P20 * 0.98)
4. Update hanya kalau selisih > Rp 1.000
5. Bulatkan ke ribuan terdekat
"""
import asyncio
import math
from typing import Optional

import httpx

from core.celery_app import celery_app
from core.config import FLOOR_MARGIN
from core.db import execute, fetch
from core.logger import logger


def calculate_floor_price(cogs_idr: int, floor_margin: float = FLOOR_MARGIN, platform_fee: float = 0.08) -> int:
    return math.ceil(cogs_idr / (1 - floor_margin - platform_fee))


def calculate_optimal_price(
    competitor_prices: list[int],
    cogs_idr: int,
    floor_margin: float = FLOOR_MARGIN,
) -> int:
    if not competitor_prices:
        return 0

    sorted_prices = sorted(competitor_prices)
    idx = max(0, int(len(sorted_prices) * 0.20) - 1)
    p20 = sorted_prices[idx]

    floor = calculate_floor_price(cogs_idr, floor_margin)
    optimal = max(floor, int(p20 * 0.98))

    # Round to nearest 1000
    optimal = round(optimal / 1000) * 1000

    return optimal


async def scrape_competitor_prices(keyword: str, platform: str = "shopee") -> list[int]:
    """Scrape top competitor prices via search API or web scraping."""
    prices = []

    try:
        # Use Shopee search API (public, no auth needed)
        if platform == "shopee":
            url = "https://shopee.co.id/api/v4/search/search_items"
            params = {
                "keyword": keyword,
                "limit": 10,
                "order": "desc",
                "page_type": "search",
                "scenario": "PAGE_GLOBAL_SEARCH",
                "by": "relevancy",
            }
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, params=params, headers={
                    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                })
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", [])[:10]:
                        price = item.get("item_basic", {}).get("price", 0)
                        if price > 0:
                            prices.append(price // 100000)  # Shopee price in micro-cents
    except Exception as e:
        logger.warning("competitor_scrape_failed", keyword=keyword, platform=platform, error=str(e))

    return prices


async def reprice_product(product_id: int) -> Optional[dict]:
    row = await fetch(
        "SELECT id, name, niche, cogs_idr, current_price, floor_margin, platform_ids FROM products WHERE id = $1",
        product_id,
    )
    if not row:
        return None

    product = dict(row[0])
    keyword = product["name"][:50]
    cogs = product["cogs_idr"]
    current = product["current_price"]
    margin = float(product["floor_margin"])

    competitor_prices = await scrape_competitor_prices(keyword)
    if not competitor_prices:
        logger.info("reprice_skipped_no_competitors", product_id=product_id)
        return None

    optimal = calculate_optimal_price(competitor_prices, cogs, margin)

    if abs(optimal - current) <= 1000:
        logger.info("reprice_skipped_small_diff", product_id=product_id, current=current, optimal=optimal)
        return None

    await execute(
        "UPDATE products SET current_price = $1, updated_at = NOW() WHERE id = $2",
        optimal, product_id,
    )

    await execute(
        "INSERT INTO price_history (product_id, price, competitor_avg) VALUES ($1, $2, $3)",
        product_id, optimal, int(sum(competitor_prices) / len(competitor_prices)),
    )

    logger.info(
        "product_repriced",
        product_id=product_id, old_price=current, new_price=optimal,
        competitor_count=len(competitor_prices),
    )

    return {
        "product_id": product_id,
        "old_price": current,
        "new_price": optimal,
        "competitor_avg": int(sum(competitor_prices) / len(competitor_prices)),
    }


@celery_app.task(name="store.repricing_bot.reprice_all")
def reprice_all():
    async def _run():
        products = await fetch("SELECT id FROM products WHERE is_active = TRUE")
        results = []
        for p in products:
            result = await reprice_product(p["id"])
            if result:
                results.append(result)
            await asyncio.sleep(2)  # Rate limit
        return {"repriced": len(results), "results": results}

    return asyncio.run(_run())
