"""Celery enrichment task orchestration."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from celery.exceptions import MaxRetriesExceededError

from event_platform.application.enrichment_service import (
    EnrichmentRetryableError,
    EnrichmentService,
    EnrichmentTerminalError,
    next_retry_at,
    utc_now,
)
from event_platform.core.config import get_settings
from event_platform.infrastructure.db.session import session_scope
from event_platform.infrastructure.repositories.events_repo import EventRepository

from event_platform.worker.celery_app import celery_app

logger = structlog.get_logger(__name__)
settings = get_settings()


@celery_app.task(
    name="event_platform.enrich_event",
    bind=True,
    max_retries=settings.enrichment_max_retries,
    retry_backoff=settings.enrichment_backoff_base_seconds,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
)
def enrich_event(self, event_id: str) -> dict[str, str]:
    """Run enrichment for one event with retries and failure persistence."""
    event_uuid = uuid.UUID(event_id)
    service = EnrichmentService()
    attempt = int(self.request.retries) + 1
    logger.info("enrichment_task_received", event_id=event_id, task_id=self.request.id, attempt=attempt)

    try:
        with session_scope() as session:
            result = service.enrich_event(session=session, event_id=event_uuid)
        logger.info("enrichment_completed", event_id=event_id, task_id=self.request.id, status=result.status)
        return {"event_id": event_id, "status": result.status}

    except EnrichmentRetryableError as exc:
        now_utc = utc_now()
        retry_eta = next_retry_at(
            now_utc=now_utc,
            base_seconds=settings.enrichment_backoff_base_seconds,
            attempt=attempt,
        )
        _record_failure(
            event_uuid=event_uuid,
            stage="enrichment",
            error_code="retry_scheduled",
            error_message=str(exc),
            attempts=attempt,
            status="retrying",
            next_retry_at_utc=retry_eta,
            task_id=self.request.id,
            lifecycle_state="queued",
        )
        logger.warning(
            "enrichment_retry_scheduled",
            event_id=event_id,
            task_id=self.request.id,
            attempt=attempt,
            next_retry_at=retry_eta.isoformat(),
            error=str(exc),
        )
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            _record_failure(
                event_uuid=event_uuid,
                stage="enrichment",
                error_code="retry_exhausted",
                error_message=str(exc),
                attempts=attempt,
                status="terminal",
                next_retry_at_utc=None,
                task_id=self.request.id,
                lifecycle_state="failed_terminal",
            )
            logger.error(
                "enrichment_terminal_failure",
                event_id=event_id,
                task_id=self.request.id,
                attempt=attempt,
                error=str(exc),
            )
            return {"event_id": event_id, "status": "failed_terminal"}
        raise

    except EnrichmentTerminalError as exc:
        _record_failure(
            event_uuid=event_uuid,
            stage="enrichment",
            error_code="terminal_error",
            error_message=str(exc),
            attempts=attempt,
            status="terminal",
            next_retry_at_utc=None,
            task_id=self.request.id,
            lifecycle_state="failed_terminal",
        )
        logger.error(
            "enrichment_terminal_failure",
            event_id=event_id,
            task_id=self.request.id,
            attempt=attempt,
            error=str(exc),
        )
        return {"event_id": event_id, "status": "failed_terminal"}

    except Exception as exc:
        _record_failure(
            event_uuid=event_uuid,
            stage="enrichment",
            error_code="unexpected_error",
            error_message=str(exc),
            attempts=attempt,
            status="terminal",
            next_retry_at_utc=None,
            task_id=self.request.id,
            lifecycle_state="failed_terminal",
        )
        logger.exception(
            "enrichment_unexpected_failure",
            event_id=event_id,
            task_id=self.request.id,
            attempt=attempt,
        )
        return {"event_id": event_id, "status": "failed_terminal"}


def _record_failure(
    event_uuid: uuid.UUID,
    stage: str,
    error_code: str,
    error_message: str,
    attempts: int,
    status: str,
    next_retry_at_utc: datetime | None,
    task_id: str | None,
    lifecycle_state: str,
) -> None:
    with session_scope() as session:
        repo = EventRepository(session)
        loaded = repo.get_raw_with_normalized(event_uuid)
        if loaded is None:
            return
        raw, _normalized = loaded
        repo.upsert_failed_enrichment(
            event_id=raw.id,
            tenant_id=raw.tenant_id,
            stage=stage,
            error_code=error_code,
            error_message=error_message,
            attempts=attempts,
            failed_at=utc_now().astimezone(UTC),
            next_retry_at=next_retry_at_utc,
            status=status,
            last_task_id=task_id,
        )
        repo.set_ingest_status(raw.id, lifecycle_state)

