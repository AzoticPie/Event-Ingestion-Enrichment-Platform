"""Ingestion API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, status
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
from event_platform.infrastructure.db.session import get_session, transaction

router = APIRouter(prefix="/v1/ingest", tags=["ingestion"])

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

