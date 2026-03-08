"""Health and readiness endpoints."""

from __future__ import annotations

import logging
import socket
from typing import Any

import redis
from fastapi import APIRouter, HTTPException, Request

from event_platform.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/live")
def live(request: Request) -> dict[str, str]:
    """Liveness probe endpoint."""
    logger.info(
        "health_live_probe",
        extra={
            "origin": request.headers.get("origin"),
            "host": request.headers.get("host"),
            "client": request.client.host if request.client else None,
        },
    )
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> dict[str, Any]:
    """Readiness probe endpoint with dependency checks."""
    settings = get_settings()
    dependencies: dict[str, str] = {"postgres": "skipped", "redis": "skipped"}

    logger.info(
        "health_ready_probe_started",
        extra={
            "origin": request.headers.get("origin"),
            "host": request.headers.get("host"),
            "client": request.client.host if request.client else None,
            "dependency_checks_enabled": settings.enable_readiness_dependency_checks,
        },
    )

    if not settings.enable_readiness_dependency_checks:
        logger.info("health_ready_probe_completed", extra={"status": "ready", "dependencies": dependencies})
        return {"status": "ready", "dependencies": dependencies}

    try:
        _check_tcp_host(settings.postgres_host, settings.postgres_port)
        dependencies["postgres"] = "ok"
    except OSError as exc:
        dependencies["postgres"] = f"error: {exc}"

    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        if client.ping():
            dependencies["redis"] = "ok"
    except redis.RedisError as exc:
        dependencies["redis"] = f"error: {exc}"

    if all(state == "ok" for state in dependencies.values()):
        logger.info("health_ready_probe_completed", extra={"status": "ready", "dependencies": dependencies})
        return {"status": "ready", "dependencies": dependencies}

    logger.warning("health_ready_probe_failed", extra={"status": "not_ready", "dependencies": dependencies})
    raise HTTPException(status_code=503, detail={"status": "not_ready", "dependencies": dependencies})


def _check_tcp_host(host: str, port: int) -> None:
    """Verify a TCP service is reachable."""
    with socket.create_connection((host, port), timeout=1):
        return

