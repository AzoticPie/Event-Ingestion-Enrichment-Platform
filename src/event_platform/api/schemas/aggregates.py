"""Schemas for aggregate query endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AggregateCountResponse(BaseModel):
    """Event count aggregate response."""

    value: int
    data_source: Literal["rollup", "direct_query"]


class AggregateBucketItem(BaseModel):
    """Label/value aggregate bucket item."""

    key: str
    value: int


class AggregateBucketsResponse(BaseModel):
    """Top-N aggregate response."""

    items: list[AggregateBucketItem]
    data_source: Literal["rollup", "direct_query"]


class AggregateUniqueUsersResponse(BaseModel):
    """Unique users aggregate response."""

    value: int
    data_source: Literal["direct_query"]

