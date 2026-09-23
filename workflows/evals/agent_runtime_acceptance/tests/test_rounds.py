from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from workflows.evals.agent_runtime_acceptance.client import RunTimeout, SseEvent
from workflows.evals.agent_runtime_acceptance.normalization import _normalize_run_events
from workflows.evals.agent_runtime_acceptance.qualification import (
    is_eligible_primary_matrix,
)
from workflows.evals.agent_runtime_acceptance.runner import (
    _capability_checks,
    execute_case,
    run_primary_rounds,
)


@dataclass(frozen=True)
class _Turn:
    conversation_key: str
    user: str


@dataclass(frozen=True)
class _InitialFact:
    subject_key: str
    value: str
    fact_type: str
    qualifier: str | None = None


@dataclass(frozen=True)
class _Case:
    key: str
    conversations: dict[str, tuple[str, str]]
    turns: tuple[_Turn, ...]
    initial_facts: tuple[object, ...] = ()
    prelude_messages: tuple[object, ...] = ()
    fact_assertions: tuple[object, ...] = ()
    assistant_assertions: tuple[object, ...] = ()
    enabled_tools: tuple[str, ...] = ()
    expected_tool_observations: tuple[str, ...] = ()
    require_failed_tool_result: bool = False


class _FakeClient:
    def __init__(self, *, status: str = "succeeded", retry: bool = False) -> None:
        self.status = status
        self.retry = retry
        self.session_payloads: list[dict[str, Any]] = []
        self.cancelled: list[str] = []
        self._counter = 0
        self._conversations: dict[str, tuple[str, str]] = {}

    async def create_evaluation_session(self, **payload: Any) -> dict[str, Any]:
        self.session_payloads.append(
            {key: value for key, value in payload.items() if value is not None}
        )
        self._counter += 1
        sequence = self._counter
        definition_id = payload.get("agent_definition_id") or f"definition-{sequence}"
        subject_id = payload.get("memory_subject_id") or f"subject-{sequence}"
        conversation_id = f"conversation-{sequence}"
        self._conversations[conversation_id] = (definition_id, subject_id)
        return {
            "session_id": f"session-{sequence}",
            "agent_definition": {"id": definition_id, "deployments": []},
            "memory_subject": {"id": subject_id},
            "conversation": {"id": conversation_id},
        }

    async def accept_turn(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self._counter += 1
        return {
            "run_id": f"run-{self._counter}",
            "events_url": f"/api/v3/runs/run-{self._counter}/events",
        }

    async def await_terminal(
        self, accepted: dict[str, Any], *, timeout_seconds: float
    ) -> tuple[dict[str, Any], tuple[SseEvent, ...]]:
        del timeout_seconds
        run_id = accepted["run_id"]
        events: list[SseEvent] = []
        raw_events = [
            ("run.started", {}),
            ("model.request.started", {"role": "conversation", "request_number": 1}),
            ("model.response.completed", {"role": "conversation", "request_number": 1}),
        ]
        if self.retry:
            raw_events.append(("retry.scheduled", {}))
        raw_events.extend(
            [
                ("model.request.started", {"role": "reviewer", "request_number": 1}),
                ("model.response.completed", {"role": "reviewer", "request_number": 1}),
                (
                    "message.committed"
                    if self.status == "succeeded"
                    else f"run.{self.status}",
                    {"role": "assistant"} if self.status == "succeeded" else {},
                ),
            ]
        )
        if self.status == "succeeded":
            raw_events.append(("run.completed", {"usage": {"total_tokens": 12}}))
        previous_id: str | None = None
        request_ids: dict[tuple[str, int], str] = {}
        for sequence, (event_type, payload) in enumerate(raw_events, start=1):
            event_id = f"{run_id}-{sequence}"
            causation_id = previous_id
            if event_type == "model.request.started":
                request_ids[(payload["role"], payload["request_number"])] = event_id
            elif event_type == "model.response.completed":
                causation_id = request_ids[(payload["role"], payload["request_number"])]
            events.append(
                SseEvent(
                    event_id=event_id,
                    event_type=event_type,
                    data={
                        "id": event_id,
                        "run_id": run_id,
                        "sequence": sequence,
                        "type": event_type,
                        "correlation_id": run_id,
                        "causation_id": causation_id,
                        "payload": payload,
                    },
                )
            )
            previous_id = event_id
        return (
            {
                "id": run_id,
                "status": self.status,
                "attempt_count": 2 if self.retry else 1,
                "started_at": "2026-08-29T12:00:00Z",
                "finished_at": "2026-08-29T12:00:01Z",
            },
            tuple(events),
        )

    async def get_evaluation_session_state(
        self, conversation_id: str
    ) -> dict[str, Any]:
        _definition_id, subject_id = self._conversations[conversation_id]
        return {
            "conversation": {
                "id": conversation_id,
                "messages": [{"role": "assistant", "content": "hello"}],
            },
            "memory_subject": {"id": subject_id},
            "memories": {
                "facts": [
                    {
                        "id": "fact-1",
                        "fact_type": "person.preference",
                        "entity_id": subject_id,
                        "qualifier": "place",
                        "value": "Royal Ontario Museum",
                        "status": "active",
                    }
                ]
            },
            "latest_run": None,
        }

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        self.cancelled.append(run_id)
        return {"id": run_id, "status": "cancelled"}

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return {"id": run_id, "status": "cancelled"}


def _case(key: str = "canonical") -> _Case:
    return _Case(
        key=key,
        conversations={"primary": ("primary", "primary")},
        turns=(_Turn("primary", "hello"),),
    )


def test_sessions_build_shared_agent_and_subject_graphs() -> None:
    async def scenario() -> None:
        client = _FakeClient(retry=True)
        case = _Case(
            key="shared",
            conversations={
                "first": ("agent-a", "subject-a"),
                "second": ("agent-a", "subject-b"),
                "third": ("agent-b", "subject-b"),
            },
            turns=(_Turn("first", "hello"),),
            enabled_tools=("get_weather",),
        )
        result = await execute_case(
            client=client,
            case=case,
            namespace="acceptance-shared",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            prompt_key="chat_prompt",
            persona_key="chat_persona",
            timeout_seconds=180,
            retry_count=1,
        )

        assert result.score["pass"] is True
        assert result.turns[0].attempt_count == 2
        assert len(result.resources.conversation_ids) == 3
        first, second, third = client.session_payloads
        assert first["tool_names"] == ("search_memory", "get_weather")
        assert first["prompt_key"] == "chat_prompt"
        assert first["persona_key"] == "chat_persona"
        assert second["agent_definition_id"] == "definition-1"
        assert "model_key" not in second and "tool_names" not in second
        assert "prompt_key" not in second and "persona_key" not in second
        assert third["memory_subject_id"] == "subject-2"
        assert "agent_definition_id" not in third
        assert third["prompt_key"] == "chat_prompt"
        assert third["persona_key"] == "chat_persona"

    asyncio.run(scenario())


def test_initial_facts_use_a_separate_no_tool_session_and_typed_state() -> None:
    async def scenario() -> None:
        client = _FakeClient()
        case = _Case(
            key="typed-setup",
            conversations={"primary": ("primary", "primary")},
            turns=(_Turn("primary", "hello"),),
            initial_facts=(
                _InitialFact(
                    subject_key="primary",
                    fact_type="person.preference",
                    qualifier="place",
                    value="Royal Ontario Museum",
                ),
            ),
        )
        result = await execute_case(
            client=client,
            case=case,
            namespace="acceptance-typed",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            prompt_key="chat_prompt",
            persona_key="chat_persona",
            timeout_seconds=180,
            retry_count=0,
        )

        assert result.score["pass"] is True
        assert len(result.resources.conversation_ids) == 2
        assert client.session_payloads[1]["tool_names"] == ()
        assert client.session_payloads[1]["memory_subject_id"] == "subject-1"
        assert client.session_payloads[1]["prompt_key"] == "chat_prompt"
        assert client.session_payloads[1]["persona_key"] == "chat_persona"

    asyncio.run(scenario())


def test_timeout_cancels_the_accepted_run_before_case_failure() -> None:
    class _TimedOutClient(_FakeClient):
        def __init__(self) -> None:
            super().__init__(status="cancelled")
            self.waits = 0

        async def await_terminal(
            self, accepted: dict[str, Any], *, timeout_seconds: float
        ) -> tuple[dict[str, Any], tuple[SseEvent, ...]]:
            self.waits += 1
            if self.waits == 1:
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
            prompt_key="chat_prompt",
            persona_key="chat_persona",
            timeout_seconds=180,
            retry_count=0,
        )
        assert client.cancelled
        assert result.infrastructure["terminal_statuses"] == ["cancelled"]
        assert result.score["pass"] is False

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "event_type", ["model.request.failed", "model.request.cancelled"]
)
def test_provider_terminal_events_remain_infrastructure_failures(
    event_type: str,
) -> None:
    started_id = "event-1"
    events = (
        SseEvent(
            event_id=started_id,
            event_type="model.request.started",
            data={
                "id": started_id,
                "run_id": "run-1",
                "sequence": 1,
                "type": "model.request.started",
                "correlation_id": "run-1",
                "causation_id": None,
                "payload": {
                    "stage": "conversation",
                    "operation": "chat.completions",
                    "request_id": "request-1",
                    "request_number": 1,
                },
            },
        ),
        SseEvent(
            event_id="event-2",
            event_type=event_type,
            data={
                "id": "event-2",
                "run_id": "run-1",
                "sequence": 2,
                "type": event_type,
                "correlation_id": "run-1",
                "causation_id": started_id,
                "payload": {
                    "stage": "conversation",
                    "operation": "chat.completions",
                    "request_id": "request-1",
                    "request_number": 1,
                    "error_code": "provider_timeout",
                },
            },
        ),
        SseEvent(
            event_id="event-3",
            event_type="run.failed",
            data={
                "id": "event-3",
                "run_id": "run-1",
                "sequence": 3,
                "type": "run.failed",
                "correlation_id": "run-1",
                "causation_id": "event-2",
                "payload": {},
            },
        ),
    )
    _, _, score_events, _, failures, _ = _normalize_run_events(
        "run-1", events, "failed"
    )
    assert "model.request" in [event.type for event in score_events]
    assert any(
        failure["kind"] == "provider_request_failure"
        and failure["event_type"] == event_type
        for failure in failures
    )


