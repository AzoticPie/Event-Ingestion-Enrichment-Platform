"""Query use-cases for event listing."""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from event_platform.infrastructure.repositories.events_repo import EventRawRepository


class QueryValidationError(ValueError):
    """Raised when query filters or cursor inputs are invalid."""


def _to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _encode_cursor(payload: dict[str, str]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _decode_cursor(cursor: str) -> dict[str, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive parser
        raise QueryValidationError("Malformed cursor") from exc

    if not isinstance(data, dict):
        raise QueryValidationError("Malformed cursor")
    return {str(k): str(v) for k, v in data.items()}


def _build_filter_hash(
    sort: str,
    occurred_from: datetime | None,
    occurred_to: datetime | None,
    event_type: str | None,
    severity: str | None,
    source: str | None,
    user_id: str | None,
    session_id: str | None,
    ingest_status: str | None,
    geo_country: str | None,
    is_bot: bool | None,
) -> str:
    payload = {
        "sort": sort,
        "occurred_from": occurred_from.isoformat() if occurred_from else None,
        "occurred_to": occurred_to.isoformat() if occurred_to else None,
        "event_type": event_type,
        "severity": severity,
        "source": source,
        "user_id": user_id,
        "session_id": session_id,
        "ingest_status": ingest_status,
        "geo_country": geo_country,
        "is_bot": is_bot,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class QueryService:
    """Service for read-model event queries."""

    def list_events(
        self,
        session: Session,
        tenant_id: uuid.UUID,
        limit: int,
        sort: str,
        cursor: str | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        event_type: str | None,
        severity: str | None,
        source: str | None,
        user_id: str | None,
        session_id: str | None,
        ingest_status: str | None,
        geo_country: str | None,
        is_bot: bool | None,
    ) -> list[dict[str, object]]:
        occurred_from_utc = _to_utc(occurred_from)
        occurred_to_utc = _to_utc(occurred_to)

        if occurred_from_utc and occurred_to_utc and occurred_from_utc > occurred_to_utc:
            raise QueryValidationError("occurred_from must be <= occurred_to")
        if sort not in {"asc", "desc"}:
            raise QueryValidationError("sort must be 'asc' or 'desc'")

        filter_hash = _build_filter_hash(
            sort=sort,
            occurred_from=occurred_from_utc,
            occurred_to=occurred_to_utc,
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=user_id,
            session_id=session_id,
            ingest_status=ingest_status,
            geo_country=geo_country,
            is_bot=is_bot,
        )

        cursor_occurred_at: datetime | None = None
        cursor_event_id: uuid.UUID | None = None
        if cursor:
            data = _decode_cursor(cursor)
            if data.get("filter_hash") != filter_hash:
                raise QueryValidationError("Cursor does not match current filter set")
            if data.get("sort") != sort:
                raise QueryValidationError("Cursor sort does not match requested sort")
            try:
                cursor_occurred_at = datetime.fromisoformat(data["occurred_at"])
                cursor_occurred_at = _to_utc(cursor_occurred_at)
                cursor_event_id = uuid.UUID(data["event_id"])
            except Exception as exc:
                raise QueryValidationError("Malformed cursor values") from exc

        raw_repo = EventRawRepository(session)
        rows = raw_repo.list_filtered_page(
            tenant_id=tenant_id,
            limit=limit,
            sort=sort,
            cursor_occurred_at=cursor_occurred_at,
            cursor_event_id=cursor_event_id,
            occurred_from=occurred_from_utc,
            occurred_to=occurred_to_utc,
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=user_id,
            session_id=session_id,
            ingest_status=ingest_status,
            geo_country=geo_country,
            is_bot=is_bot,
        )

        has_more = len(rows) > limit
        page_rows = rows[:limit]

        result: list[dict[str, object]] = []
        for raw, normalized in page_rows:
            enriched = raw.enriched
            result.append(
                {
                    "event_id": raw.id,
                    "event_type": normalized.event_type_canonical,
                    "occurred_at": normalized.occurred_at_utc,
                    "source": normalized.source,
                    "user_id": normalized.user_id,
                    "session_id": normalized.session_id,
                    "severity": normalized.severity,
                    "url": normalized.url,
                    "referrer": normalized.referrer,
                    "received_at": raw.received_at,
                    "ingest_status": raw.ingest_status,
                    "geo_country": enriched.geo_country if enriched is not None else None,
                    "ua_browser": enriched.ua_browser if enriched is not None else None,
                    "ua_os": enriched.ua_os if enriched is not None else None,
                    "ua_device": enriched.ua_device if enriched is not None else None,
                    "url_host": enriched.url_host if enriched is not None else None,
                    "referrer_domain": enriched.referrer_domain if enriched is not None else None,
                    "is_bot": enriched.is_bot if enriched is not None else False,
                }
            )

        next_cursor: str | None = None
        if has_more and page_rows:
            last_raw, last_normalized = page_rows[-1]
            next_cursor = _encode_cursor(
                {
                    "occurred_at": last_normalized.occurred_at_utc.isoformat(),
                    "event_id": str(last_raw.id),
                    "sort": sort,
                    "filter_hash": filter_hash,
                }
            )

        return [
            {
                "count": len(result),
                "has_more": has_more,
                "next_cursor": next_cursor,
                "items": result,
            }
        ]

    def get_event_detail(self, session: Session, tenant_id: uuid.UUID, event_id: uuid.UUID) -> dict[str, Any] | None:
        raw_repo = EventRawRepository(session)
        loaded = raw_repo.get_event_detail(tenant_id=tenant_id, event_id=event_id)
        if loaded is None:
            return None

        raw, normalized = loaded
        enriched = raw.enriched
        return {
            "item": {
                "event_id": raw.id,
                "event_type": normalized.event_type_canonical,
                "occurred_at": normalized.occurred_at_utc,
                "source": normalized.source,
                "user_id": normalized.user_id,
                "session_id": normalized.session_id,
                "severity": normalized.severity,
                "url": normalized.url,
                "referrer": normalized.referrer,
                "received_at": raw.received_at,
                "ingest_status": raw.ingest_status,
                "geo_country": enriched.geo_country if enriched is not None else None,
                "ua_browser": enriched.ua_browser if enriched is not None else None,
                "ua_os": enriched.ua_os if enriched is not None else None,
                "ua_device": enriched.ua_device if enriched is not None else None,
                "url_host": enriched.url_host if enriched is not None else None,
                "referrer_domain": enriched.referrer_domain if enriched is not None else None,
                "is_bot": enriched.is_bot if enriched is not None else False,
            }
        }


