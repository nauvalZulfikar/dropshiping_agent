"""
Tokopedia scraper.
Rate limit: max 1 req / 3s per proxy. Rotate proxy every 10 requests.
Sold count format: "1,2rb terjual" → 1200
Price format: "Rp15.000" → 15000
"""
import asyncio
import logging
import re
from typing import Optional
from urllib.parse import quote

import asyncpg

from scrapers.base_scraper import BaseScraper
from utils.currency import parse_idr_string, parse_sold_count
from utils.logger import get_logger

logger = get_logger(__name__)

_MIN_DELAY = 3.0  # seconds between requests (rate limit)
_ROTATE_EVERY = 10  # rotate proxy after N requests


class TokopediaScraper(BaseScraper):
    """Scrapes search results and product details from Tokopedia."""

    SEARCH_URL = "https://www.tokopedia.com/search?st=product&q={keyword}&navsource=home&srp_component_id=02.01.00.00&page={page}"

    def __init__(self):
        super().__init__()
        self._request_count = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def scrape_search(self, keyword: str, max_pages: int = 3) -> list[dict]:
        """
        Scrape search results for a keyword across max_pages pages.
        Returns list of product dicts ready for DB insertion.
        """
        results: list[dict] = []
        for page_num in range(1, max_pages + 1):
            url = self.SEARCH_URL.format(keyword=quote(keyword), page=page_num)
            logger.info(f"[Tokopedia] Scraping page {page_num}: {url}")

            try:
                page_results = await self._scrape_search_page(url)
                results.extend(page_results)
                logger.info(f"[Tokopedia] Page {page_num}: {len(page_results)} products")
                await asyncio.sleep(_MIN_DELAY)
            except Exception as exc:
                logger.error(f"[Tokopedia] Page {page_num} failed: {exc}")
                break

        await self.close()
        return results

    async def scrape_product(self, url: str) -> dict:
        """Scrape full product detail page. Returns product dict."""
        page = await self._get_page(url, wait_until="networkidle")
        try:
            await self._random_delay(2.0, 4.0)
            content = await page.content()
            if self._detect_captcha(content):
                raise RuntimeError("CAPTCHA detected on Tokopedia product page")

            return await self._extract_product_detail(page, url)
        finally:
            await page.context.close()

    # ------------------------------------------------------------------
    # Search page extraction
    # ------------------------------------------------------------------

    async def _scrape_search_page(self, url: str) -> list[dict]:
        page = await self._get_page(url, wait_until="networkidle")
        try:
            await self._random_delay(_MIN_DELAY, _MIN_DELAY + 1.5)

            content = await page.content()
            if self._detect_captcha(content):
                logger.warning("[Tokopedia] CAPTCHA detected on search page")
                return []

            # Wait for product cards to render
            try:
                await page.wait_for_selector('[data-testid="master-product-card"]', timeout=15_000)
            except Exception:
                # Fallback selector
                await page.wait_for_selector(".css-bk6tzz", timeout=10_000)

            self._request_count += 1
            return await self._extract_search_cards(page)
        finally:
            await page.context.close()

    async def _extract_search_cards(self, page) -> list[dict]:
        """Extract all product cards from a search result page."""
        cards = await page.query_selector_all('[data-testid="master-product-card"]')
        if not cards:
            # Fallback: try generic card selectors
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
        """Parse a single product card element into a dict."""
        try:
            # Title
            title_el = await card.query_selector('[data-testid="spnSRPProdName"]')
            title = (await title_el.text_content()).strip() if title_el else ""
            if not title:
                return None

            # Price
            price_el = await card.query_selector('[data-testid="spnSRPProdPrice"]')
            price_raw = (await price_el.text_content()).strip() if price_el else "0"
            price_idr = parse_idr_string(price_raw)

            # Shop info
            shop_el = await card.query_selector('[data-testid="spnSRPProdTabName"]')
            seller_name = (await shop_el.text_content()).strip() if shop_el else ""

            location_el = await card.query_selector('[data-testid="spnSRPProdTabArea"]')
            seller_city = (await location_el.text_content()).strip() if location_el else ""

            # Rating & review
            rating_el = await card.query_selector('[data-testid="spnSRPProdRating"]')
            rating_raw = (await rating_el.text_content()).strip() if rating_el else ""
            rating = _parse_rating(rating_raw)

            review_el = await card.query_selector('[data-testid="spnSRPProdReviewTotal"]')
            review_raw = (await review_el.text_content()).strip() if review_el else "0"
            review_count = _parse_review_count(review_raw)

            # Sold count
            sold_el = await card.query_selector('[data-testid="spnSRPProdSold"]')
            sold_raw = (await sold_el.text_content()).strip() if sold_el else "0"
            sold_30d = parse_sold_count(sold_raw)

            # Image
            img_el = await card.query_selector("img")
            image_url = await img_el.get_attribute("src") if img_el else ""

            # Product URL
            link_el = await card.query_selector("a")
            product_url = await link_el.get_attribute("href") if link_el else ""
            if product_url and product_url.startswith("/"):
                product_url = f"https://www.tokopedia.com{product_url}"

            # Badge (official store, star seller, etc.)
            badge_el = await card.query_selector('[data-testid="spnSRPProdBadge"]')
            badge = (await badge_el.text_content()).strip() if badge_el else ""

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
                "seller_badge": badge,
            }
        except Exception as exc:
            logger.debug(f"[Tokopedia] Card parse exception: {exc}")
            return None

    # ------------------------------------------------------------------
    # Product detail extraction
    # ------------------------------------------------------------------

    async def _extract_product_detail(self, page, url: str) -> dict:
        """Extract full product detail from a product page."""
        title = await self._safe_text(page, 'h1[data-testid="lblPDPDetailProductName"]')
        if not title:
            title = await self._safe_text(page, "h1")

        price_raw = await self._safe_text(page, '[data-testid="lblPDPDetailProductPrice"]')
        price_idr = parse_idr_string(price_raw)

        # Sold count — total (not 30d, but best we can get from detail page)
        sold_raw = await self._safe_text(page, '[data-testid="lblPDPDetailProductSoldCounter"]')
        sold_count = parse_sold_count(sold_raw)

        rating_raw = await self._safe_text(page, '[data-testid="lblPDPDetailProductRatingNumber"]')
        rating = _parse_rating(rating_raw)

        review_raw = await self._safe_text(page, '[data-testid="btnSeeAllReview"]')
        review_count = _parse_review_count(review_raw)

        seller_name = await self._safe_text(page, '[data-testid="llbPDPFooterShopName"]')
        seller_city = await self._safe_text(page, '[data-testid="llbPDPFooterShopLocation"]')

        # Stock
        stock_raw = await self._safe_text(page, '[data-testid="lblPDPStockValueLimit"]')
        stock = _parse_integer(stock_raw)

        # Description
        desc = await self._safe_text(page, '[data-testid="lblPDPDescriptionProduk"]')

        # Image
        img_url = await self._safe_attr(page, '[data-testid="PDPMainImage"] img', "src")

        # Category breadcrumb
        breadcrumb_els = await page.query_selector_all('[data-testid="btnPDPShopBreadcrumb"] a')
        breadcrumb = " > ".join([(await el.text_content() or "").strip() for el in breadcrumb_els])

        # Platform product ID from URL
        platform_product_id = _extract_tokopedia_product_id(url)

        return {
            "platform": "tokopedia",
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
            "stock": stock,
            "description": desc,
            "category_breadcrumb": breadcrumb,
        }


# ------------------------------------------------------------------
# DB persistence helper (called from Celery tasks)
# ------------------------------------------------------------------

async def save_listings_to_db(db_url: str, listings: list[dict], job_id: str | None = None) -> int:
    """
    Upsert scraped Tokopedia listings into product_listings table.
    Uses deduplicator to find/create canonical product rows.
    Returns count of rows inserted/updated.
    """
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

                # Dedup: find or create canonical product
                product_id = await find_or_create_canonical_product_simple(
                    conn,
                    item["title"],
                    item.get("image_url"),
                )
                if not product_id:
                    continue

                # Upsert the platform listing
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
                logger.warning(f"[Tokopedia] DB save error for '{item.get('title', '')[:40]}': {exc}")

        return saved
    finally:
        await conn.close()


# ------------------------------------------------------------------
# Parsing helpers
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


def _parse_integer(raw: str) -> Optional[int]:
    try:
        clean = re.sub(r"[^\d]", "", raw)
        return int(clean) if clean else None
    except (ValueError, TypeError):
        return None


def _extract_tokopedia_product_id(url: str) -> Optional[str]:
    """Extract product ID from Tokopedia URL."""
    match = re.search(r"/(\d+)(?:\?|$)", url)
    return match.group(1) if match else None
