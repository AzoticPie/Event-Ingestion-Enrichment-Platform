"""Create tenant, ingestion key, raw event, and normalized event tables.

Revision ID: 20260303_0001
Revises:
Create Date: 2026-03-03
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260303_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_tenant_name"),
    )

    op.create_table(
        "ingestion_key",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_prefix", sa.String(length=24), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_prefix", name="uq_ingestion_key_prefix"),
    )
    op.create_index("ix_ingestion_key_tenant_id", "ingestion_key", ["tenant_id"], unique=False)
    op.create_index("ix_ingestion_key_is_active", "ingestion_key", ["is_active"], unique=False)

    op.create_table(
        "event_raw",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("event_type_original", sa.String(length=255), nullable=False),
        sa.Column("occurred_at_original", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "headers_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("dedupe_hash", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=True),
        sa.Column("ingest_status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_raw_tenant_received_at", "event_raw", ["tenant_id", "received_at"], unique=False)
    op.create_index("ix_event_raw_tenant_event_type", "event_raw", ["tenant_id", "event_type_original"], unique=False)
    op.create_index("ix_event_raw_tenant_dedupe_hash", "event_raw", ["tenant_id", "dedupe_hash"], unique=False)
    op.create_index(
        "ux_event_raw_tenant_idempotency_key_not_null",
        "event_raw",
        ["tenant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "event_normalized",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type_canonical", sa.String(length=255), nullable=False),
        sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("ingestion_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["event_raw.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_event_normalized_tenant_occurred_at",
        "event_normalized",
        ["tenant_id", "occurred_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_event_normalized_tenant_type_occurred_at",
        "event_normalized",
        ["tenant_id", "event_type_canonical", "occurred_at_utc"],
        unique=False,
    )
    op.create_index(
        "ix_event_normalized_tenant_user_occurred_at",
        "event_normalized",
        ["tenant_id", "user_id", "occurred_at_utc"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_normalized_tenant_user_occurred_at", table_name="event_normalized")
    op.drop_index("ix_event_normalized_tenant_type_occurred_at", table_name="event_normalized")
    op.drop_index("ix_event_normalized_tenant_occurred_at", table_name="event_normalized")
    op.drop_table("event_normalized")

    op.drop_index("ux_event_raw_tenant_idempotency_key_not_null", table_name="event_raw")
    op.drop_index("ix_event_raw_tenant_dedupe_hash", table_name="event_raw")
    op.drop_index("ix_event_raw_tenant_event_type", table_name="event_raw")
    op.drop_index("ix_event_raw_tenant_received_at", table_name="event_raw")
    op.drop_table("event_raw")

    op.drop_index("ix_ingestion_key_is_active", table_name="ingestion_key")
    op.drop_index("ix_ingestion_key_tenant_id", table_name="ingestion_key")
    op.drop_table("ingestion_key")

    op.drop_table("tenant")

