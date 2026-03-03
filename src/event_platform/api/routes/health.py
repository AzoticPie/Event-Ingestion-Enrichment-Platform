"""Health and readiness endpoints."""

from __future__ import annotations

import socket
from typing import Any

import redis
from fastapi import APIRouter, HTTPException

from event_platform.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    """Liveness probe endpoint."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, Any]:
    """Readiness probe endpoint with dependency checks."""
    settings = get_settings()
    dependencies: dict[str, str] = {"postgres": "skipped", "redis": "skipped"}

    if not settings.enable_readiness_dependency_checks:
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
        return {"status": "ready", "dependencies": dependencies}

    raise HTTPException(status_code=503, detail={"status": "not_ready", "dependencies": dependencies})


def _check_tcp_host(host: str, port: int) -> None:
    """Verify a TCP service is reachable."""
    with socket.create_connection((host, port), timeout=1):
        return

