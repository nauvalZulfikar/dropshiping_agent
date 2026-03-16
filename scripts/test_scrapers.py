"""
Manual smoke test for all scrapers.
Run: python scripts/test_scrapers.py

Tests:
1. Trigger Tokopedia scrape for "tas wanita"
2. Wait for task to complete
3. Verify products saved to DB
4. Verify scores computed
5. Verify health endpoint
"""
import asyncio
import httpx
import asyncpg
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")
DB_URL = os.getenv("DATABASE_URL", "")


async def test_health():
    print("\n--- Health Check ---")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/api/health", timeout=10)
        data = resp.json()
        print(f"Status: {data['status']}")
        print(f"DB: {data['db']}")
        print(f"Redis: {data['redis']}")
        assert data["status"] in ("ok", "degraded"), f"Unexpected health status: {data}"
        print("PASS: Health endpoint responding")


async def test_trigger_scrape(keyword: str = "tas wanita") -> str:
    print(f"\n--- Trigger Tokopedia Scrape: '{keyword}' ---")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/api/scraper/trigger",
            json={"source": "tokopedia", "keyword": keyword, "max_pages": 1},
            timeout=10,
        )
        data = resp.json()
        task_id = data.get("task_id", "")
        print(f"Task ID: {task_id}")
        assert task_id, "No task_id returned"
        print("PASS: Scrape task enqueued")
        return task_id


async def wait_for_task(task_id: str, timeout: int = 120) -> bool:
    print(f"\n--- Waiting for task {task_id} ---")
    async with httpx.AsyncClient() as client:
        start = time.time()
        while time.time() - start < timeout:
            resp = await client.get(f"{API_BASE}/api/scraper/status/{task_id}", timeout=10)
            data = resp.json()
            status = data.get("status", "UNKNOWN")
            print(f"  Status: {status}")
            if status == "SUCCESS":
                print("PASS: Task completed successfully")
                return True
            if status in ("FAILURE", "REVOKED"):
                print(f"FAIL: Task ended with status {status}")
                return False
            await asyncio.sleep(5)
    print(f"FAIL: Task did not complete within {timeout}s")
    return False


async def test_db_has_products():
    print("\n--- Verify DB has product rows ---")
    if not DB_URL:
        print("SKIP: DATABASE_URL not configured")
        return
    conn = await asyncpg.connect(DB_URL)
    try:
        count = await conn.fetchval("SELECT COUNT(*) FROM product_listings WHERE platform = 'tokopedia'")
        print(f"Tokopedia listings in DB: {count}")
        assert count and count > 0, "No Tokopedia products found in DB"
        print("PASS: Products saved to DB")
    finally:
        await conn.close()


async def test_scores_computed():
    print("\n--- Verify scores computed in DB ---")
    if not DB_URL:
        print("SKIP: DATABASE_URL not configured")
        return
    conn = await asyncpg.connect(DB_URL)
    try:
        count = await conn.fetchval("""
            SELECT COUNT(*)
            FROM product_scores ps
            JOIN product_listings pl ON pl.id = ps.listing_id
            WHERE pl.platform = 'tokopedia'
              AND ps.opportunity_score IS NOT NULL
        """)
        print(f"Scored Tokopedia listings: {count}")
        if count and count > 0:
            print("PASS: Scores computed")
        else:
            print("WARN: No scores yet — scoring runs async, check again in ~30s")
    finally:
        await conn.close()


async def test_products_api():
    print("\n--- Verify /api/products returns data ---")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/api/products?platform=tokopedia&limit=5", timeout=10)
        assert resp.status_code == 200, f"Unexpected status {resp.status_code}"
        data = resp.json()
        items = data.get("items", [])
        total = data.get("total", 0)
        print(f"Total listings: {total} | Returned: {len(items)}")
        if items:
            p = items[0]
            print(f"  First: {p.get('title', '')[:60]}")
            print(f"  Score: {p.get('opportunity_score')} | Margin: {p.get('margin_pct')}%")
        print("PASS: Products API responding")


async def test_dashboard_summary():
    print("\n--- Verify /api/analytics/summary ---")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/api/analytics/summary", timeout=10)
        assert resp.status_code == 200, f"Unexpected status {resp.status_code}"
        data = resp.json()
        print(f"  Total listings: {data.get('total_listings', 0)}")
        print(f"  Gate passed: {data.get('gate_passed_count', 0)}")
        print(f"  Avg margin: {data.get('avg_margin_pct', 0)}%")
        print("PASS: Analytics summary responding")


async def main():
    print("=" * 60)
    print("Dropship Research — Scraper Smoke Test")
    print("=" * 60)

    try:
        await test_health()
        task_id = await test_trigger_scrape("tas wanita")
        success = await wait_for_task(task_id, timeout=120)
        if success:
            await asyncio.sleep(5)  # brief wait for DB write + scoring trigger
            await test_db_has_products()
            await test_scores_computed()
            await test_products_api()
            await test_dashboard_summary()
        print("\n" + "=" * 60)
        print("All tests passed!" if success else "Some tests failed.")
    except AssertionError as exc:
        print(f"\nFAIL: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
