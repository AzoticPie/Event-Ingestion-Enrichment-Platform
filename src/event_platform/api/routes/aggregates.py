"""Aggregate API routes for dashboard metrics."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog
from sqlalchemy.orm import Session

from event_platform.api.dependencies import AuthContext, get_authenticated_tenant
from event_platform.api.schemas.aggregates import (
    AggregateBucketsResponse,
    AggregateCountResponse,
    AggregateUniqueUsersResponse,
)
from event_platform.application.aggregate_service import AggregateService
from event_platform.application.query_service import QueryValidationError
from event_platform.infrastructure.db.session import get_session

router = APIRouter(prefix="/v1/aggregates", tags=["aggregates"])
logger = structlog.get_logger(__name__)


def _require_time_bound(occurred_from: datetime | None, occurred_to: datetime | None) -> None:
    if occurred_from is None and occurred_to is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": "At least one time bound is required"},
        )


@router.get("/count", response_model=AggregateCountResponse)
def aggregate_count(
    occurred_from: datetime | None = Query(default=None),
    occurred_to: datetime | None = Query(default=None),
    event_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    source: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    ingest_status: str | None = Query(default=None),
    geo_country: str | None = Query(default=None),
    is_bot: bool | None = Query(default=None),
    auth: AuthContext = Depends(get_authenticated_tenant),
    session: Session = Depends(get_session),
) -> AggregateCountResponse:
    _require_time_bound(occurred_from, occurred_to)
    service = AggregateService()
    try:
        payload = service.count_events(
            session=session,
            tenant_id=auth.tenant_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=user_id,
            session_id=session_id,
            ingest_status=ingest_status,
            geo_country=geo_country,
            is_bot=is_bot,
        )
    except QueryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc
    except Exception:
        logger.exception("aggregate_count_unexpected_failure", tenant_id=str(auth.tenant_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Unexpected aggregate error"},
        )
    return AggregateCountResponse.model_validate(payload)


@router.get("/top-event-types", response_model=AggregateBucketsResponse)
def aggregate_top_event_types(
    limit: int = Query(default=10, ge=1, le=100),
    occurred_from: datetime | None = Query(default=None),
    occurred_to: datetime | None = Query(default=None),
    source: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    geo_country: str | None = Query(default=None),
    is_bot: bool | None = Query(default=None),
    auth: AuthContext = Depends(get_authenticated_tenant),
    session: Session = Depends(get_session),
) -> AggregateBucketsResponse:
    _require_time_bound(occurred_from, occurred_to)
    service = AggregateService()
    try:
        payload = service.top_event_types(
            session=session,
            tenant_id=auth.tenant_id,
            limit=limit,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            source=source,
            severity=severity,
            geo_country=geo_country,
            is_bot=is_bot,
        )
    except QueryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc
    except Exception:
        logger.exception("aggregate_top_event_types_unexpected_failure", tenant_id=str(auth.tenant_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Unexpected aggregate error"},
        )
    return AggregateBucketsResponse.model_validate(payload)


@router.get("/top-urls", response_model=AggregateBucketsResponse)
def aggregate_top_urls(
    limit: int = Query(default=10, ge=1, le=100),
    occurred_from: datetime | None = Query(default=None),
    occurred_to: datetime | None = Query(default=None),
    event_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    geo_country: str | None = Query(default=None),
    is_bot: bool | None = Query(default=None),
    auth: AuthContext = Depends(get_authenticated_tenant),
    session: Session = Depends(get_session),
) -> AggregateBucketsResponse:
    _require_time_bound(occurred_from, occurred_to)
    service = AggregateService()
    try:
        payload = service.top_urls(
            session=session,
            tenant_id=auth.tenant_id,
            limit=limit,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            event_type=event_type,
            source=source,
            severity=severity,
            geo_country=geo_country,
            is_bot=is_bot,
        )
    except QueryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc
    except Exception:
        logger.exception("aggregate_top_urls_unexpected_failure", tenant_id=str(auth.tenant_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Unexpected aggregate error"},
        )
    return AggregateBucketsResponse.model_validate(payload)


@router.get("/unique-users", response_model=AggregateUniqueUsersResponse)
def aggregate_unique_users(
    occurred_from: datetime | None = Query(default=None),
    occurred_to: datetime | None = Query(default=None),
    event_type: str | None = Query(default=None),
    source: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    geo_country: str | None = Query(default=None),
    is_bot: bool | None = Query(default=None),
    auth: AuthContext = Depends(get_authenticated_tenant),
    session: Session = Depends(get_session),
) -> AggregateUniqueUsersResponse:
    _require_time_bound(occurred_from, occurred_to)
    service = AggregateService()
    try:
        payload = service.unique_users(
            session=session,
            tenant_id=auth.tenant_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            event_type=event_type,
            source=source,
            severity=severity,
            geo_country=geo_country,
            is_bot=is_bot,
        )
    except QueryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc
    except Exception:
        logger.exception("aggregate_unique_users_unexpected_failure", tenant_id=str(auth.tenant_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "internal_error", "message": "Unexpected aggregate error"},
        )
    return AggregateUniqueUsersResponse.model_validate(payload)

