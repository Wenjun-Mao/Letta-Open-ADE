"""Connection helpers that keep database URLs outside shared application settings."""

from __future__ import annotations

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def async_database_url(database_url: str) -> str:
    """Return a Psycopg async SQLAlchemy URL without changing its credentials."""

    url: URL = make_url(database_url)
    if url.drivername in {"postgresql", "postgres"}:
        url = url.set(drivername="postgresql+psycopg")
    elif url.drivername != "postgresql+psycopg":
        raise ValueError("ADE persistence requires a PostgreSQL Psycopg URL")
    return url.render_as_string(hide_password=False)


def create_persistence_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(async_database_url(database_url), pool_pre_ping=True)
