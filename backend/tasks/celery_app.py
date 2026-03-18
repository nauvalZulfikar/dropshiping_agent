from celery import Celery
from celery.schedules import crontab
from config import settings

celery_app = Celery(
    "dropship",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "tasks.scrape_tasks",
        "tasks.score_tasks",
        "tasks.alert_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "full-scan-hourly": {
        "task": "tasks.scrape_tasks.full_scan",
        "schedule": crontab(minute=0),
        "args": [[
            "serum wajah", "sunscreen", "lip tint", "skincare bundling",
            "kaos oversized", "hijab", "gamis", "tas wanita",
            "casing hp", "earphone wireless", "powerbank", "tripod hp",
            "kopi lokal", "snack viral", "bumbu masak", "keripik",
            "organizer rumah", "alat dapur", "dekorasi rumah",
            "vitamin c", "multivitamin", "suplemen kesehatan",
            "popok bayi", "mpasi", "susu formula",
            "kursus online", "template desain"
        ]],
    },
    "score-all-2h": {
        "task": "tasks.score_tasks.score_all_products",
        "schedule": crontab(minute=0, hour="*/2"),
    },
    "monitor-prices-30m": {
        "task": "tasks.scrape_tasks.monitor_price_changes",
        "schedule": crontab(minute="*/30"),
    },
    "daily-digest-8am": {
        "task": "tasks.alert_tasks.send_daily_digest",
        "schedule": crontab(hour=8, minute=0),  # WIB (UTC+7 → set UTC offset in config)
    },
    "watchlist-alerts-hourly": {
        "task": "tasks.alert_tasks.send_watchlist_alerts",
        "schedule": crontab(minute=15),
    },
    "embed-images-6h": {
        "task": "tasks.score_tasks.embed_product_images",
        "schedule": crontab(minute=30, hour="*/6"),
    },
    "match-suppliers-6h": {
        "task": "tasks.score_tasks.match_suppliers",
        "schedule": crontab(minute=45, hour="*/6"),
    },
}
