"""
1688.com scraper — Chinese B2B supplier source.
Phase 2 stub. Requires Chinese IP or CN proxy to access reliably.
Full implementation in Phase 3 (supplier matching phase).
"""
from scrapers.base_scraper import BaseScraper
from utils.logger import get_logger

logger = get_logger(__name__)


class Source1688Scraper(BaseScraper):
    """1688.com scraper for Chinese wholesale supplier prices (stub)."""

    SEARCH_URL = "https://s.1688.com/selloffer/offer_search.htm?keywords={keyword}"

    async def scrape_search(self, keyword: str, max_pages: int = 3) -> list[dict]:
        logger.warning("[1688] Scraper not yet implemented. Returning empty list.")
        return []

    async def scrape_product(self, url: str) -> dict:
        logger.warning("[1688] scrape_product not yet implemented.")
        return {}
