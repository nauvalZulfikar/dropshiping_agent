"""
Abstract base class for all marketplace scrapers.
Uses Playwright async API + playwright-stealth for bot avoidance.
"""
import asyncio
import random
import logging
from abc import ABC, abstractmethod
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from scrapers.proxy_manager import ProxyManager
from utils.logger import get_logger

logger = get_logger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all platform scrapers.
    Subclasses must implement scrape_search() and scrape_product().
    """

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    ]

    VIEWPORT_SIZES = [
        {"width": 1920, "height": 1080},
        {"width": 1440, "height": 900},
        {"width": 1366, "height": 768},
        {"width": 1280, "height": 800},
    ]

    def __init__(self):
        self.proxy_manager = ProxyManager()
        self._browser: Optional[Browser] = None
        self._playwright = None

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def scrape_search(self, keyword: str, max_pages: int = 3) -> list[dict]:
        """Scrape search results for a keyword. Returns list of product dicts."""
        ...

    @abstractmethod
    async def scrape_product(self, url: str) -> dict:
        """Scrape full detail for a single product URL. Returns product dict."""
        ...

    # ------------------------------------------------------------------
    # Browser lifecycle
    # ------------------------------------------------------------------

    async def _get_browser(self) -> Browser:
        if self._browser is None or not self._browser.is_connected():
            self._playwright = await async_playwright().start()
            launch_kwargs = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            }
            proxy = self.proxy_manager.get_proxy()
            if proxy:
                launch_kwargs["proxy"] = {
                    "server": f"http://{proxy['host']}:{proxy['port']}",
                    "username": proxy.get("user", ""),
                    "password": proxy.get("password", ""),
                }
            self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        return self._browser

    async def _new_context(self) -> BrowserContext:
        browser = await self._get_browser()
        ua = random.choice(self.USER_AGENTS)
        vp = random.choice(self.VIEWPORT_SIZES)

        context = await browser.new_context(
            user_agent=ua,
            viewport=vp,
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            extra_http_headers={
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )

        # Apply stealth patches to avoid bot detection
        try:
            from playwright_stealth import stealth_async
            page = await context.new_page()
            await stealth_async(page)
            await page.close()
        except ImportError:
            logger.warning("playwright-stealth not installed; running without stealth")

        return context

    async def _get_page(self, url: str, wait_until: str = "domcontentloaded") -> Page:
        """
        Open a new page, navigate to URL, apply stealth.
        Rotates proxy per context. Uses random UA + viewport.
        """
        context = await self._new_context()
        page = await context.new_page()

        # Apply stealth to the actual page
        try:
            from playwright_stealth import stealth_async
            await stealth_async(page)
        except ImportError:
            pass

        try:
            await page.goto(url, wait_until=wait_until, timeout=30_000)
        except Exception as exc:
            logger.warning(f"Navigation to {url} failed: {exc}")
            await page.close()
            await context.close()
            raise

        return page

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _random_delay(self, min_s: float = 2.0, max_s: float = 6.0):
        """Async sleep for a random duration to mimic human browsing."""
        delay = random.uniform(min_s, max_s)
        await asyncio.sleep(delay)

    async def _human_scroll(self, page: Page):
        """Scroll page slowly like a human to trigger lazy-load and avoid bot detection."""
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(300, 700))
            await asyncio.sleep(random.uniform(0.3, 0.8))

    def _detect_captcha(self, content: str) -> bool:
        """Heuristic check for CAPTCHA pages."""
        indicators = ["captcha", "robot", "verify you are human", "cf-challenge", "recaptcha"]
        lower = content.lower()
        return any(i in lower for i in indicators)

    async def _safe_text(self, page: Page, selector: str, default: str = "") -> str:
        """Extract text from a selector, returning default if not found."""
        try:
            el = page.locator(selector).first
            return (await el.text_content(timeout=3000) or "").strip()
        except Exception:
            return default

    async def _safe_attr(self, page: Page, selector: str, attr: str, default: str = "") -> str:
        """Extract an attribute from a selector, returning default if not found."""
        try:
            el = page.locator(selector).first
            return (await el.get_attribute(attr, timeout=3000) or "").strip()
        except Exception:
            return default
