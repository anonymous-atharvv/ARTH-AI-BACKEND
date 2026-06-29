from celery import Celery
from celery.schedules import crontab
from config import settings

celery_app = Celery(
    "arthai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.message_tasks", "tasks.scheduled_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_soft_time_limit=60,     # 60 second soft limit per task
    task_time_limit=90,           # 90 second hard limit
    worker_prefetch_multiplier=1, # Process one task at a time per worker
)

celery_app.conf.beat_schedule = {
    "send-weekly-summary-monday-morning": {
        "task": "send_weekly_summary",
        "schedule": crontab(day_of_week=1, hour=9, minute=0), # Monday 9:00 AM
    },
    "run-daily-anomaly-checks-evening": {
        "task": "run_daily_anomaly_checks",
        "schedule": crontab(hour=20, minute=0), # Daily 8:00 PM
    },
    "nightly-cache-warming-2am": {
        "task": "nightly_cache_warming",
        "schedule": crontab(hour=2, minute=0), # Daily 2:00 AM
    },
}
