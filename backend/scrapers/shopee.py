"""
Shopee scraper.
Shopee is a SPA — waits for network idle + specific selectors.
Anti-bot: playwright-stealth + random 2-5s delays + viewport randomization.
Sold count format: "1.2K sold" → 1200
Price format: integers in the API response embedded in HTML.
"""
import asyncio
import json
import logging
import re
from typing import Optional
from urllib.parse import quote

import asyncpg

from scrapers.base_scraper import BaseScraper
from utils.currency import parse_idr_string, parse_sold_count
from utils.logger import get_logger

logger = get_logger(__name__)


class ShopeeScraper(BaseScraper):
    """Scrapes search results and product detail from Shopee Indonesia."""

    SEARCH_URL = "https://shopee.co.id/search?keyword={keyword}&page={page}"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def scrape_search(self, keyword: str, max_pages: int = 3) -> list[dict]:
        """
        Scrape Shopee search results.
        Uses SPA wait strategy: networkidle + selector wait.
        """
        results: list[dict] = []
        for page_num in range(max_pages):
            url = self.SEARCH_URL.format(keyword=quote(keyword), page=page_num)
            logger.info(f"[Shopee] Scraping page {page_num + 1}: {url}")
            try:
                page_results = await self._scrape_search_page(url)
                results.extend(page_results)
                logger.info(f"[Shopee] Page {page_num + 1}: {len(page_results)} products")
                await asyncio.sleep(2.5)
            except Exception as exc:
                logger.error(f"[Shopee] Page {page_num + 1} failed: {exc}")
                break

        await self.close()
        return results

    async def scrape_product(self, url: str) -> dict:
        """Scrape full Shopee product detail."""
        page = await self._get_page(url, wait_until="networkidle")
        try:
            await self._random_delay(2.0, 5.0)
            content = await page.content()
            if self._detect_captcha(content):
                raise RuntimeError("CAPTCHA detected on Shopee product page")
            return await self._extract_product_detail(page, url)
        finally:
            await page.context.close()

    # ------------------------------------------------------------------
    # Search page
    # ------------------------------------------------------------------

    async def _scrape_search_page(self, url: str) -> list[dict]:
        page = await self._get_page(url, wait_until="networkidle")
        try:
            await self._random_delay(2.0, 5.0)

            content = await page.content()
            if self._detect_captcha(content):
                logger.warning("[Shopee] CAPTCHA on search page")
                return []

            # Wait for product cards — Shopee renders cards in a grid
            try:
                await page.wait_for_selector('[data-sqe="item"]', timeout=20_000)
            except Exception:
                try:
                    await page.wait_for_selector(".shopee-search-item-result__items .col-xs-2-4", timeout=15_000)
                except Exception:
                    logger.warning("[Shopee] No product cards found on page")
                    return []

            return await self._extract_search_cards(page)
        finally:
            await page.context.close()

    async def _extract_search_cards(self, page) -> list[dict]:
        """Extract product data from Shopee search result cards."""
        # Try to intercept the SRP API response embedded in window.__page_state__
        # Fallback: parse DOM elements
        products = await self._try_extract_from_page_state(page)
        if products:
            return products

        # DOM-based fallback
        cards = await page.query_selector_all('[data-sqe="item"]')
        if not cards:
            cards = await page.query_selector_all(".col-xs-2-4")

        results = []
        for card in cards:
            try:
                p = await self._parse_card_dom(card)
                if p:
                    results.append(p)
            except Exception as exc:
                logger.debug(f"[Shopee] Card parse error: {exc}")
        return results

    async def _try_extract_from_page_state(self, page) -> list[dict]:
        """
        Try to extract product data from Shopee's embedded JSON state.
        Shopee often embeds search results in window.__NEXT_DATA__ or similar.
        """
        try:
            data = await page.evaluate("""
                () => {
                    const s = document.getElementById('__NEXT_DATA__');
                    return s ? s.textContent : null;
                }
            """)
            if not data:
                return []
            parsed = json.loads(data)
            items = (
                parsed.get("props", {})
                      .get("pageProps", {})
                      .get("data", {})
                      .get("sections", [{}])[0]
                      .get("data", {})
                      .get("item", [])
            )
            return [self._normalize_shopee_item(item) for item in items if item]
        except Exception:
            return []

    def _normalize_shopee_item(self, item: dict) -> dict:
        """Normalize a Shopee API item dict to our standard schema."""
        price = item.get("price", 0)
        if price > 1_000_000:  # Shopee sometimes returns price in micro-IDR
            price = price // 100_000
        price_before = item.get("price_before_discount", 0)
        if price_before > 1_000_000:
            price_before = price_before // 100_000

        sold = item.get("historical_sold", 0) or item.get("sold", 0)
        image_id = item.get("image", "")
        image_url = f"https://down-id.img.susercontent.com/file/{image_id}" if image_id else ""
        shop_id = item.get("shopid", "")
        item_id = item.get("itemid", "")
        url = f"https://shopee.co.id/product/{shop_id}/{item_id}" if shop_id and item_id else ""

        return {
            "platform": "shopee",
            "platform_product_id": str(item_id),
            "title": item.get("name", ""),
            "url": url,
            "image_url": image_url,
            "price_idr": int(price),
            "original_price_idr": int(price_before) if price_before else None,
            "sold_count": int(sold),
            "sold_30d": int(sold),
            "review_count": item.get("item_rating", {}).get("rating_count", [0])[-1] if isinstance(item.get("item_rating", {}).get("rating_count"), list) else 0,
            "rating": round(item.get("item_rating", {}).get("rating_star", 0), 2),
            "seller_name": item.get("shop_name", ""),
            "seller_id": str(shop_id),
            "liked_count": item.get("liked_count", 0),
        }

    async def _parse_card_dom(self, card) -> Optional[dict]:
        """DOM fallback: parse product card HTML elements."""
        try:
            name_el = await card.query_selector('[data-sqe="name"]')
            title = (await name_el.text_content()).strip() if name_el else ""
            if not title:
                return None

            price_el = await card.query_selector('[data-sqe="price"]')
            price_raw = (await price_el.text_content()).strip() if price_el else "0"
            price_idr = parse_idr_string(price_raw)

            sold_el = await card.query_selector("._1ST3e")  # Shopee sold count class
            sold_raw = (await sold_el.text_content()).strip() if sold_el else "0"
            sold_30d = parse_sold_count(sold_raw)

            rating_el = await card.query_selector("._4d1go")
            rating_raw = (await rating_el.text_content()).strip() if rating_el else ""
            rating = _parse_float(rating_raw)

            img_el = await card.query_selector("img")
            image_url = await img_el.get_attribute("src") if img_el else ""

            link_el = await card.query_selector("a")
            product_url = await link_el.get_attribute("href") if link_el else ""
            if product_url and not product_url.startswith("http"):
                product_url = f"https://shopee.co.id{product_url}"

            shop_el = await card.query_selector("._3bMEb")
            seller_name = (await shop_el.text_content()).strip() if shop_el else ""

            location_el = await card.query_selector(".Ox0TMh")
            seller_city = (await location_el.text_content()).strip() if location_el else ""

            return {
                "platform": "shopee",
                "title": title,
                "price_idr": price_idr,
                "sold_count": sold_30d,
                "sold_30d": sold_30d,
                "rating": rating,
                "image_url": image_url,
                "url": product_url,
                "seller_name": seller_name,
                "seller_city": seller_city,
            }
        except Exception as exc:
            logger.debug(f"[Shopee] DOM parse error: {exc}")
            return None

    # ------------------------------------------------------------------
    # Product detail
    # ------------------------------------------------------------------

    async def _extract_product_detail(self, page, url: str) -> dict:
        title = await self._safe_text(page, "._44qnta")
        if not title:
            title = await self._safe_text(page, "h1")

        price_raw = await self._safe_text(page, "._3n5NQx")
        price_idr = parse_idr_string(price_raw)

        sold_raw = await self._safe_text(page, "._18SLip")
        sold_count = parse_sold_count(sold_raw)

        rating_raw = await self._safe_text(page, "._3Oj5_n")
        rating = _parse_float(rating_raw)

        review_raw = await self._safe_text(page, "._3Oj5_n + span")
        review_count = _parse_int(review_raw)

        shop_raw = await self._safe_text(page, ".sGDH8d")
        seller_name = shop_raw

        location_raw = await self._safe_text(page, "._3kd3QA")
        seller_city = location_raw

        img_url = await self._safe_attr(page, "._2h5NaP img", "src")

        # Platform IDs from URL pattern: /product/{shop_id}/{item_id}
        parts = url.rstrip("/").split("/")
        platform_product_id = parts[-1] if parts else None

        return {
            "platform": "shopee",
            "platform_product_id": platform_product_id,
            "title": title,
            "url": url,
            "image_url": img_url,
            "price_idr": price_idr,
            "sold_count": sold_count,
            "sold_30d": sold_count,
            "review_count": review_count,
            "rating": rating,
            "seller_name": seller_name,
            "seller_city": seller_city,
        }


