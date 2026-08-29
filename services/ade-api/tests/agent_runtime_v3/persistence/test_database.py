from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.persistence.database import async_database_url


def test_async_database_url_uses_psycopg_for_plain_postgres_url() -> None:
    assert (
        async_database_url("postgresql://ade:secret@localhost:5432/ade_test")
        == "postgresql+psycopg://ade:secret@localhost:5432/ade_test"
    )


def test_async_database_url_rejects_non_postgres_url() -> None:
    with pytest.raises(ValueError, match="PostgreSQL Psycopg"):
        async_database_url("sqlite+aiosqlite:///tmp/ade.db")
