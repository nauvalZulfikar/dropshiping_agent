"""
Celery scraping tasks.
Scrapers use asyncio.run() since Playwright is async but Celery workers are sync.
Each task:
1. Runs the scraper
2. Saves results to DB
3. Logs to scraper_jobs table
4. Triggers scoring for new listings
"""
import asyncio
import logging
import uuid

from celery import group

from tasks.celery_app import celery_app
from config import settings

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Individual scraper tasks
# ------------------------------------------------------------------

@celery_app.task(name="tasks.scrape_tasks.scrape_tokopedia", bind=True, max_retries=3)
def scrape_tokopedia(self, keyword: str, max_pages: int = 3):
    """Scrape Tokopedia search results and save to DB."""
    try:
        return asyncio.run(_scrape_and_save_tokopedia(keyword, max_pages))
    except Exception as exc:
        logger.error(f"[Tokopedia] Task failed for '{keyword}': {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="tasks.scrape_tasks.scrape_shopee", bind=True, max_retries=3)
def scrape_shopee(self, keyword: str, max_pages: int = 3):
    """Scrape Shopee search results and save to DB."""
    try:
        return asyncio.run(_scrape_and_save_shopee(keyword, max_pages))
    except Exception as exc:
        logger.error(f"[Shopee] Task failed for '{keyword}': {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="tasks.scrape_tasks.scrape_aliexpress", bind=True, max_retries=3)
def scrape_aliexpress(self, keyword: str, max_results: int = 20):
    """Scrape AliExpress for supplier prices and save to DB."""
    try:
        return asyncio.run(_scrape_and_save_aliexpress(keyword, max_results))
    except Exception as exc:
        logger.error(f"[AliExpress] Task failed for '{keyword}': {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="tasks.scrape_tasks.full_scan")
def full_scan(keywords: list[str]):
    """Run all 3 scrapers per keyword in parallel using Celery group."""
    tasks = []
    for keyword in keywords:
        tasks.extend([
            # scrape_tokopedia.s(keyword),  # disabled: proxy tunnel blocked
            # scrape_shopee.s(keyword),      # disabled: proxy tunnel blocked
            scrape_aliexpress.s(keyword),
        ])
    job = group(tasks)
    result = job.apply_async()
    return {"group_id": result.id, "keyword_count": len(keywords), "task_count": len(tasks)}


@celery_app.task(name="tasks.scrape_tasks.monitor_price_changes")
def monitor_price_changes():
    """Re-scrape watchlisted products and record price changes."""
    return asyncio.run(_monitor_price_changes_async())


# ------------------------------------------------------------------
# Async implementation functions
# ------------------------------------------------------------------

async def _scrape_and_save_tokopedia(keyword: str, max_pages: int) -> dict:
    from scrapers.tokopedia import TokopediaScraper, save_listings_to_db

    job_id = await _log_job_start("tokopedia", "full_scan")
    try:
        scraper = TokopediaScraper()
        listings = await scraper.scrape_search(keyword, max_pages)
        saved = await save_listings_to_db(settings.database_url, listings, job_id)
        await _log_job_done(job_id, "success", items_scraped=len(listings))

        # Trigger scoring for new listings
        from tasks.score_tasks import score_all_products
        score_all_products.apply_async(countdown=15)

        logger.info(f"[Tokopedia] '{keyword}': scraped={len(listings)}, saved={saved}")
        return {"source": "tokopedia", "keyword": keyword, "scraped": len(listings), "saved": saved}
    except Exception as exc:
        await _log_job_done(job_id, "failed", error=str(exc))
        raise


async def _scrape_and_save_shopee(keyword: str, max_pages: int) -> dict:
    from scrapers.shopee import ShopeeScraper, save_listings_to_db

    job_id = await _log_job_start("shopee", "full_scan")
    try:
        scraper = ShopeeScraper()
        listings = await scraper.scrape_search(keyword, max_pages)
        saved = await save_listings_to_db(settings.database_url, listings)
        await _log_job_done(job_id, "success", items_scraped=len(listings))

        from tasks.score_tasks import score_all_products
        score_all_products.apply_async(countdown=15)

        logger.info(f"[Shopee] '{keyword}': scraped={len(listings)}, saved={saved}")
        return {"source": "shopee", "keyword": keyword, "scraped": len(listings), "saved": saved}
    except Exception as exc:
        await _log_job_done(job_id, "failed", error=str(exc))
        raise


async def _scrape_and_save_aliexpress(keyword: str, max_results: int) -> dict:
    from scrapers.aliexpress import AliExpressScraper, save_suppliers_to_db

    job_id = await _log_job_start("aliexpress", "full_scan")
    try:
        scraper = AliExpressScraper()
        suppliers = await scraper.scrape_search(keyword, max_results)
        saved = await save_suppliers_to_db(settings.database_url, suppliers)
        await _log_job_done(job_id, "success", items_scraped=len(suppliers))

        logger.info(f"[AliExpress] '{keyword}': scraped={len(suppliers)}, saved={saved}")
        return {"source": "aliexpress", "keyword": keyword, "scraped": len(suppliers), "saved": saved}
    except Exception as exc:
        await _log_job_done(job_id, "failed", error=str(exc))
        raise


async def _monitor_price_changes_async() -> dict:
    import asyncpg
    from scrapers.tokopedia import TokopediaScraper
    from scrapers.shopee import ShopeeScraper

    # Use a pool so we don't reconnect for every single row update
    pool = await asyncpg.create_pool(settings.asyncpg_url, min_size=1, max_size=3)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT
                    pl.id, pl.url, pl.platform,
                    pl.price_idr, pl.sold_30d
                FROM watchlists w
                JOIN product_listings pl ON pl.id = w.listing_id
                WHERE pl.is_active = TRUE AND pl.url IS NOT NULL
            """)
    except Exception as exc:
        logger.error(f"[monitor_price_changes] DB fetch failed: {exc}")
        await pool.close()
        return {"updated": 0, "checked": 0, "error": str(exc)}

    scraper_map: dict = {
        "tokopedia": TokopediaScraper(),
        "shopee": ShopeeScraper(),
    }

    updated = 0
    alert_needed = False

    for row in rows:
        scraper = scraper_map.get(row["platform"])
        if not scraper:
            continue
        try:
            data = await scraper.scrape_product(row["url"])
            new_price = data.get("price_idr") or 0
            new_sold  = data.get("sold_count") or data.get("sold_30d") or 0
            old_price = row["price_idr"] or 0
            old_sold  = row["sold_30d"] or 0

            price_changed = old_price > 0 and abs(new_price - old_price) / old_price > 0.02
            sold_changed  = old_sold > 0 and abs(new_sold - old_sold) / old_sold > 0.10

            if price_changed or sold_changed:
                async with pool.acquire() as conn:
                    await conn.execute("""
                        INSERT INTO price_history (listing_id, price_idr, sold_count)
                        VALUES ($1, $2, $3)
                    """, row["id"], new_price, new_sold)
                    await conn.execute("""
                        UPDATE product_listings
                        SET price_idr = $1, sold_30d = $2, scraped_at = NOW()
                        WHERE id = $3
                    """, new_price, new_sold, row["id"])
                updated += 1

                # Trigger alert if price dropped >5% or sold spiked >50%
                if old_price > 0 and (old_price - new_price) / old_price > 0.05:
                    alert_needed = True
                if old_sold > 0 and (new_sold - old_sold) / old_sold > 0.50:
                    alert_needed = True

        except Exception as exc:
            logger.warning(f"[monitor] listing {row['id']} failed: {exc}")

    await pool.close()

    if alert_needed:
        from tasks.alert_tasks import send_watchlist_alerts
        send_watchlist_alerts.delay()

    return {"updated": updated, "checked": len(rows)}


# ------------------------------------------------------------------
# Scraper job logging helpers
# ------------------------------------------------------------------

async def _log_job_start(source: str, job_type: str) -> str:
    """Insert a scraper_jobs row and return its string ID."""
    try:
        import asyncpg
        conn = await asyncpg.connect(settings.asyncpg_url)
        try:
            row = await conn.fetchrow("""
                INSERT INTO scraper_jobs (source, job_type, status, started_at)
                VALUES ($1, $2, 'running', NOW())
                RETURNING id
            """, source, job_type)
            return str(row["id"])
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning(f"Could not log job start: {exc}")
        return str(uuid.uuid4())


async def _log_job_done(job_id: str, status: str, items_scraped: int = 0, error: str | None = None):
    """Update a scraper_jobs row with completion status."""
    try:
        import asyncpg
        conn = await asyncpg.connect(settings.asyncpg_url)
        try:
            await conn.execute("""
                UPDATE scraper_jobs
                SET status = $1, items_scraped = $2, error_message = $3, finished_at = NOW()
                WHERE id = $4
            """, status, items_scraped, error, job_id)
        finally:
            await conn.close()
    except Exception as exc:
        logger.warning(f"Could not log job completion: {exc}")
