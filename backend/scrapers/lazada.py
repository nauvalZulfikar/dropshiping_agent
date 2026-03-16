"""
Lazada scraper — Phase 2 stub.
Full implementation in Phase 2 extension or Phase 7 polish.
"""
from scrapers.base_scraper import BaseScraper
from utils.logger import get_logger

logger = get_logger(__name__)


class LazadaScraper(BaseScraper):
    """Lazada Indonesia scraper (stub — full implementation TODO)."""

    SEARCH_URL = "https://www.lazada.co.id/catalog/?q={keyword}&page={page}"

    async def scrape_search(self, keyword: str, max_pages: int = 3) -> list[dict]:
        logger.warning("[Lazada] Scraper not yet implemented. Returning empty list.")
        return []

    async def scrape_product(self, url: str) -> dict:
        logger.warning("[Lazada] scrape_product not yet implemented.")
        return {}
