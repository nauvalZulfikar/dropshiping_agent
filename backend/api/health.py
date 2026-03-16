import logging
from fastapi import APIRouter
import redis.asyncio as aioredis

from database import test_db_connection
from config import settings

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Returns service health status including DB and Redis connectivity."""
    db_status = "connected" if await test_db_connection() else "disconnected"

    redis_status = "disconnected"
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        redis_status = "connected"
    except Exception as exc:
        logger.warning(f"Redis health check failed: {exc}")

    overall = "ok" if db_status == "connected" and redis_status == "connected" else "degraded"

    return {
        "status": overall,
        "db": db_status,
        "redis": redis_status,
    }
