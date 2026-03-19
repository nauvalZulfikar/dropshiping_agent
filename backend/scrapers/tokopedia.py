"""
Tokopedia scraper — uses GraphQL API via httpx (no browser needed).
Falls back to Playwright only for product detail pages.
"""
import asyncio
import re
import random
from typing import Optional
from urllib.parse import quote

import asyncpg
import httpx

from scrapers.base_scraper import BaseScraper
from utils.currency import parse_idr_string, parse_sold_count
from utils.logger import get_logger

logger = get_logger(__name__)

_GQL_URL = "https://gql.tokopedia.com/"
_MIN_DELAY = 2.0


class TokopediaScraper(BaseScraper):
    """Scrapes Tokopedia via GraphQL API — fast, no browser overhead."""

    SEARCH_URL = "https://www.tokopedia.com/search?st=product&q={keyword}&page={page}"

    def __init__(self):
        super().__init__()

    async def scrape_search(self, keyword: str, max_pages: int = 3) -> list[dict]:
        results: list[dict] = []
        for page_num in range(1, max_pages + 1):
            try:
                products = await self._gql_search(keyword, page_num)
                results.extend(products)
                logger.info(f"[Tokopedia] Page {page_num}: {len(products)} products")
                if not products:
                    break
                await asyncio.sleep(random.uniform(_MIN_DELAY, _MIN_DELAY + 2))
            except Exception as exc:
                logger.error(f"[Tokopedia] Page {page_num} failed: {exc}")
                break
        return results

    async def scrape_product(self, url: str) -> dict:
        """Fallback to Playwright for product detail."""
        page = await self._get_page(url, wait_until="domcontentloaded")
        try:
            return await self._extract_product_detail(page, url)
        finally:
            await page.context.close()

    async def _gql_search(self, keyword: str, page: int) -> list[dict]:
        """Query Tokopedia SearchProductV5 GraphQL endpoint."""
        proxy = self.proxy_manager.get_proxy()
        mounts = None
        if proxy:
            proxy_url = f"http://{proxy['user']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
            mounts = {"https://": httpx.AsyncHTTPTransport(proxy=proxy_url)}

        headers = {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Referer": f"https://www.tokopedia.com/search?q={quote(keyword)}",
            "Origin": "https://www.tokopedia.com",
            "X-Source": "tokopedia-lite",
            "X-Tkpd-Lite-Service": "zeus",
        }

        payload = [{
            "operationName": "SearchProductQueryV4",
            "variables": {
                "params": f"device=desktop&navsource=home&ob=23&page={page}&q={quote(keyword)}&related=true&rows=60&safe_search=false&scheme=https&source=search&srp_component_id=02.01.00.00&st=product&topads_bucket=true"
            },
            "query": "query SearchProductQueryV4($params: String) { searchProductV4(params: $params) { data { products { id name url imageUrl price ratingAverage labelGroups { position title } shop { id name city } stats { reviewCount } } } } }"
        }]

        try:
            client_kwargs = {"timeout": 30.0, "follow_redirects": True}
            if mounts:
                client_kwargs["mounts"] = mounts
            async with httpx.AsyncClient(**client_kwargs) as client:
                resp = await client.post(_GQL_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                logger.info(f"[Tokopedia] GQL status={resp.status_code} response_preview={str(data)[:300]}")

            if not data or not isinstance(data, list) or data[0] is None:
                logger.error(f"[Tokopedia] GQL unexpected response: {data}")
                return []

            products_raw = (
                data[0].get("data", {})
                .get("searchProductV4", {})
                .get("data", {})
                .get("products", [])
            )
            return [self._parse_gql_product(p) for p in products_raw if p.get("name")]

        except Exception as exc:
            logger.error(f"[Tokopedia] GQL error: {exc}")
            return []

    def _parse_gql_product(self, p: dict) -> dict:
        price_idr = parse_idr_string(p.get("price", "0"))
        sold_raw = ""
        for label in p.get("labelGroups", []):
            if label.get("position") == "integrity":
                sold_raw = label.get("title", "")
                break
        sold_30d = parse_sold_count(sold_raw)

        try:
            rating = float(p.get("ratingAverage", 0) or 0)
            rating = rating if 0 < rating <= 5 else None
        except (ValueError, TypeError):
            rating = None

        shop = p.get("shop", {})
        stats = p.get("stats", {})

        return {
            "platform": "tokopedia",
            "platform_product_id": str(p.get("id", "")),
            "title": p.get("name", ""),
            "url": p.get("url", ""),
            "image_url": p.get("imageUrl", ""),
            "price_idr": price_idr,
            "sold_count": sold_30d,
            "sold_30d": sold_30d,
            "review_count": stats.get("reviewCount", 0) or 0,
            "rating": rating,
            "seller_name": shop.get("name", ""),
            "seller_city": shop.get("city", ""),
            "seller_badge": "",
        }

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
                logger.warning(f"[Tokopedia] DB save error for '{item.get('title', '')[:40]}': {exc}")
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
