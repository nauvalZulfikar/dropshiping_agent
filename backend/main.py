import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
import redis.asyncio as aioredis

from config import settings
from database import test_db_connection
from api.health import router as health_router
from api.products import router as products_router
from api.scraper import router as scraper_router
from api.analytics import router as analytics_router
from api.watchlist import router as watchlist_router
from api.suppliers import router as suppliers_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Dropship Research API...")
    await test_db_connection()

    # Initialize Redis cache
    redis_client = aioredis.from_url(settings.redis_url, encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis_client), prefix="dropship-cache:")
    logger.info("FastAPI cache initialized with Redis backend")

    yield

    logger.info("Shutting down Dropship Research API...")


app = FastAPI(
    title="Dropship Research API",
    description="Indonesian marketplace intelligence — product research & scoring platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "message": "Internal server error",
            "code": 500,
        },
    )


app.include_router(health_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(scraper_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(watchlist_router, prefix="/api")
app.include_router(suppliers_router, prefix="/api")
