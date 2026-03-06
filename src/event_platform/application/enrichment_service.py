"""Asynchronous enrichment orchestration service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from event_platform.core.config import get_settings
from event_platform.infrastructure.enrichment.geoip import GeoIpUnavailableError, parse_geo_country
from event_platform.infrastructure.enrichment.url_parser import parse_url_fields
from event_platform.infrastructure.enrichment.user_agent import parse_user_agent
from event_platform.infrastructure.repositories.events_repo import EventRepository


class EnrichmentRetryableError(RuntimeError):
    """Retryable enrichment error caused by transient infrastructure."""


class EnrichmentTerminalError(RuntimeError):
    """Terminal enrichment error that should not be retried."""


@dataclass(slots=True)
class EnrichmentResult:
    """Outcome for one enrichment execution."""

    event_id: uuid.UUID
    status: str


class EnrichmentService:
    """Service that enriches accepted events and persists projections."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def enrich_event(self, session: Session, event_id: uuid.UUID) -> EnrichmentResult:
        """Perform idempotent enrichment for one event."""
        repo = EventRepository(session)
        loaded = repo.get_raw_with_normalized(event_id)
        if loaded is None:
            raise EnrichmentTerminalError(f"event_not_found:{event_id}")

        raw, normalized = loaded
        existing_enriched = repo.get_enriched(event_id)
        if existing_enriched is not None and existing_enriched.schema_tag == "m4_baseline":
            repo.set_ingest_status(event_id, "enriched")
            repo.clear_failed_enrichment(event_id)
            return EnrichmentResult(event_id=event_id, status="already_enriched")

        repo.set_ingest_status(event_id, "enriching")

        ua_data = parse_user_agent(raw.user_agent)
        url_data = parse_url_fields(normalized.url, normalized.referrer)

        try:
            geo_data = parse_geo_country(raw.ip, self._settings.geoip_db_path)
        except GeoIpUnavailableError as exc:
            raise EnrichmentRetryableError(str(exc)) from exc

        repo.upsert_enriched(
            event_id=raw.id,
            tenant_id=raw.tenant_id,
            geo_country=geo_data.country,
            ua_browser=ua_data.browser,
            ua_os=ua_data.os,
            ua_device=ua_data.device,
            url_host=url_data.url_host,
            url_path=url_data.url_path,
            referrer_domain=url_data.referrer_domain,
            is_bot=ua_data.is_bot,
            schema_tag="m4_baseline",
        )
        repo.clear_failed_enrichment(event_id)
        repo.set_ingest_status(event_id, "enriched")
        return EnrichmentResult(event_id=event_id, status="enriched")


def next_retry_at(now_utc: datetime, base_seconds: int, attempt: int, max_seconds: int = 300) -> datetime:
    """Compute exponential backoff retry schedule."""
    delay = min(base_seconds * (2 ** max(0, attempt - 1)), max_seconds)
    return now_utc + timedelta(seconds=delay)


def utc_now() -> datetime:
    """Current UTC timestamp helper."""
    return datetime.now(UTC)

