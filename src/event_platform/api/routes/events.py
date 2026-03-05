"""Event query API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from event_platform.api.dependencies import AuthContext, get_authenticated_tenant
from event_platform.api.schemas.events import EventListItem, EventListResponse
from event_platform.application.query_service import QueryService
from event_platform.infrastructure.db.session import get_session

router = APIRouter(prefix="/v1", tags=["events"])


@router.get("/events", response_model=EventListResponse)
def list_events(
    limit: int = Query(default=50, ge=1, le=200),
    event_type: str | None = Query(default=None),
    auth: AuthContext = Depends(get_authenticated_tenant),
    session: Session = Depends(get_session),
) -> EventListResponse:
    """List events scoped to authenticated tenant."""
    service = QueryService()
    rows = service.list_events(
        session=session,
        tenant_id=auth.tenant_id,
        limit=limit,
        event_type=event_type,
    )

    return EventListResponse(count=len(rows), items=[EventListItem.model_validate(item) for item in rows])

