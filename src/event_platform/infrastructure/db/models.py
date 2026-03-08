"""SQLAlchemy models for core ingestion and enrichment tables."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from event_platform.infrastructure.db.base import Base, TimestampMixin


class Tenant(TimestampMixin, Base):
    """Tenant/workspace owning events and ingestion credentials."""

    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    ingestion_keys: Mapped[list[IngestionKey]] = relationship(back_populates="tenant")


class IngestionKey(TimestampMixin, Base):
    """Hashed ingestion credentials scoped to a tenant."""

    __tablename__ = "ingestion_key"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    key_prefix: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped[Tenant] = relationship(back_populates="ingestion_keys")


class EventRaw(Base):
    """Immutable raw event payload record."""

    __tablename__ = "event_raw"
    __table_args__ = (
        Index("ix_event_raw_tenant_received_at", "tenant_id", "received_at"),
        Index("ix_event_raw_tenant_event_type", "tenant_id", "event_type_original"),
        Index("ix_event_raw_tenant_dedupe_hash", "tenant_id", "dedupe_hash"),
        Index("ix_event_raw_tenant_ingest_status_received_at", "tenant_id", "ingest_status", "received_at"),
        Index(
            "ux_event_raw_tenant_idempotency_key_not_null",
            "tenant_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type_original: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at_original: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    payload_jsonb: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    headers_jsonb: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dedupe_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ingest_status: Mapped[str] = mapped_column(String(32), nullable=False, default="accepted")

    normalized: Mapped[EventNormalized | None] = relationship(back_populates="event_raw", uselist=False)
    enriched: Mapped[EventEnriched | None] = relationship(back_populates="event_raw", uselist=False)
    failed_enrichment: Mapped[FailedEnrichment | None] = relationship(back_populates="event_raw", uselist=False)


class EventNormalized(Base):
    """Normalized searchable event fields."""

    __tablename__ = "event_normalized"
    __table_args__ = (
        Index("ix_event_normalized_tenant_occurred_at", "tenant_id", "occurred_at_utc"),
        Index(
            "ix_event_normalized_tenant_type_occurred_at",
            "tenant_id",
            "event_type_canonical",
            "occurred_at_utc",
        ),
        Index(
            "ix_event_normalized_tenant_source_occurred_at",
            "tenant_id",
            "source",
            "occurred_at_utc",
        ),
        Index(
            "ix_event_normalized_tenant_severity_occurred_at",
            "tenant_id",
            "severity",
            "occurred_at_utc",
        ),
        Index(
            "ix_event_normalized_tenant_session_occurred_at",
            "tenant_id",
            "session_id",
            "occurred_at_utc",
        ),
        Index(
            "ix_event_normalized_tenant_user_occurred_at",
            "tenant_id",
            "user_id",
            "occurred_at_utc",
        ),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_raw.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type_canonical: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    referrer: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    ingestion_date: Mapped[date] = mapped_column(Date, nullable=False)

    event_raw: Mapped[EventRaw] = relationship(back_populates="normalized")


class EventEnriched(Base):
    """Asynchronous enrichment projection keyed by event id."""

    __tablename__ = "event_enriched"
    __table_args__ = (
        Index("ix_event_enriched_tenant_enriched_at", "tenant_id", "enriched_at"),
        Index("ix_event_enriched_tenant_geo_country", "tenant_id", "geo_country"),
        Index("ix_event_enriched_tenant_geo_country_event_id", "tenant_id", "geo_country", "event_id"),
        Index("ix_event_enriched_tenant_is_bot", "tenant_id", "is_bot"),
        Index("ix_event_enriched_tenant_is_bot_event_id", "tenant_id", "is_bot", "event_id"),
        Index("ix_event_enriched_tenant_url_host", "tenant_id", "url_host"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_raw.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    geo_country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ua_browser: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ua_os: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ua_device: Mapped[str | None] = mapped_column(String(128), nullable=True)
    url_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    referrer_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    schema_tag: Mapped[str] = mapped_column(String(64), nullable=False, default="m4_baseline")
    enriched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    event_raw: Mapped[EventRaw] = relationship(back_populates="enriched")


class FailedEnrichment(Base):
    """Durable failed enrichment records for retries and terminal states."""

    __tablename__ = "failed_enrichment"
    __table_args__ = (
        Index("ix_failed_enrichment_tenant_status_failed_at", "tenant_id", "status", "failed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("event_raw.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    event_raw: Mapped[EventRaw] = relationship(back_populates="failed_enrichment")


class AggregateRollup(Base):
    """Materialized minute-bucket aggregates for dashboard read paths."""

    __tablename__ = "aggregate_rollup"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "bucket_start",
            "bucket_granularity",
            "metric_name",
            "dimension_key",
            name="uq_aggregate_rollup_bucket_metric_dimension",
        ),
        CheckConstraint(
            "(metric_name = 'events.count' AND dimension_key = '__all__') "
            "OR (metric_name <> 'events.count' AND dimension_key <> '__all__')",
            name="ck_aggregate_rollup_dimension_policy",
        ),
        Index(
            "ix_aggregate_rollup_tenant_metric_bucket_start",
            "tenant_id",
            "metric_name",
            "bucket_start",
        ),
        Index(
            "ix_aggregate_rollup_tenant_metric_bucket_dimension",
            "tenant_id",
            "metric_name",
            "bucket_start",
            "dimension_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bucket_granularity: Mapped[str] = mapped_column(String(16), nullable=False, default="minute")
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    dimension_key: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class AggregateRollupCoverageSegment(Base):
    """Coverage segments proving which windows are fully materialized."""

    __tablename__ = "aggregate_rollup_coverage_segment"
    __table_args__ = (
        CheckConstraint("segment_start < segment_end", name="ck_rollup_coverage_segment_bounds"),
        UniqueConstraint(
            "tenant_id",
            "bucket_granularity",
            "metric_group",
            "segment_start",
            "segment_end",
            name="uq_rollup_coverage_segment",
        ),
        Index(
            "ix_rollup_coverage_tenant_granularity_group_bounds",
            "tenant_id",
            "bucket_granularity",
            "metric_group",
            "segment_start",
            "segment_end",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    bucket_granularity: Mapped[str] = mapped_column(String(16), nullable=False, default="minute")
    metric_group: Mapped[str] = mapped_column(String(64), nullable=False, default="core_dashboard")
    segment_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    segment_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

