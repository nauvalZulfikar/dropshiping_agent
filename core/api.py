from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.db import get_pool, close_pool
from core.redis_client import close_redis
from core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    logger.info("app_started")
    yield
    await close_pool()
    await close_redis()
    logger.info("app_stopped")


app = FastAPI(
    title="Dropship Automation API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}
