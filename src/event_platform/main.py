"""Application entrypoint for the Event Ingestion & Enrichment Platform."""

from fastapi import FastAPI

from event_platform.api.routes.health import router as health_router
from event_platform.core.config import get_settings
from event_platform.core.logging import configure_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(health_router)
    return app


app = create_app()

