"""Request and response schemas for ingestion endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class IngestEventRequest(BaseModel):
    """Payload for a single event ingestion request."""

    event_type: str = Field(min_length=1, max_length=255)
    occurred_at: datetime
    source: str = Field(default="api", min_length=1, max_length=128)
    user_id: str | None = Field(default=None, max_length=255)
    session_id: str | None = Field(default=None, max_length=255)
    severity: str | None = Field(default=None, max_length=32)
    url: str | None = None
    referrer: str | None = None
    schema_version: str | None = Field(default=None, max_length=32)
    idempotency_key: str | None = Field(default=None, max_length=255)
    attributes: dict[str, Any] = Field(default_factory=dict)


class IngestBatchRequest(BaseModel):
    """Payload for a batch ingestion request."""

    batch_id: str | None = Field(default=None, max_length=128)
    events: list[IngestEventRequest] = Field(min_length=1, max_length=1000)


class IngestedEventResult(BaseModel):
    """Outcome for an ingested event."""

    event_id: uuid.UUID
    status: Literal["accepted", "duplicate"]
    duplicate_reason: Literal["idempotency_key", "dedupe_hash"] | None = None


class IngestSingleResponse(BaseModel):
    """Response envelope for single event ingestion."""

    result: IngestedEventResult


class IngestBatchResponse(BaseModel):
    """Response envelope for batch ingestion."""

    total_count: int
    accepted_count: int
    duplicate_count: int
    results: list[IngestedEventResult]

