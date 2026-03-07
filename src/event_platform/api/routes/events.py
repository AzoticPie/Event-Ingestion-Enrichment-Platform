"""Event query API routes."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from event_platform.api.dependencies import AuthContext, get_authenticated_tenant
from event_platform.api.schemas.events import EventDetailResponse, EventListItem, EventListResponse
from event_platform.application.query_service import QueryService, QueryValidationError
from event_platform.infrastructure.db.session import get_session

router = APIRouter(prefix="/v1", tags=["events"])


@router.get("/events", response_model=EventListResponse)
def list_events(
    limit: int = Query(default=50, ge=1, le=200),
    sort: str = Query(default="desc"),
    cursor: str | None = Query(default=None),
    occurred_from: datetime | None = Query(default=None),
    occurred_to: datetime | None = Query(default=None),
    event_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    source: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    ingest_status: str | None = Query(default=None),
    geo_country: str | None = Query(default=None),
    is_bot: bool | None = Query(default=None),
    auth: AuthContext = Depends(get_authenticated_tenant),
    session: Session = Depends(get_session),
) -> EventListResponse:
    """List events scoped to authenticated tenant."""
    service = QueryService()
    try:
        rows = service.list_events(
            session=session,
            tenant_id=auth.tenant_id,
            limit=limit,
            sort=sort,
            cursor=cursor,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=user_id,
            session_id=session_id,
            ingest_status=ingest_status,
            geo_country=geo_country,
            is_bot=is_bot,
        )
    except QueryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc

    page = rows[0]
    return EventListResponse(
        count=int(page["count"]),
        has_more=bool(page["has_more"]),
        next_cursor=page["next_cursor"],
        items=[EventListItem.model_validate(item) for item in page["items"]],
    )


@router.get("/events/{event_id}", response_model=EventDetailResponse)
def get_event_detail(
    event_id: str,
    auth: AuthContext = Depends(get_authenticated_tenant),
    session: Session = Depends(get_session),
) -> EventDetailResponse:
    """Fetch one event detail view scoped to authenticated tenant."""
    try:
        event_uuid = uuid.UUID(event_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": "Invalid event_id"},
        ) from exc

    service = QueryService()
    payload = service.get_event_detail(session=session, tenant_id=auth.tenant_id, event_id=event_uuid)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Event not found"},
        )
    return EventDetailResponse.model_validate(payload)


