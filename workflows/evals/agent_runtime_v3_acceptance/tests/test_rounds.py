from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from workflows.evals.agent_runtime_v3_acceptance.qualification import (
    is_eligible_primary_matrix,
)
from workflows.evals.agent_runtime_v3_acceptance.runner import (
    execute_case,
    run_primary_rounds,
)


@dataclass(frozen=True)
class _Turn:
    conversation_key: str
    user: str


@dataclass(frozen=True)
class _Case:
    key: str
    conversations: dict[str, tuple[str, str]]
    turns: tuple[_Turn, ...]
    agent_keys: tuple[str, ...] = ("primary",)
    subject_keys: tuple[str, ...] = ("primary",)
    initial_facts: tuple[object, ...] = ()
    prelude_messages: tuple[object, ...] = ()
    fact_assertions: tuple[object, ...] = ()
    assistant_assertions: tuple[object, ...] = ()
    required_tools: tuple[str, ...] = ()
    require_failed_tool_result: bool = False


class _FakeClient:
    def __init__(
        self, *, status: str = "succeeded", retry: bool = False, reviewed: bool = True
    ) -> None:
        self.status = status
        self.retry = retry
        self.reviewed = reviewed
        self.counter = 0
        self.cancelled: list[str] = []

    async def create_definition(self, **_payload: Any) -> dict[str, Any]:
        self.counter += 1
        return {"id": f"definition-{self.counter}", "deployments": []}

    async def create_subject(self, *_args: Any) -> dict[str, Any]:
        self.counter += 1
        return {"id": f"subject-{self.counter}"}

    async def create_conversation(self, *_args: Any) -> dict[str, Any]:
        self.counter += 1
        return {"id": f"conversation-{self.counter}"}

    async def accept_turn(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self.counter += 1
        return {
            "run_id": f"run-{self.counter}",
            "events_url": f"/runs/run-{self.counter}/events",
            "idempotent_replay": False,
        }

    async def stream_events(self, url: str):
        run_id = url.split("/")[-2]
        events = [
            ("run.started", {}),
            ("model.request.started", {"role": "conversation"}),
            ("model.response.completed", {"role": "conversation"}),
        ]
        if self.retry:
            events.append(("retry.scheduled", {}))
        events.append(("model.request.started", {"role": "reviewer"}))
        if self.reviewed:
            events.append(("model.response.completed", {"role": "reviewer"}))
        if self.status == "succeeded":
            events.append(("message.committed", {"role": "assistant"}))
        terminal_type = (
            "run.completed" if self.status == "succeeded" else f"run.{self.status}"
        )
        events.append((terminal_type, {"usage": {"total_tokens": 12}}))
        for sequence, (event_type, payload) in enumerate(events, start=1):
            yield SimpleNamespace(
                event_id=str(sequence),
                event_type=event_type,
                data={
                    "run_id": run_id,
                    "sequence": sequence,
                    "type": event_type,
                    "payload": payload,
                },
            )

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return {
            "id": run_id,
            "status": self.status,
            "attempt_count": 2 if self.retry else 1,
            "started_at": "2026-08-29T12:00:00Z",
            "finished_at": "2026-08-29T12:00:01Z",
        }

    async def await_terminal(self, accepted: dict[str, Any], *, timeout_seconds: float):
        del timeout_seconds
        events = tuple(
            [event async for event in self.stream_events(accepted["events_url"])]
        )
        return await self.get_run(accepted["run_id"]), events

    async def get_conversation_state(self, _conversation_id: str) -> dict[str, Any]:
        return {"messages": [{"role": "assistant", "content": "hello"}]}

    async def get_subject_memories(self, subject_id: str) -> dict[str, Any]:
        return {"subject_id": subject_id, "facts": []}

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        self.cancelled.append(run_id)
        return {"id": run_id, "status": "cancelled"}


def _case(key: str = "canonical") -> _Case:
    return _Case(
        key=key,
        conversations={"primary": ("primary", "primary")},
        turns=(_Turn("primary", "hello"),),
    )


def test_normal_turn_and_retry_are_normalized_against_shared_contracts() -> None:
    async def scenario() -> None:
        result = await execute_case(
            client=_FakeClient(retry=True),
            case=_case(),
            namespace="acceptance-a",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=1,
        )
        assert result.score["pass"] is True
        assert result.turns[0].attempt_count == 2
        assert any(event.event_type == "retry.scheduled" for event in result.events)

    asyncio.run(scenario())


def test_failed_or_focused_or_fake_rounds_never_qualify() -> None:
    passing = SimpleNamespace(
        index=1,
        kind="primary",
        execution_mode="live-api",
        complete_matrix=True,
        passed=True,
        case_keys=("a", "b"),
    )
    sequential = [
        SimpleNamespace(**{**passing.__dict__, "index": index}) for index in range(1, 4)
    ]
    assert is_eligible_primary_matrix(
        sequential, canonical_case_keys=("a", "b"), required_rounds=3
    )
    assert not is_eligible_primary_matrix(
        [passing] * 2, canonical_case_keys=("a", "b"), required_rounds=3
    )
    assert not is_eligible_primary_matrix(
        [passing], canonical_case_keys=("a",), required_rounds=3
    )
    assert not is_eligible_primary_matrix(
        [
            SimpleNamespace(**{**item.__dict__, "execution_mode": "fake-transport"})
            for item in sequential
        ],
        canonical_case_keys=("a", "b"),
        required_rounds=3,
    )
    assert not is_eligible_primary_matrix(
        [
            SimpleNamespace(**{**item.__dict__, "complete_matrix": False})
            for item in sequential
        ],
        canonical_case_keys=("a", "b"),
        required_rounds=3,
    )


def test_cancellation_and_concurrent_requests_are_recorded_as_diagnostics() -> None:
    async def scenario() -> None:
        client = _FakeClient(status="cancelled")
        result = await execute_case(
            client=client,
            case=_case(),
            namespace="acceptance-cancelled",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
        )
        assert result.score["pass"] is False
        assert result.infrastructure["terminal_statuses"] == ["cancelled"]

    asyncio.run(scenario())


def test_client_deadline_cancels_and_waits_for_terminal_evidence() -> None:
    class _TimedOutClient(_FakeClient):
        def __init__(self) -> None:
            super().__init__(status="cancelled")
            self.wait_count = 0

        async def await_terminal(
            self, accepted: dict[str, Any], *, timeout_seconds: float
        ):
            self.wait_count += 1
            if self.wait_count == 1:
                from workflows.evals.agent_runtime_v3_acceptance.client import (
                    RunTimeout,
                )

                raise RunTimeout("deadline")
            return await super().await_terminal(
                accepted, timeout_seconds=timeout_seconds
            )

    async def scenario() -> None:
        client = _TimedOutClient()
        result = await execute_case(
            client=client,
            case=_case(),
            namespace="acceptance-timeout",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
        )
        assert client.cancelled
        assert client.wait_count == 2
        assert result.infrastructure["terminal_statuses"] == ["cancelled"]

    asyncio.run(scenario())


def test_reviewer_request_and_response_trace_is_a_required_success_invariant() -> None:
    async def scenario() -> None:
        result = await execute_case(
            client=_FakeClient(reviewed=False),
            case=_case(),
            namespace="acceptance-reviewer",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
        )
        assert result.score["pass"] is False
        assert any(
            failure["kind"] == "required_model_events" and failure["role"] == "reviewer"
            for failure in result.infrastructure["failures"]
        )

    asyncio.run(scenario())


def test_uncertain_create_response_is_registered_for_scoped_cleanup() -> None:
    class _UncertainCreateClient(_FakeClient):
        async def create_definition(self, **_payload: Any) -> dict[str, Any]:
            raise TimeoutError("creation outcome is unknown")

    async def scenario() -> None:
        scopes = []
        with pytest.raises(TimeoutError, match="unknown"):
            await execute_case(
                client=_UncertainCreateClient(),
                case=_case(),
                namespace="acceptance-uncertain",
                conversation_model_key="chat",
                reviewer_model_key="reviewer",
                embedding_model_key="embedding",
                timeout_seconds=180,
                retry_count=0,
                resource_scope_sink=scopes,
            )
        assert len(scopes) == 1
        assert scopes[0].definition_keys[0].startswith("acceptance-uncertain")

    asyncio.run(scenario())


def test_infrastructure_failure_finishes_the_matrix_then_stops_later_rounds() -> None:
    class _UnavailableClient(_FakeClient):
        async def create_definition(self, **_payload: Any) -> dict[str, Any]:
            raise ConnectionError("router unavailable")

    async def scenario() -> None:
        scopes = []
        rounds = await run_primary_rounds(
            client=_UnavailableClient(),
            cases=(_case("case-a"), _case("case-b")),
            canonical_case_keys=("case-a", "case-b"),
            namespace="acceptance-matrix",
            rounds=3,
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
            resource_scope_sink=scopes,
        )
        assert len(rounds) == 1
        assert rounds[0].complete_matrix is True
        assert rounds[0].passed is False
        assert [item.case_key for item in rounds[0].cases] == ["case-a", "case-b"]
        assert all(
            item.infrastructure["failures"][0]["kind"] == "case_execution_error"
            for item in rounds[0].cases
        )
        assert len(scopes) == 2

    asyncio.run(scenario())


def test_task_cancellation_preserves_uncertain_resource_scope() -> None:
    class _CancelledClient(_FakeClient):
        async def create_conversation(self, *_args: Any) -> dict[str, Any]:
            raise asyncio.CancelledError

    async def scenario() -> None:
        scopes = []
        with pytest.raises(asyncio.CancelledError):
            await run_primary_rounds(
                client=_CancelledClient(),
                cases=(_case("cancelled-case"),),
                canonical_case_keys=("cancelled-case",),
                namespace="acceptance-cancel-scope",
                rounds=3,
                conversation_model_key="chat",
                reviewer_model_key="reviewer",
                embedding_model_key="embedding",
                timeout_seconds=180,
                retry_count=0,
                resource_scope_sink=scopes,
            )

        assert any(scope.definition_keys for scope in scopes)
        assert any(scope.subject_external_keys for scope in scopes)

    asyncio.run(scenario())
