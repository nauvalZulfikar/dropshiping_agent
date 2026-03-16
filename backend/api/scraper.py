from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import uuid

from database import get_db
from tasks.celery_app import celery_app

router = APIRouter(prefix="/scraper", tags=["scraper"])

SUPPORTED_SOURCES = ["tokopedia", "shopee", "aliexpress"]


class ScrapeRequest(BaseModel):
    source: str
    keyword: str
    max_pages: int = Field(default=3, ge=1, le=10)


@router.post("/trigger")
async def trigger_scrape(req: ScrapeRequest, db: AsyncSession = Depends(get_db)):
    """Enqueue a scrape job and return the Celery task ID."""
    if req.source not in SUPPORTED_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{req.source}'. Supported: {SUPPORTED_SOURCES}",
        )

    task_map = {
        "tokopedia": "tasks.scrape_tasks.scrape_tokopedia",
        "shopee":    "tasks.scrape_tasks.scrape_shopee",
        "aliexpress": "tasks.scrape_tasks.scrape_aliexpress",
    }

    task = celery_app.send_task(
        task_map[req.source],
        args=[req.keyword, req.max_pages],
    )

    # Log job to DB
    await db.execute(text("""
        INSERT INTO scraper_jobs (id, source, job_type, status, started_at)
        VALUES (:id, :source, :job_type, 'pending', NOW())
        ON CONFLICT DO NOTHING
    """), {
        "id": str(uuid.uuid4()),
        "source": req.source,
        "job_type": f"search:{req.keyword}",
    })
    await db.commit()

    return {"task_id": task.id, "source": req.source, "keyword": req.keyword, "status": "queued"}


@router.get("/status/{task_id}")
async def scrape_status(task_id: str):
    """Return the current status of a Celery task."""
    result = celery_app.AsyncResult(task_id)
    response = {
        "task_id": task_id,
        "status": result.status,
        "result": None,
        "error": None,
    }
    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.result)
    return response


@router.delete("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Revoke (cancel) a pending or active Celery task."""
    celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
    return {"task_id": task_id, "status": "revoked"}


@router.get("/jobs")
async def list_jobs(
    source: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Return recent scraper job logs from DB."""
    where = ["1=1"]
    params: dict = {"limit": min(limit, 200)}
    if source:
        where.append("source = :source")
        params["source"] = source
    if status:
        where.append("status = :status")
        params["status"] = status

    query = text(f"""
        SELECT id, source, job_type, status, items_scraped, items_failed,
               error_message, started_at, finished_at, created_at
        FROM scraper_jobs
        WHERE {' AND '.join(where)}
        ORDER BY created_at DESC
        LIMIT :limit
    """)
    result = await db.execute(query, params)
    rows = result.mappings().all()
    return {
        "jobs": [
            {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(r).items()}
            for r in rows
        ]
    }


@router.get("/stats")
async def scraper_stats(db: AsyncSession = Depends(get_db)):
    """Aggregate stats on scraper health."""
    query = text("""
        SELECT
            source,
            COUNT(*) AS total_jobs,
            COUNT(*) FILTER (WHERE status = 'success')  AS succeeded,
            COUNT(*) FILTER (WHERE status = 'failed')   AS failed,
            COUNT(*) FILTER (WHERE status = 'pending')  AS pending,
            SUM(items_scraped)                           AS total_scraped,
            MAX(finished_at)                             AS last_run
        FROM scraper_jobs
        WHERE created_at >= NOW() - INTERVAL '24 hours'
        GROUP BY source
        ORDER BY source
    """)
    result = await db.execute(query)
    rows = result.mappings().all()
    return {
        "items": [
            {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dict(r).items()}
            for r in rows
        ]
    }
