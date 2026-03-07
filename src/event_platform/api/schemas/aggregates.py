"""Schemas for aggregate query endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class AggregateCountResponse(BaseModel):
    """Event count aggregate response."""

    value: int
    data_source: str


class AggregateBucketItem(BaseModel):
    """Label/value aggregate bucket item."""

    key: str
    value: int


class AggregateBucketsResponse(BaseModel):
    """Top-N aggregate response."""

    items: list[AggregateBucketItem]
    data_source: str


class AggregateUniqueUsersResponse(BaseModel):
    """Unique users aggregate response."""

    value: int
    data_source: str

