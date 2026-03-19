"""
Tokopedia scraper using Playwright with Indonesia proxy.
Uses domcontentloaded (not networkidle) and 120s timeout for slow proxy connections.
"""
import asyncio
import re
from typing import Optional
from urllib.parse import quote

import asyncpg

from scrapers.base_scraper import BaseScraper
from utils.currency import parse_idr_string, parse_sold_count
from utils.logger import get_logger

logger = get_logger(__name__)

_MIN_DELAY = 3.0


class TokopediaScraper(BaseScraper):

    SEARCH_URL = "https://www.tokopedia.com/search?st=product&q={keyword}&navsource=home&srp_component_id=02.01.00.00&page={page}"

    def __init__(self):
        super().__init__()

    async def scrape_search(self, keyword: str, max_pages: int = 3) -> list[dict]:
        results: list[dict] = []
        for page_num in range(1, max_pages + 1):
            url = self.SEARCH_URL.format(keyword=quote(keyword), page=page_num)
            logger.info(f"[Tokopedia] Scraping page {page_num}: {url}")
            try:
                page_results = await self._scrape_search_page(url)
                results.extend(page_results)
                logger.info(f"[Tokopedia] Page {page_num}: {len(page_results)} products")
                if not page_results:
                    break
                await asyncio.sleep(_MIN_DELAY)
            except Exception as exc:
                logger.error(f"[Tokopedia] Page {page_num} failed: {exc}")
                break
        await self.close()
        return results

    async def scrape_product(self, url: str) -> dict:
        page = await self._get_page(url, wait_until="domcontentloaded")
        try:
            return await self._extract_product_detail(page, url)
        finally:
            await page.context.close()

    async def _scrape_search_page(self, url: str) -> list[dict]:
        page = await self._get_page(url, wait_until="domcontentloaded")
        try:
            await self._random_delay(_MIN_DELAY, _MIN_DELAY + 2)
            content = await page.content()
            if self._detect_captcha(content):
                logger.warning("[Tokopedia] CAPTCHA detected")
                return []

            # Wait for product cards
            try:
                await page.wait_for_selector('[data-testid="master-product-card"]', timeout=20_000)
            except Exception:
                try:
                    await page.wait_for_selector(".css-bk6tzz", timeout=10_000)
                except Exception:
                    logger.warning("[Tokopedia] No product cards found")
                    return []

            await self._human_scroll(page)
            return await self._extract_search_cards(page)
        finally:
            await page.context.close()

    async def _extract_search_cards(self, page) -> list[dict]:
        cards = await page.query_selector_all('[data-testid="master-product-card"]')
        if not cards:
            cards = await page.query_selector_all(".css-bk6tzz")
        products = []
        for card in cards:
            try:
                product = await self._parse_card(card)
                if product:
                    products.append(product)
            except Exception as exc:
                logger.debug(f"[Tokopedia] Card parse error: {exc}")
        return products

    async def _parse_card(self, card) -> Optional[dict]:
        try:
            title_el = await card.query_selector('[data-testid="spnSRPProdName"]')
            title = (await title_el.text_content()).strip() if title_el else ""
            if not title:
                return None
            price_el = await card.query_selector('[data-testid="spnSRPProdPrice"]')
            price_raw = (await price_el.text_content()).strip() if price_el else "0"
            price_idr = parse_idr_string(price_raw)
            shop_el = await card.query_selector('[data-testid="spnSRPProdTabName"]')
            seller_name = (await shop_el.text_content()).strip() if shop_el else ""
            location_el = await card.query_selector('[data-testid="spnSRPProdTabArea"]')
            seller_city = (await location_el.text_content()).strip() if location_el else ""
            rating_el = await card.query_selector('[data-testid="spnSRPProdRating"]')
            rating_raw = (await rating_el.text_content()).strip() if rating_el else ""
            rating = _parse_rating(rating_raw)
            review_el = await card.query_selector('[data-testid="spnSRPProdReviewTotal"]')
            review_raw = (await review_el.text_content()).strip() if review_el else "0"
            review_count = _parse_review_count(review_raw)
            sold_el = await card.query_selector('[data-testid="spnSRPProdSold"]')
            sold_raw = (await sold_el.text_content()).strip() if sold_el else "0"
            sold_30d = parse_sold_count(sold_raw)
            img_el = await card.query_selector("img")
            image_url = await img_el.get_attribute("src") if img_el else ""
            link_el = await card.query_selector("a")
            product_url = await link_el.get_attribute("href") if link_el else ""
            if product_url and product_url.startswith("/"):
                product_url = f"https://www.tokopedia.com{product_url}"
            return {
                "platform": "tokopedia",
                "title": title,
                "price_idr": price_idr,
                "seller_name": seller_name,
                "seller_city": seller_city,
                "rating": rating,
                "review_count": review_count,
                "sold_30d": sold_30d,
                "sold_count": sold_30d,
                "image_url": image_url,
                "url": product_url,
                "seller_badge": "",
            }
        except Exception as exc:
            logger.debug(f"[Tokopedia] Card parse exception: {exc}")
            return None

    async def _extract_product_detail(self, page, url: str) -> dict:
        title = await self._safe_text(page, 'h1[data-testid="lblPDPDetailProductName"]')
        if not title:
            title = await self._safe_text(page, "h1")
        price_raw = await self._safe_text(page, '[data-testid="lblPDPDetailProductPrice"]')
        price_idr = parse_idr_string(price_raw)
        sold_raw = await self._safe_text(page, '[data-testid="lblPDPDetailProductSoldCounter"]')
        sold_count = parse_sold_count(sold_raw)
        rating_raw = await self._safe_text(page, '[data-testid="lblPDPDetailProductRatingNumber"]')
        rating = _parse_rating(rating_raw)
        review_raw = await self._safe_text(page, '[data-testid="btnSeeAllReview"]')
        review_count = _parse_review_count(review_raw)
        seller_name = await self._safe_text(page, '[data-testid="llbPDPFooterShopName"]')
        seller_city = await self._safe_text(page, '[data-testid="llbPDPFooterShopLocation"]')
        img_url = await self._safe_attr(page, '[data-testid="PDPMainImage"] img', "src")
        return {
            "platform": "tokopedia",
            "platform_product_id": _extract_tokopedia_product_id(url),
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
# DB persistence
# ------------------------------------------------------------------

async def save_listings_to_db(db_url: str, listings: list[dict], job_id: str | None = None) -> int:
    if not listings:
        return 0
    from engines.deduplicator import find_or_create_canonical_product_simple
    conn = await asyncpg.connect(db_url)
    try:
        saved = 0
        for item in listings:
            try:
                if not item.get("title"):
                    continue
                product_id = await find_or_create_canonical_product_simple(
                    conn, item["title"], item.get("image_url"),
                )
                if not product_id:
                    continue
                await conn.execute("""
                    INSERT INTO product_listings (
                        product_id, platform, platform_product_id,
                        title, url, image_url,
                        price_idr, sold_count, sold_30d,
                        review_count, rating,
                        seller_name, seller_city, seller_badge,
                        scraped_at
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,NOW())
                    ON CONFLICT (product_id, platform, platform_product_id)
                    DO UPDATE SET
                        price_idr = EXCLUDED.price_idr,
                        sold_count = EXCLUDED.sold_count,
                        sold_30d = EXCLUDED.sold_30d,
                        review_count = EXCLUDED.review_count,
                        rating = EXCLUDED.rating,
                        scraped_at = NOW()
                """,
                product_id,
                item.get("platform", "tokopedia"),
                item.get("platform_product_id") or item.get("url", "")[:200],
                item.get("title", ""),
                item.get("url"),
                item.get("image_url"),
                item.get("price_idr", 0),
                item.get("sold_count", 0),
                item.get("sold_30d", 0),
                item.get("review_count", 0),
                item.get("rating"),
                item.get("seller_name"),
                item.get("seller_city"),
                item.get("seller_badge"),
                )
                saved += 1
            except Exception as exc:
                logger.warning(f"[Tokopedia] DB save error: {exc}")
        return saved
    finally:
        await conn.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_rating(raw: str) -> Optional[float]:
    try:
        clean = re.sub(r"[^\d.,]", "", raw).replace(",", ".")
        val = float(clean)
        return val if 0 <= val <= 5 else None
    except (ValueError, TypeError):
        return None


def _parse_review_count(raw: str) -> int:
    try:
        clean = re.sub(r"[^\d]", "", raw)
        return int(clean) if clean else 0
    except (ValueError, TypeError):
        return 0


def _extract_tokopedia_product_id(url: str) -> Optional[str]:
    match = re.search(r"/(\d+)(?:\?|$)", url)
    return match.group(1) if match else None
