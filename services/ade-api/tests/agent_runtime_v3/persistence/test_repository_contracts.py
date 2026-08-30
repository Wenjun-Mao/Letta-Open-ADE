from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.ext.asyncio import AsyncConnection

from ade_api.features.agent_runtime_v3.persistence.base import IdempotencyConflictError
from ade_api.features.agent_runtime_v3.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime_v3.persistence.memory import MemoryRepository
from ade_api.features.agent_runtime_v3.persistence.runs import RunRepository


class _Result:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    def mappings(self) -> _Result:
        return self

    def one_or_none(self) -> dict[str, Any] | None:
        return self._row


class _RecordingConnection:
    def __init__(self, rows: list[dict[str, Any] | None]) -> None:
        self.rows = rows
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> _Result:
        self.statements.append(statement)
        return _Result(self.rows.pop(0))


class _RevisionConnection:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    async def execute(self, statement: Any) -> _Result:
        self.statements.append(statement)
        if len(self.statements) == 1:
            return _Result({"id": "revision", "fact_id": "fact"})
        return cast(Any, type("UpdateResult", (), {"rowcount": 1})())


class _RowsResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _RowsResult:
        return self

    def one_or_none(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class _SummaryConnection:
    def __init__(self) -> None:
        self.statements: list[Any] = []
        self.results = [
            _RowsResult([]),
            _RowsResult(
                [
                    {"id": "message-1", "sequence": 1},
                    {"id": "message-2", "sequence": 2},
                ]
            ),
        ]

    async def execute(self, statement: Any) -> _RowsResult:
        self.statements.append(statement)
        return self.results.pop(0)


def test_run_accept_uses_database_idempotency_and_replays_the_same_hash() -> None:
    connection = _RecordingConnection(
        [None, {"id": "existing-run", "request_hash": "request-hash"}]
    )
    repository = RunRepository(cast(AsyncConnection, connection))

    run, replayed = asyncio.run(
        repository.accept(
            {
                "id": "new-run",
                "workspace_id": "workspace",
                "conversation_id": "conversation",
                "idempotency_key": "request-key",
                "request_hash": "request-hash",
                "status": "pending",
            }
        )
    )

    statement = str(connection.statements[0].compile(dialect=dialect()))
    assert "ON CONFLICT (conversation_id, idempotency_key) DO NOTHING" in statement
    assert replayed is True
    assert run["id"] == "existing-run"


def test_run_accept_rejects_reused_idempotency_key_for_different_content() -> None:
    connection = _RecordingConnection(
        [None, {"id": "existing-run", "request_hash": "old"}]
    )
    repository = RunRepository(cast(AsyncConnection, connection))

    with pytest.raises(IdempotencyConflictError, match="different request hash"):
        asyncio.run(
            repository.accept(
                {
                    "id": "new-run",
                    "workspace_id": "workspace",
                    "conversation_id": "conversation",
                    "idempotency_key": "request-key",
                    "request_hash": "new",
                    "status": "pending",
                }
            )
        )


def test_memory_revision_must_advance_the_fact_version_exactly_once() -> None:
    repository = MemoryRepository(cast(AsyncConnection, object()))

    with pytest.raises(ValueError, match="advance the expected fact version"):
        asyncio.run(
            repository.create_revision(
                {
                    "id": "revision",
                    "fact_id": "fact",
                    "fact_version": 9,
                },
                expected_fact_version=7,
                next_fact_status="active",
                updated_at=datetime.now(UTC),
            )
        )


def test_memory_revision_exists_before_projection_references_it() -> None:
    connection = _RevisionConnection()
    repository = MemoryRepository(cast(AsyncConnection, connection))

    asyncio.run(
        repository.create_revision(
            {
                "id": "revision",
                "fact_id": "fact",
                "workspace_id": "workspace",
                "subject_id": "subject",
                "operation": "correct",
                "fact_version": 2,
                "value": "new",
                "run_id": "run",
            },
            expected_fact_version=1,
            next_fact_status="active",
            updated_at=datetime.now(UTC),
        )
    )

    assert connection.statements[0].is_insert
    assert connection.statements[1].is_update


def test_compaction_requires_complete_contiguous_summary_sources() -> None:
    connection = _SummaryConnection()
    repository = ConversationRepository(cast(AsyncConnection, connection))

    with pytest.raises(ValueError, match="contiguous history prefix"):
        asyncio.run(
            repository.create_compaction(
                payload={
                    "id": "summary-1",
                    "conversation_id": "conversation-1",
                    "version": 1,
                    "through_sequence": 2,
                    "content": "A summary.",
                    "run_id": "run-1",
                    "previous_summary_id": None,
                    "model_key": "source::model",
                    "provider_request_id": "provider-1",
                    "prompt_sha256": "a" * 64,
                    "input_sha256": "b" * 64,
                },
                source_message_ids=("message-1",),
                expected_summary_version=0,
                expected_previous_summary_id=None,
            )
        )

    assert len(connection.statements) == 2
