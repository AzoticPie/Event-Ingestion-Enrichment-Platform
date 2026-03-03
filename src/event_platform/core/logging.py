"""Structured logging configuration."""

import logging
import sys

import structlog


def configure_logging(level: str) -> None:
    """Configure stdlib and structlog logging."""
    resolved_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=resolved_level,
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

