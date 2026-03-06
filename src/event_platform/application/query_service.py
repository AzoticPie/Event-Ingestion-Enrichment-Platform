"""Query use-cases for event listing."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from event_platform.infrastructure.repositories.events_repo import EventRawRepository


class QueryService:
    """Service for read-model event queries."""

    def list_events(
        self,
        session: Session,
        tenant_id: uuid.UUID,
        limit: int,
        event_type: str | None,
    ) -> list[dict[str, object]]:
        raw_repo = EventRawRepository(session)
        rows = raw_repo.list_with_normalized(tenant_id=tenant_id, limit=limit, event_type=event_type)

        result: list[dict[str, object]] = []
        for raw, normalized in rows:
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
        return result

