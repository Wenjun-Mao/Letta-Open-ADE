from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from workflows.evals.agent_runtime_v3_acceptance.qualification import (
    is_eligible_primary_matrix,
)
from workflows.evals.agent_runtime_v3_acceptance.runner import execute_case


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
        yield SimpleNamespace(
            event_id="1",
            event_type="run.started",
            data={
                "run_id": run_id,
                "sequence": 1,
                "type": "run.started",
                "payload": {},
            },
        )
        yield SimpleNamespace(
            event_id="2",
            event_type="model.request",
            data={
                "run_id": run_id,
                "sequence": 2,
                "type": "model.request",
                "payload": {"role": "conversation"},
            },
        )
        yield SimpleNamespace(
            event_id="3",
            event_type="model.response",
            data={
                "run_id": run_id,
                "sequence": 3,
                "type": "model.response",
                "payload": {"role": "conversation"},
            },
        )
        if self.retry:
            yield SimpleNamespace(
                event_id="4",
                event_type="retry.scheduled",
                data={
                    "run_id": run_id,
                    "sequence": 4,
                    "type": "retry.scheduled",
                    "payload": {},
                },
            )
        yield SimpleNamespace(
            event_id="5",
            event_type="memory.review.request",
            data={
                "run_id": run_id,
                "sequence": 5,
                "type": "memory.review.request",
                "payload": {},
            },
        )
        if self.reviewed:
            yield SimpleNamespace(
                event_id="6",
                event_type="memory.reviewed",
                data={
                    "run_id": run_id,
                    "sequence": 6,
                    "type": "memory.reviewed",
                    "payload": {},
                },
            )
        message_sequence = 7 if self.reviewed else 6
        yield SimpleNamespace(
            event_id=str(message_sequence),
            event_type="message.committed",
            data={
                "run_id": run_id,
                "sequence": message_sequence,
                "type": "message.committed",
                "payload": {"role": "assistant", "content": "hello"},
            },
        )
        terminal_sequence = message_sequence + 1
        yield SimpleNamespace(
            event_id=str(terminal_sequence),
            event_type=f"run.{self.status if self.status != 'succeeded' else 'completed'}",
            data={
                "run_id": run_id,
                "sequence": terminal_sequence,
                "type": f"run.{self.status if self.status != 'succeeded' else 'completed'}",
                "payload": {},
            },
        )

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return {
            "id": run_id,
            "status": self.status,
            "attempt_count": 2 if self.retry else 1,
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


def test_reviewer_and_message_atomicity_is_a_required_success_invariant() -> None:
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
            failure["kind"] == "reviewer_atomicity"
            for failure in result.infrastructure["failures"]
        )

    asyncio.run(scenario())
