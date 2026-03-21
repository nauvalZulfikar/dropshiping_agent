"""
AliExpress scraper.
Saves to suppliers table (not product_listings).
Converts USD prices → IDR using live Bank Indonesia rate.
CAPTCHA detection: marks proxy as blocked, switches proxy, retries.
"""
import asyncio
import json
import re
from typing import Optional
from urllib.parse import quote

import asyncpg

from scrapers.base_scraper import BaseScraper
from utils.currency import usd_to_idr, fetch_usd_to_idr_rate
from utils.logger import get_logger

logger = get_logger(__name__)

_MAX_CAPTCHA_RETRIES = 3


class AliExpressScraper(BaseScraper):
    """Scrapes AliExpress search results and saves to suppliers table."""

    SEARCH_URL = "https://www.aliexpress.com/w/wholesale-{keyword}.html"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def scrape_search(self, keyword: str, max_results: int = 20) -> list[dict]:
        """
        Scrape AliExpress wholesale search for supplier products.
        Returns list of supplier dicts.
        """
        slug = keyword.strip().replace(" ", "-")
        url = self.SEARCH_URL.format(keyword=quote(slug, safe="-"))
        logger.info(f"[AliExpress] Scraping: {url}")

        # Fetch live exchange rate once
        rate = await fetch_usd_to_idr_rate()

        for attempt in range(_MAX_CAPTCHA_RETRIES):
            try:
                results = await self._scrape_search_page(url, rate, max_results)
                logger.info(f"[AliExpress] Got {len(results)} suppliers")
                await self.close()
                return results
            except CaptchaError as exc:
                logger.warning(f"[AliExpress] CAPTCHA attempt {attempt + 1}: {exc}")
                if attempt < _MAX_CAPTCHA_RETRIES - 1:
                    await asyncio.sleep(5)
                    continue
                logger.error("[AliExpress] Max CAPTCHA retries exceeded")
                break
            except Exception as exc:
                logger.error(f"[AliExpress] Scrape error: {exc}")
                break

        await self.close()
        return []

    async def scrape_product(self, url: str) -> dict:
        """Scrape AliExpress product detail page."""
        rate = await fetch_usd_to_idr_rate()
        page = await self._get_page(url, wait_until="domcontentloaded")
        try:
            await self._random_delay(2.0, 4.0)
            content = await page.content()
            if self._detect_captcha(content):
                raise CaptchaError("CAPTCHA on product page")
            return await self._extract_product_detail(page, url, rate)
        finally:
            await page.context.close()

    # ------------------------------------------------------------------
    # Search page
    # ------------------------------------------------------------------

    async def _scrape_search_page(self, url: str, rate: float, max_results: int) -> list[dict]:
        page = await self._get_page(url, wait_until="domcontentloaded")
        try:
            # Human-like scroll to trigger lazy-load rendering
            await self._random_delay(3.0, 5.0)
            await self._human_scroll(page)
            await self._random_delay(2.0, 3.0)

            # Check for product cards after scroll
            try:
                await page.wait_for_selector(".search-item-card-wrapper-gallery", timeout=8_000)
                has_cards = True
            except Exception:
                has_cards = False

            if not has_cards:
                content = await page.content()
                # Only raise if actual CAPTCHA challenge — AliExpress JS contains "captcha" string normally
                if "slide to verify" in content.lower() or "verify your identity" in content.lower():
                    await page.context.close()
                    raise CaptchaError("CAPTCHA on search page")

            # Try JSON embedded data first (faster)
            products = await self._try_extract_json(page, rate)
            if not products:
                # DOM fallback
                products = await self._extract_dom(page, rate)

            return products[:max_results]
        finally:
            try:
                await page.context.close()
            except Exception:
                pass

    async def _try_extract_json(self, page, rate: float) -> list[dict]:
        """Try to extract product data from AliExpress embedded JS."""
        try:
            data_str = await page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    for (const s of scripts) {
                        const t = s.textContent || '';
                        if (t.includes('runParams') && t.includes('items')) {
                            const match = t.match(/runParams\\s*=\\s*({.+?});/s);
                            return match ? match[1] : null;
                        }
                    }
                    return null;
                }
            """)
            if not data_str:
                return []

            data = json.loads(data_str)
            items = data.get("mods", {}).get("itemList", {}).get("content", [])
            return [self._normalize_ae_item(item, rate) for item in items if item]
        except Exception as exc:
            logger.debug(f"[AliExpress] JSON extract failed: {exc}")
            return []

    async def _extract_dom(self, page, rate: float) -> list[dict]:
        """DOM-based fallback extraction for AliExpress search cards."""
        cards = await page.query_selector_all(".search-item-card-wrapper-gallery")
        results = []
        for card in cards:
            try:
                p = await self._parse_card_dom(card, rate)
                if p:
                    results.append(p)
            except Exception as exc:
                logger.debug(f"[AliExpress] DOM card error: {exc}")
        return results

    async def _parse_card_dom(self, card, rate: float) -> Optional[dict]:
        # Link & product ID — extract product ID from any aliexpress subdomain URL
        html = await card.inner_html()
        url_matches = re.findall(r'href="((?:https?:)?//[a-z]+\.aliexpress\.com/item/[^"?]+)', html)
        product_url = url_matches[0] if url_matches else ""
        if product_url.startswith("//"):
            product_url = f"https:{product_url}"
        source_product_id = _extract_ae_product_id(product_url)
        # Normalize to www.aliexpress.com to avoid 404 on regional subdomains
        if source_product_id:
            product_url = f"https://www.aliexpress.com/item/{source_product_id}.html"

        # Title
        title_el = await card.query_selector("h3")
        if not title_el:
            title_el = await card.query_selector("[class*='title']")
        title = (await title_el.text_content()).strip() if title_el else ""
        if not title:
            return None

        # Price — parse from raw HTML (AliExpress price not in predictable CSS class)
        price_idr = 0
        price_usd = 0.0
        rp_prices = re.findall(r"Rp\s*[\d,.]+", html)
        if rp_prices:
            price_idr = _parse_idr(rp_prices[0])
        else:
            usd_prices = re.findall(r"US\$\s*[\d,.]+", html)
            if usd_prices:
                price_usd = _parse_usd(usd_prices[0])
                price_idr = usd_to_idr(price_usd, rate)

        # Rating — match 1.0-5.0 range
        rating = None
        rating_matches = re.findall(r"\b([1-5]\.\d)\b", html)
        if rating_matches:
            rating = float(rating_matches[0])

        # Sold count — look for patterns like "500+ sold" or "1000 sold"
        review_count = 0
        sold_matches = re.findall(r"([\d,]+)\+?\s*(?:sold|terjual|orders?)", html, re.IGNORECASE)
        if sold_matches:
            review_count = _parse_int_first(sold_matches[0]) or 0

        # Image
        img_el = await card.query_selector("img")
        image_url = await img_el.get_attribute("src") if img_el else ""
        if not image_url:
            image_url = await img_el.get_attribute("data-src") if img_el else ""
        if image_url and image_url.startswith("//"):
            image_url = f"https:{image_url}"

        return {
            "source": "aliexpress",
            "source_product_id": source_product_id,
            "title": title,
            "url": product_url,
            "image_url": image_url,
            "price_usd": price_usd,
            "price_idr": price_idr,
            "shipping_cost_idr": 0,
            "moq": 1,
            "seller_name": "",
            "rating": rating,
            "review_count": review_count,
        }

    def _normalize_ae_item(self, item: dict, rate: float) -> dict:
        """Normalize AliExpress JSON item to supplier schema."""
        price_raw = item.get("prices", {}).get("salePrice", {}).get("minPrice", "0")
        price_usd = _parse_usd(str(price_raw))
        price_idr = usd_to_idr(price_usd, rate)

        trade_raw = item.get("trade", {})
        sold_count = trade_raw.get("tradeCount", 0)

        sku = item.get("productId", "")
        title = item.get("title", {}).get("displayTitle", "") or item.get("title", "")
        if isinstance(title, dict):
            title = title.get("displayTitle", "")

        image_url = ""
        images = item.get("image", {}).get("imgUrl", "")
        if images:
            image_url = f"https:{images}" if images.startswith("//") else images

        url = item.get("productDetailUrl", "")
        if url and not url.startswith("http"):
            url = f"https:{url}"

        seller_name = item.get("store", {}).get("storeName", "")
        rating = item.get("evaluation", {}).get("starRating", None)
        if rating:
            rating = float(rating)

        return {
            "source": "aliexpress",
            "source_product_id": str(sku),
            "title": title,
            "url": url,
            "image_url": image_url,
            "price_usd": price_usd,
            "price_idr": price_idr,
            "shipping_cost_idr": 0,  # fetch from product detail for accuracy
            "moq": 1,
            "seller_name": seller_name,
            "rating": rating,
            "sold_count": sold_count,
        }

    # ------------------------------------------------------------------
    # Product detail
    # ------------------------------------------------------------------

    async def _extract_product_detail(self, page, url: str, rate: float) -> dict:
        title = await self._safe_text(page, "h1.product-title-text")
        if not title:
            title = await self._safe_text(page, "h1")

        price_raw = await self._safe_text(page, ".product-price-value")
        price_usd = _parse_usd(price_raw)
        price_idr = usd_to_idr(price_usd, rate)

        shipping_raw = await self._safe_text(page, ".product-shipping-price")
        shipping_usd = _parse_usd(shipping_raw) if "free" not in shipping_raw.lower() else 0.0
        shipping_idr = usd_to_idr(shipping_usd, rate)

        shipping_days_raw = await self._safe_text(page, ".delivery-time")
        shipping_days = _parse_int_first(shipping_days_raw)

        rating_raw = await self._safe_text(page, ".overview-rating-average")
        rating = _parse_float(rating_raw)

        seller_name = await self._safe_text(page, ".shop-name")
        img_url = await self._safe_attr(page, ".magnifier-image", "src")

        # MOQ
        moq_raw = await self._safe_text(page, ".min-order")
        moq = _parse_int_first(moq_raw) or 1

        product_id = _extract_ae_product_id(url)

        return {
            "source": "aliexpress",
            "source_product_id": product_id,
            "title": title,
            "url": url,
            "image_url": img_url,
            "price_usd": price_usd,
            "price_idr": price_idr,
            "shipping_cost_idr": shipping_idr,
            "shipping_days_estimate": shipping_days,
            "moq": moq,
            "seller_name": seller_name,
            "rating": rating,
        }


# ------------------------------------------------------------------
# DB persistence helper
# ------------------------------------------------------------------

async def save_suppliers_to_db(db_url: str, suppliers: list[dict], product_id: Optional[str] = None) -> int:
    """
    Upsert AliExpress supplier rows into the suppliers table.
    product_id links the supplier to a canonical product (optional at save time).
    """
    if not suppliers:
        return 0
    conn = await asyncpg.connect(db_url)
    try:
        saved = 0
        for s in suppliers:
            if not s.get("title"):
                continue
            try:
                await conn.execute("""
                    INSERT INTO suppliers (
                        product_id, source, source_product_id,
                        title, url, image_url,
                        price_usd, price_idr, shipping_cost_idr,
                        shipping_days_estimate, moq,
                        seller_name, rating,
                        scraped_at
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,NOW())
                    ON CONFLICT (source, title) DO UPDATE SET
                        price_idr = EXCLUDED.price_idr,
                        price_usd = EXCLUDED.price_usd,
                        rating = EXCLUDED.rating,
                        scraped_at = NOW()
                """,
                product_id,
                s.get("source", "aliexpress"),
                s.get("source_product_id"),
                s["title"],
                s.get("url"),
                s.get("image_url"),
                s.get("price_usd"),
                s.get("price_idr"),
                s.get("shipping_cost_idr", 0),
                s.get("shipping_days_estimate"),
                s.get("moq", 1),
                s.get("seller_name"),
                s.get("rating"),
                )
                saved += 1
            except Exception as exc:
                logger.warning(f"[AliExpress] DB save error for '{s.get('title','')[:40]}': {exc}")
        return saved
    finally:
        await conn.close()


# ------------------------------------------------------------------
# Custom exceptions
# ------------------------------------------------------------------

class CaptchaError(RuntimeError):
    pass


# ------------------------------------------------------------------
# Parsing helpers
# ------------------------------------------------------------------

def _parse_idr(raw: str) -> int:
    """Parse IDR string like 'Rp78,445' → 78445."""
    try:
        clean = re.sub(r"[^\d]", "", raw)
        return int(clean) if clean else 0
    except (ValueError, TypeError):
        return 0


def _parse_usd(raw: str) -> float:
    try:
        clean = re.sub(r"[^\d.]", "", raw.replace(",", ""))
        return float(clean) if clean else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_float(raw: str) -> Optional[float]:
    try:
        clean = re.sub(r"[^\d.]", "", raw)
        return float(clean) if clean else None
    except (ValueError, TypeError):
        return None


def _parse_int_from_parentheses(raw: str) -> int:
    """Extract number from format like '4.8 (1234)'."""
    match = re.search(r"\((\d+)\)", raw)
    return int(match.group(1)) if match else 0


def _parse_int_first(raw: str) -> Optional[int]:
    match = re.search(r"\d+", raw)
    return int(match.group()) if match else None


def _extract_ae_product_id(url: str) -> Optional[str]:
    match = re.search(r"/(\d+)\.html", url)
    return match.group(1) if match else None