def test_qualification_and_summary_requirements_stay_fail_closed() -> None:
    passing = SimpleNamespace(
        kind="primary",
        execution_mode="live-api",
        complete_matrix=True,
        passed=True,
        case_keys=("a",),
    )
    rounds = [
        SimpleNamespace(**{**passing.__dict__, "index": index}) for index in range(1, 4)
    ]
    assert is_eligible_primary_matrix(
        rounds, canonical_case_keys=("a",), required_rounds=3
    )

    case = _Case(
        key="summary",
        conversations={"primary": ("primary", "primary")},
        turns=(_Turn("primary", "hello"),),
        prelude_messages=(
            SimpleNamespace(
                conversation_key="primary",
                count=1,
                user_template="history {index}",
                summary="summary",
                summary_through_sequence=2,
            ),
        ),
    )
    checks = _capability_checks(
        case,
        (
            SimpleNamespace(
                event_type="summary.committed", payload={"through_sequence": 2}
            ),
        ),
        [
            {
                "conversation_key": "primary",
                "conversation_state": {"messages": [{}, {}, {}, {}]},
            }
        ],
    )
    assert all(check["pass"] for check in checks)


def test_failed_matrix_stops_after_the_completed_first_round() -> None:
    class _UnavailableClient(_FakeClient):
        async def create_evaluation_session(self, **_payload: Any) -> dict[str, Any]:
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
            prompt_key="chat_prompt",
            persona_key="chat_persona",
            timeout_seconds=180,
            retry_count=0,
            session_scope_sink=scopes,
        )
        assert len(rounds) == 1
        assert rounds[0].complete_matrix is True
        assert rounds[0].passed is False
        assert scopes == []

    asyncio.run(scenario())


def test_budget_exhaustion_stops_scheduling_later_cases() -> None:
    class _UnavailableClient(_FakeClient):
        async def create_evaluation_session(self, **_payload: Any) -> dict[str, Any]:
            raise ConnectionError("synthetic cap")

    checks = 0

    def exhausted() -> bool:
        nonlocal checks
        checks += 1
        return checks >= 2

    async def scenario() -> None:
        rounds = await run_primary_rounds(
            client=_UnavailableClient(),
            cases=(_case("case-a"), _case("case-b")),
            canonical_case_keys=("case-a", "case-b"),
            namespace="acceptance-budget",
            rounds=3,
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            prompt_key="chat_prompt",
            persona_key="chat_persona",
            timeout_seconds=180,
            retry_count=0,
            budget_exhausted=exhausted,
        )
        assert len(rounds) == 1
        assert rounds[0].case_keys == ("case-a",)
        assert rounds[0].complete_matrix is False
        assert rounds[0].passed is False

    asyncio.run(scenario())
