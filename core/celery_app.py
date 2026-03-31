from celery import Celery
from celery.schedules import crontab

from core.config import REDIS_URL

celery_app = Celery("dropship", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    worker_max_tasks_per_child=50,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "pull_affiliate_data": {
        "task": "affiliate.scheduler.pull_all_affiliate_data",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "score_niches": {
        "task": "affiliate.niche_scorer.score_all_niches",
        "schedule": crontab(minute=30, hour="*/6"),
    },
    "sync_inventory": {
        "task": "store.inventory_sync.sync_all_inventory",
        "schedule": crontab(minute=0, hour="*/2"),
    },
    "reprice_products": {
        "task": "store.repricing_bot.reprice_all",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}

celery_app.autodiscover_tasks([
    "affiliate",
    "store",
    "fulfillment",
    "ai",
])
