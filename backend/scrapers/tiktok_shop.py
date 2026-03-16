"""
TikTok Shop scraper — Phase 2 stub.
TikTok Shop uses aggressive bot detection and requires valid session cookies.
Full implementation planned for Phase 6 (automation phase).
Strategy: use TikTok Shop API endpoints intercepted via Playwright network events.
"""
from scrapers.base_scraper import BaseScraper
from utils.logger import get_logger

logger = get_logger(__name__)


class TikTokShopScraper(BaseScraper):
    """TikTok Shop Indonesia scraper (stub — full implementation TODO)."""

    SEARCH_URL = "https://shop.tiktok.com/search?keyword={keyword}"

    async def scrape_search(self, keyword: str, max_pages: int = 3) -> list[dict]:
        logger.warning("[TikTokShop] Scraper not yet implemented. Returning empty list.")
        return []

    async def scrape_product(self, url: str) -> dict:
        logger.warning("[TikTokShop] scrape_product not yet implemented.")
        return {}
