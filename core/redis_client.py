import redis.asyncio as aioredis
from typing import Optional

from core.config import REDIS_URL
from core.logger import logger

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        logger.info("redis_connected", url=REDIS_URL)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.close()
        logger.info("redis_closed")
        _redis = None
