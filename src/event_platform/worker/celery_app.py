"""Celery application wiring for enrichment workers."""

from celery import Celery

from event_platform.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "event_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["event_platform.worker.tasks.enrichment"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

