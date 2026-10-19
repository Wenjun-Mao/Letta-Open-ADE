"""Memory infrastructure failures pause saved input, not Character tool apologies."""

import asyncio
from contextlib import asynccontextmanager
import time

import pytest
from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    IntegrityError,
    InterfaceError,
    OperationalError,
    ProgrammingError,
    TimeoutError as PoolTimeoutError,
)

from ade_api.features.agent_runtime import worker_finalization
from ade_api.features.agent_runtime.executor import ConversationExecutor, curated_tools
from ade_api.features.agent_runtime.provider_tracing import AttemptTrace
from ade_api.features.agent_runtime.retry import is_retryable
from ade_api.features.agent_runtime.turn_recall import MemoryLookupError, TurnRecall
from ade_api.features.agent_runtime.worker_claims import ClaimedRun
from ade_api.features.agent_runtime.worker_finalization import RunFinalizer


def database_error(kind, *, invalidated=False):
    return kind(
        "synthetic relationship read",
        {},
        RuntimeError("private database details"),
        connection_invalidated=invalidated,
    )


def unavailable_errors():
    return [
        database_error(OperationalError),
        database_error(InterfaceError),
        database_error(DBAPIError, invalidated=True),
        DisconnectionError("private pool details"),
        PoolTimeoutError("private pool details"),
        ConnectionRefusedError("private connection details"),
    ]


class Banks:
    def __init__(self, failure):
        self.failure = failure

    async def ensure_ready(self, *args, **kwargs):
        if self.failure is not None:
            raise self.failure


class Native:
    async def recall(self, *args, **kwargs):
        return {"results": [{"id": "memory-1", "text": "Original memory"}]}


def recall_for(banks, *, trace=None):
    return TurnRecall(
        banks=banks,
        client=Native(),
        bank_id="owned-bank",
        deadline=time.monotonic() + 10,
        trace=trace,
    )


@pytest.mark.parametrize(
    "failure", unavailable_errors(), ids=lambda error: type(error).__name__
)
def test_database_lookup_failure_has_safe_pause_reason_and_can_recover(failure):
    async def scenario():
        records = []
        trace = AttemptTrace(attempt=1)
        trace.record_private = lambda event, value: records.append((event, value))
        banks = Banks(failure)
        recall = recall_for(banks, trace=trace)
        with pytest.raises(MemoryLookupError) as caught:
            await recall.lookup("immutable accepted input")
        assert caught.value.detail_code == "memory_lookup_database_unavailable"
        assert caught.value.__cause__ is failure
        assert not is_retryable(caught.value)
        assert recall.observations == []
        assert trace.memory_lookup_active is False
        assert records[-1] == (
            "memory_lookup.failed",
            {
                "lookup_contract": "ade-memory-lookup-v2",
                "lookup_number": 1,
                "phase": "automatic",
                "bank_id": "owned-bank",
                "query": "immutable accepted input",
                "limit": 20,
                "error_code": "memory_lookup_database_unavailable",
            },
        )
        assert "private" not in str(records)
        banks.failure = None
        assert await recall.lookup("immutable accepted input") == [
            {"id": "memory-1", "text": "Original memory"}
        ]

    asyncio.run(scenario())


class Character:
    def __init__(self):
        self.calls = 0

    async def chat_completion(self, *args, **kwargs):
        self.calls += 1
        if self.calls > 1:
            raise AssertionError(
                "Memory outage must not dispatch an apology continuation"
            )
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "tool-1",
                                "type": "function",
                                "function": {
                                    "name": "search_memory",
                                    "arguments": '{"query":"prior history"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }


@pytest.mark.parametrize(
    "failure", unavailable_errors(), ids=lambda error: type(error).__name__
)
def test_discretionary_database_lookup_failure_stops_before_second_character_request(
    failure,
):
    async def scenario():
        recall, character = recall_for(Banks(failure)), Character()
        with pytest.raises(MemoryLookupError):
            await ConversationExecutor(character).execute(
                model_key="synthetic::character",
                messages=[{"role": "user", "content": "Remember prior history?"}],
                timeout_seconds=1,
                max_output_tokens=256,
                tools=curated_tools(["search_memory"], search_memory=recall.search),
            )
        assert character.calls == 1
        assert recall.observations == []

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "failure",
    [
        database_error(ProgrammingError),
        database_error(IntegrityError),
        ValueError("bug"),
        asyncio.CancelledError(),
    ],
    ids=lambda error: type(error).__name__,
)
def test_programming_integrity_and_cancellation_errors_are_not_reclassified(failure):
    async def scenario():
        with pytest.raises(type(failure)) as caught:
            await recall_for(Banks(failure)).lookup("saved input")
        assert caught.value is failure

    asyncio.run(scenario())


def test_normalized_database_failure_pauses_the_same_saved_run(monkeypatch):
    async def scenario():
        run = {
            "id": "saved-run",
            "status": "running",
            "attempt_count": 1,
            "cancellation_requested_at": None,
        }
        events, finished_attempts = [], []

        class Engine:
            @asynccontextmanager
            async def begin(self):
                yield object()

        class Runs:
            async def finish_attempt(self, attempt_id, **values):
                finished_attempts.append((attempt_id, values))

            async def finish(self, *args, **kwargs):
                raise AssertionError(
                    "Memory availability failure must not terminally fail saved input"
                )

        class Leases:
            async def owns(self, token, run_id):
                return token == "owned-token" and run_id == "saved-run"

            async def release_owned(self, token, run_id):
                return await self.owns(token, run_id)

        class Lifecycle:
            async def pause(self, run_id, *, detail_code):
                assert run_id == "saved-run"
                run.update(status="paused", error_detail_code=detail_code)

        async def lock_run(connection, run_id):
            assert run_id == "saved-run"
            return {}, run

        async def append_event(repository, **values):
            events.append(values)

        monkeypatch.setattr(worker_finalization, "lock_run", lock_run)
        monkeypatch.setattr(
            worker_finalization, "RunRepository", lambda connection: Runs()
        )
        monkeypatch.setattr(
            worker_finalization,
            "ConversationLeaseRepository",
            lambda connection: Leases(),
        )
        monkeypatch.setattr(
            worker_finalization,
            "RunLifecycleRepository",
            lambda connection: Lifecycle(),
        )
        monkeypatch.setattr(worker_finalization, "append_run_event", append_event)
        try:
            await recall_for(Banks(database_error(OperationalError))).lookup(
                "saved input"
            )
        except MemoryLookupError as failure:
            await RunFinalizer(Engine()).commit_failure(
                ClaimedRun(run=run, lease_token="owned-token", recovered=False),
                "attempt-1",
                failure,
            )
        assert run["status"] == "paused"
        assert run["error_detail_code"] == "memory_lookup_database_unavailable"
        assert finished_attempts[0][1]["status"] == "failed"
        assert [event["event_type"] for event in events] == ["run.paused"]

    asyncio.run(scenario())