# ------------------------------------------------------------------
# DB persistence helper
# ------------------------------------------------------------------

async def save_listings_to_db(db_url: str, listings: list[dict]) -> int:
    """Upsert Shopee listings into product_listings using deduplicator."""
    if not listings:
        return 0
    from engines.deduplicator import find_or_create_canonical_product_simple
    conn = await asyncpg.connect(db_url)
    try:
        saved = 0
        for item in listings:
            if not item.get("title"):
                continue
            try:
                product_id = await find_or_create_canonical_product_simple(
                    conn,
                    item["title"],
                    item.get("image_url"),
                )
                if not product_id:
                    continue

                await conn.execute("""
                    INSERT INTO product_listings (
                        product_id, platform, platform_product_id,
                        title, url, image_url,
                        price_idr, original_price_idr,
                        sold_count, sold_30d,
                        review_count, rating,
                        seller_name, seller_id, seller_city,
                        scraped_at
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,NOW())
                    ON CONFLICT (product_id, platform, platform_product_id)
                    DO UPDATE SET
                        price_idr = EXCLUDED.price_idr,
                        sold_count = EXCLUDED.sold_count,
                        sold_30d = EXCLUDED.sold_30d,
                        rating = EXCLUDED.rating,
                        scraped_at = NOW()
                """,
                product_id,
                "shopee",
                item.get("platform_product_id") or item.get("url", "")[:200],
                item["title"],
                item.get("url"),
                item.get("image_url"),
                item.get("price_idr", 0),
                item.get("original_price_idr"),
                item.get("sold_count", 0),
                item.get("sold_30d", 0),
                item.get("review_count", 0),
                item.get("rating"),
                item.get("seller_name"),
                item.get("seller_id"),
                item.get("seller_city"),
                )
                saved += 1
            except Exception as exc:
                logger.warning(f"[Shopee] DB save error for '{item.get('title', '')[:40]}': {exc}")
        return saved
    finally:
        await conn.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_float(raw: str) -> Optional[float]:
    try:
        clean = re.sub(r"[^\d.]", "", raw)
        return float(clean) if clean else None
    except (ValueError, TypeError):
        return None


def _parse_int(raw: str) -> int:
    try:
        clean = re.sub(r"[^\d]", "", raw)
        return int(clean) if clean else 0
    except (ValueError, TypeError):
        return 0
