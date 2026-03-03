"""SQLAlchemy models for milestone 2 core tables."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text, text
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

