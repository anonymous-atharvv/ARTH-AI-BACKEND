from celery import Celery
from config import settings

celery_app = Celery(
    "arthai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.message_tasks"]
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
