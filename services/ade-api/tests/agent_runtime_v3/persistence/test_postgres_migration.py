from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text

from ade_api.features.agent_runtime_v3.persistence.validation import (
    validate_database_at_head,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="ADE_TEST_DATABASE_URL is required for PostgreSQL pgvector migration tests",
)


def _sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    raise ValueError("ADE_TEST_DATABASE_URL must be a PostgreSQL URL")


def test_alembic_upgrade_creates_named_ade_pgvector_schema() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(_sync_database_url(DATABASE_URL))
    try:
        with engine.connect() as connection:
            validate_database_at_head(connection)
            inspector = inspect(connection)
            assert "memory_embeddings" in inspector.get_table_names(schema="ade")
            summary_columns = {
                column["name"]
                for column in inspector.get_columns("conversation_summaries", schema="ade")
            }
            assert {
                "previous_summary_id",
                "model_key",
                "provider_request_id",
                "prompt_sha256",
                "input_sha256",
            } <= summary_columns
            assert "uq_runs_active_conversation" in {
                index["name"] for index in inspector.get_indexes("runs", schema="ade")
            }
            assert connection.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
            )
    finally:
        engine.dispose()
