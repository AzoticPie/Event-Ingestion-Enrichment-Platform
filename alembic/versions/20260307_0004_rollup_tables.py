"""Add rollup tables for milestone 6 aggregate materialization.

Revision ID: 20260307_0004
Revises: 20260306_0003
Create Date: 2026-03-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260307_0004"
down_revision = "20260306_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aggregate_rollup",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket_granularity", sa.String(length=16), nullable=False),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("dimension_key", sa.String(length=255), nullable=False),
        sa.Column("metric_value", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "(metric_name = 'events.count' AND dimension_key = '__all__') "
            "OR (metric_name <> 'events.count' AND dimension_key <> '__all__')",
            name="ck_aggregate_rollup_dimension_policy",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "bucket_start",
            "bucket_granularity",
            "metric_name",
            "dimension_key",
            name="uq_aggregate_rollup_bucket_metric_dimension",
        ),
    )
    op.create_index(
        "ix_aggregate_rollup_tenant_metric_bucket_start",
        "aggregate_rollup",
        ["tenant_id", "metric_name", "bucket_start"],
        unique=False,
    )
    op.create_index(
        "ix_aggregate_rollup_tenant_metric_bucket_dimension",
        "aggregate_rollup",
        ["tenant_id", "metric_name", "bucket_start", "dimension_key"],
        unique=False,
    )

    op.create_table(
        "aggregate_rollup_coverage_segment",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bucket_granularity", sa.String(length=16), nullable=False),
        sa.Column("metric_group", sa.String(length=64), nullable=False),
        sa.Column("segment_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("segment_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("segment_start < segment_end", name="ck_rollup_coverage_segment_bounds"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "bucket_granularity",
            "metric_group",
            "segment_start",
            "segment_end",
            name="uq_rollup_coverage_segment",
        ),
    )
    op.create_index(
        "ix_rollup_coverage_tenant_granularity_group_bounds",
        "aggregate_rollup_coverage_segment",
        ["tenant_id", "bucket_granularity", "metric_group", "segment_start", "segment_end"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rollup_coverage_tenant_granularity_group_bounds",
        table_name="aggregate_rollup_coverage_segment",
    )
    op.drop_table("aggregate_rollup_coverage_segment")

    op.drop_index("ix_aggregate_rollup_tenant_metric_bucket_dimension", table_name="aggregate_rollup")
    op.drop_index("ix_aggregate_rollup_tenant_metric_bucket_start", table_name="aggregate_rollup")
    op.drop_table("aggregate_rollup")

