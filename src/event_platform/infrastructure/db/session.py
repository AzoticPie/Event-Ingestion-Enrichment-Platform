"""Database engine and session management."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from event_platform.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.postgres_dsn,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_session() -> Generator[Session, None, None]:
    """Provide a request-scoped SQLAlchemy session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def transaction(session: Session) -> Generator[Session, None, None]:
    """Wrap operations in a rollback-safe transaction using an existing session."""
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise

