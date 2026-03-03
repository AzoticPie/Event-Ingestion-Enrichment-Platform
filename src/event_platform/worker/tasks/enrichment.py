"""Enrichment task placeholders for milestone 1 foundation."""

from __future__ import annotations

import structlog

from event_platform.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(name="event_platform.enrich_event", bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def enrich_event(self, event_id: str) -> dict[str, str]:
    """Placeholder enrichment task that confirms worker wiring."""
    logger.info("enrichment_task_received", event_id=event_id, task_id=self.request.id)
    return {"event_id": event_id, "status": "queued_for_future_enrichment"}

