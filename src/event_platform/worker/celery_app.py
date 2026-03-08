"""Celery application wiring for enrichment workers."""

from datetime import timedelta

from celery import Celery

from event_platform.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "event_platform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["event_platform.worker.tasks.enrichment", "event_platform.worker.tasks.rollups"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "event_platform.enrich_event": {"queue": settings.celery_enrichment_queue},
        "event_platform.refresh_recent_rollups": {"queue": settings.celery_rollup_queue},
        "event_platform.refresh_recent_rollups_for_tenant": {"queue": settings.celery_rollup_queue},
        "event_platform.backfill_rollups": {"queue": settings.celery_rollup_queue},
    },
    beat_schedule=(
        {
            "refresh-recent-rollups": {
                "task": "event_platform.refresh_recent_rollups",
                "schedule": timedelta(seconds=max(1, settings.aggregate_rollup_refresh_interval_seconds)),
            }
        }
        if settings.aggregate_rollup_enabled
        else {}
    ),
)

