"""
Trend engine: fetches Google Trends data via pytrends + caches in Redis.
Also persists trend signals to the trend_signals DB table.
"""
import asyncio
import json
import logging
from typing import Optional

import asyncpg
import redis.asyncio as aioredis
from pytrends.request import TrendReq

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

_CACHE_TTL_SECONDS = 6 * 3600  # 6 hours
_GEO = "ID"
_TIMEFRAME = "today 3-m"


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

async def get_trend_score(keyword: str) -> int:
    """
    Return the latest Google Trends interest value (0–100) for a keyword in Indonesia.
    Results are cached in Redis for 6 hours to avoid rate limiting pytrends.
    """
    cache_key = f"trend:score:{keyword.lower().strip()}"

    # Try Redis cache first
    cached = await _cache_get(cache_key)
    if cached is not None:
        logger.debug(f"[Trends] Cache hit: '{keyword}' = {cached}")
        return int(cached)

    # Fetch from pytrends (blocking — run in executor)
    score = await asyncio.get_event_loop().run_in_executor(
        None, _fetch_trend_score_sync, keyword
    )

    # Cache the result
    await _cache_set(cache_key, str(score), ttl=_CACHE_TTL_SECONDS)

    # Persist to DB (fire-and-forget)
    asyncio.create_task(_save_trend_signal(keyword, score))

    return score


async def get_related_queries(keyword: str) -> list[str]:
    """
    Return rising related queries for a keyword in Indonesia.
    Useful for keyword discovery.
    """
    cache_key = f"trend:related:{keyword.lower().strip()}"
    cached = await _cache_get(cache_key)
    if cached:
        return json.loads(cached)

    queries = await asyncio.get_event_loop().run_in_executor(
        None, _fetch_related_queries_sync, keyword
    )

    await _cache_set(cache_key, json.dumps(queries), ttl=_CACHE_TTL_SECONDS)
    return queries


async def get_trend_direction(keyword: str) -> str:
    """
    Compare 30-day avg vs 90-day avg to determine direction.
    Returns 'rising', 'stable', or 'declining'.
    """
    cache_key = f"trend:direction:{keyword.lower().strip()}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    direction = await asyncio.get_event_loop().run_in_executor(
        None, _fetch_trend_direction_sync, keyword
    )

    await _cache_set(cache_key, direction, ttl=_CACHE_TTL_SECONDS)
    return direction


async def compute_trend_score(keyword: str) -> dict:
    """
    Full trend computation: score + direction + breakout + related.
    Returns dict suitable for storing in product_scores.trend_score.
    """
    google_score = await get_trend_score(keyword)
    direction = await get_trend_direction(keyword)

    # TikTok signal: placeholder (Phase 6+ will add TikTok scraper)
    tiktok_signal = 0

    trend_score = (google_score * 0.7) + (tiktok_signal * 30)
    trend_breakout = google_score >= 70 and direction == "rising"

    return {
        "trend_score": round(trend_score, 2),
        "google_trend_value": google_score,
        "trend_direction": direction,
        "trend_breakout": trend_breakout,
        "tiktok_signal": tiktok_signal,
    }


# ------------------------------------------------------------------
# Sync pytrends helpers (run in executor to avoid blocking event loop)
# ------------------------------------------------------------------

def _fetch_trend_score_sync(keyword: str) -> int:
    """Blocking pytrends call. Run via run_in_executor."""
    try:
        pt = TrendReq(hl="id-ID", tz=420, timeout=(10, 25), retries=2, backoff_factor=0.5)
        pt.build_payload([keyword], geo=_GEO, timeframe=_TIMEFRAME)
        df = pt.interest_over_time()
        if df.empty or keyword not in df.columns:
            return 0
        latest = int(df[keyword].iloc[-1])
        logger.info(f"[Trends] '{keyword}' latest score: {latest}")
        return latest
    except Exception as exc:
        logger.warning(f"[Trends] pytrends error for '{keyword}': {exc}")
        return 0


def _fetch_related_queries_sync(keyword: str) -> list[str]:
    """Fetch rising related queries for keyword."""
    try:
        pt = TrendReq(hl="id-ID", tz=420, timeout=(10, 25), retries=2, backoff_factor=0.5)
        pt.build_payload([keyword], geo=_GEO, timeframe=_TIMEFRAME)
        related = pt.related_queries()
        rising_df = related.get(keyword, {}).get("rising")
        if rising_df is None or rising_df.empty:
            return []
        return rising_df["query"].tolist()[:10]
    except Exception as exc:
        logger.warning(f"[Trends] Related queries error for '{keyword}': {exc}")
        return []


def _fetch_trend_direction_sync(keyword: str) -> str:
    """Compare 30d vs 90d average interest to determine direction."""
    try:
        pt = TrendReq(hl="id-ID", tz=420, timeout=(10, 25), retries=2, backoff_factor=0.5)
        pt.build_payload([keyword], geo=_GEO, timeframe=_TIMEFRAME)
        df = pt.interest_over_time()
        if df.empty or keyword not in df.columns:
            return "stable"
        series = df[keyword]
        avg_90 = float(series.mean())
        avg_30 = float(series.tail(4).mean())  # ~4 weeks ≈ 30 days
        if avg_90 == 0:
            return "stable"
        ratio = avg_30 / avg_90
        if ratio >= 1.15:
            return "rising"
        if ratio <= 0.85:
            return "declining"
        return "stable"
    except Exception as exc:
        logger.warning(f"[Trends] Direction error for '{keyword}': {exc}")
        return "stable"


# ------------------------------------------------------------------
# Redis helpers
# ------------------------------------------------------------------

async def _cache_get(key: str) -> Optional[str]:
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        value = await r.get(key)
        await r.aclose()
        return value
    except Exception as exc:
        logger.debug(f"[Trends] Redis get failed: {exc}")
        return None


async def _cache_set(key: str, value: str, ttl: int = _CACHE_TTL_SECONDS):
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.setex(key, ttl, value)
        await r.aclose()
    except Exception as exc:
        logger.debug(f"[Trends] Redis set failed: {exc}")


# ------------------------------------------------------------------
# DB persistence
# ------------------------------------------------------------------

async def _save_trend_signal(keyword: str, score: int):
    """Persist a trend data point to trend_signals table."""
    try:
        conn = await asyncpg.connect(settings.asyncpg_url)
        await conn.execute("""
            INSERT INTO trend_signals (keyword, platform, trend_value, geo)
            VALUES ($1, 'google', $2, $3)
        """, keyword, score, _GEO)
        await conn.close()
    except Exception as exc:
        logger.debug(f"[Trends] DB persist failed for '{keyword}': {exc}")
