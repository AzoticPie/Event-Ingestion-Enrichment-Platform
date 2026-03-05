"""Schemas for event query endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class EventListItem(BaseModel):
    """Serialized list item for queried event data."""

    event_id: uuid.UUID
    event_type: str
    occurred_at: datetime
    source: str
    user_id: str | None
    session_id: str | None
    severity: str | None
    url: str | None
    referrer: str | None
    received_at: datetime
    ingest_status: str


class EventListResponse(BaseModel):
    """Response envelope for event list endpoint."""

    count: int
    items: list[EventListItem]

