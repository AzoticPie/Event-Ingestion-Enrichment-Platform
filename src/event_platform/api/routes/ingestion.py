"""Ingestion API routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, status
import structlog
from sqlalchemy.orm import Session

from event_platform.api.dependencies import AuthContext, get_authenticated_tenant
from event_platform.api.schemas.ingestion import (
    IngestBatchRequest,
    IngestBatchResponse,
    IngestedEventResult,
    IngestEventRequest,
    IngestSingleResponse,
)
from event_platform.application.ingestion_service import IngestionService
from event_platform.core.config import get_settings
from event_platform.infrastructure.repositories.events_repo import EventRepository
from event_platform.infrastructure.db.session import get_session, transaction
from event_platform.worker.tasks.enrichment import enrich_event

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])
settings = get_settings()
logger = structlog.get_logger(__name__)

SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-api-key",
    "x-ingest-key",
}


@router.post("/events", response_model=IngestSingleResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_event(
    payload: IngestEventRequest,
    request: Request,
    auth: AuthContext = Depends(get_authenticated_tenant),
    session: Session = Depends(get_session),
) -> IngestSingleResponse:
    """Ingest a single event for authenticated tenant."""
    service = IngestionService()
    headers_jsonb = _request_headers(request)

    with transaction(session):
        result = service.ingest_event(
            session=session,
            tenant_id=auth.tenant_id,
            payload=payload,
            headers_jsonb=headers_jsonb,
            ip=request.client.host if request.client is not None else None,
            user_agent=request.headers.get("user-agent"),
        )

    if result.queued_for_enrichment:
        try:
            _publish_enrichment_task(session=session, event_id=result.event_id)
        except Exception:
            logger.exception("enrichment_publish_failed_for_single_event", event_id=str(result.event_id))

    return IngestSingleResponse(
        result=IngestedEventResult(
            event_id=result.event_id,
            status=result.status,
            duplicate_reason=result.duplicate_reason,
        )
    )


@router.post("/events:batch", response_model=IngestBatchResponse, status_code=status.HTTP_202_ACCEPTED)
def ingest_events_batch(
    payload: IngestBatchRequest,
    request: Request,
    auth: AuthContext = Depends(get_authenticated_tenant),
    session: Session = Depends(get_session),
) -> IngestBatchResponse:
    """Ingest a batch of events transactionally for authenticated tenant."""
    service = IngestionService()
    headers_jsonb = _request_headers(request)
    results: list[IngestedEventResult] = []
    accepted_ids: list[str] = []

    with transaction(session):
        for event in payload.events:
            ingest_result = service.ingest_event(
                session=session,
                tenant_id=auth.tenant_id,
                payload=event,
                headers_jsonb=headers_jsonb,
                ip=request.client.host if request.client is not None else None,
                user_agent=request.headers.get("user-agent"),
            )
            results.append(
                IngestedEventResult(
                    event_id=ingest_result.event_id,
                    status=ingest_result.status,
                    duplicate_reason=ingest_result.duplicate_reason,
                )
            )
            if ingest_result.queued_for_enrichment:
                accepted_ids.append(str(ingest_result.event_id))

    for accepted_event_id in accepted_ids:
        try:
            _publish_enrichment_task(session=session, event_id=accepted_event_id)
        except Exception:
            logger.exception("enrichment_publish_failed_for_batch_event", event_id=accepted_event_id)

    accepted_count = sum(1 for item in results if item.status == "accepted")
    duplicate_count = len(results) - accepted_count

    return IngestBatchResponse(
        total_count=len(results),
        accepted_count=accepted_count,
        duplicate_count=duplicate_count,
        results=results,
    )


def _request_headers(request: Request) -> dict[str, Any]:
    return {
        key.lower(): value
        for key, value in request.headers.items()
        if key.lower() not in SENSITIVE_HEADER_NAMES
    }


def _publish_enrichment_task(session: Session, event_id: object) -> None:
    event_id_str = str(event_id)
    event_uuid = uuid.UUID(event_id_str)
    repo = EventRepository(session)
    try:
        async_result = enrich_event.apply_async(args=[event_id_str], queue=settings.celery_enrichment_queue)
        logger.info(
            "enrichment_task_published",
            event_id=event_id_str,
            task_id=async_result.id,
            queue=settings.celery_enrichment_queue,
        )
        with transaction(session):
            repo.set_ingest_status(event_uuid, "queued")
    except Exception:
        with transaction(session):
            repo.set_ingest_status(event_uuid, "failed_terminal")
        raise

