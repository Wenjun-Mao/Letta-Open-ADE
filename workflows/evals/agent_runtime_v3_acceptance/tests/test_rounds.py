from __future__ import annotations

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from workflows.evals.agent_runtime_v3_acceptance.client import SseEvent
from workflows.evals.agent_runtime_v3_acceptance.normalization import (
    _normalize_run_events,
)
from workflows.evals.agent_runtime_v3_acceptance.qualification import (
    is_eligible_primary_matrix,
)
from workflows.evals.agent_runtime_v3_acceptance.runner import (
    CaseStageError,
    execute_case,
    run_primary_rounds,
)


@dataclass(frozen=True)
class _Turn:
    conversation_key: str
    user: str


@dataclass(frozen=True)
class _Prelude:
    conversation_key: str
    count: int
    user_template: str
    summary: str
    summary_through_sequence: int


@dataclass(frozen=True)
class _InitialFact:
    subject_key: str
    value: str
    fact_type: str
    qualifier: str | None = None
    key: str = ""


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
    enabled_tools: tuple[str, ...] = ()
    expected_tool_observations: tuple[str, ...] = ()
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
        self.definition_payloads: list[dict[str, Any]] = []

    async def create_definition(self, **payload: Any) -> dict[str, Any]:
        self.definition_payloads.append(payload)
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
            (
                "model.request.started",
                {"role": "conversation", "request_number": 1},
            ),
            (
                "model.response.completed",
                {"role": "conversation", "request_number": 1},
            ),
        ]
        if self.retry:
            events.append(("retry.scheduled", {}))
        events.append(
            ("model.request.started", {"role": "reviewer", "request_number": 1})
        )
        if self.reviewed:
            events.append(
                (
                    "model.response.completed",
                    {"role": "reviewer", "request_number": 1},
                )
            )
        if self.status == "succeeded":
            events.append(("message.committed", {"role": "assistant"}))
        terminal_type = (
            "run.completed" if self.status == "succeeded" else f"run.{self.status}"
        )
        terminal_payload = {"usage": {"total_tokens": 12}}
        if self.status == "failed":
            terminal_payload.update(
                {
                    "error_code": "runtime_validation_error",
                    "error_detail_code": "conversation_output_empty",
                }
            )
        events.append((terminal_type, terminal_payload))
        prior_event_id = None
        request_ids: dict[tuple[str, int], str] = {}
        for sequence, (event_type, payload) in enumerate(events, start=1):
            event_id = f"{run_id}-event-{sequence}"
            causation_id = prior_event_id
            if event_type == "model.request.started":
                request_ids[(payload["role"], payload["request_number"])] = event_id
            elif event_type == "model.response.completed":
                causation_id = request_ids[(payload["role"], payload["request_number"])]
            yield SimpleNamespace(
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
            prior_event_id = event_id

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


def test_case_definitions_enable_search_and_only_declared_curated_tools() -> None:
    async def scenario() -> None:
        client = _FakeClient()
        case = _Case(
            key="weather",
            conversations={"primary": ("primary", "primary")},
            turns=(_Turn("primary", "Weather in Toronto?"),),
            enabled_tools=("get_weather",),
        )

        await execute_case(
            client=client,
            case=case,
            namespace="acceptance-tools",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
        )

        assert client.definition_payloads[0]["tool_names"] == (
            "search_memory",
            "get_weather",
        )

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


def test_case_filtered_rounds_are_explicit_diagnostics() -> None:
    async def scenario() -> None:
        rounds = await run_primary_rounds(
            client=_FakeClient(),
            cases=(_case("weather_tool_failure"),),
            canonical_case_keys=("old_memory_deep_search", "weather_tool_failure"),
            namespace="acceptance-diagnostic",
            rounds=1,
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
            diagnostic=True,
        )

        assert rounds[0].kind == "diagnostic"
        assert rounds[0].execution_mode == "live-api-diagnostic"
        assert rounds[0].complete_matrix is False
        assert rounds[0].case_keys == ("weather_tool_failure",)

    asyncio.run(scenario())


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


@pytest.mark.parametrize(
    "event_type", ["model.request.failed", "model.request.cancelled"]
)
def test_provider_request_terminal_events_are_infrastructure_failures(
    event_type: str,
) -> None:
    request_id = "provider-request-1"
    started_id = "event-1"
    events = [
        SseEvent(
            event_id=started_id,
            event_type="model.request.started",
            data={
                "id": started_id,
                "run_id": "run-1",
                "sequence": 1,
                "type": "model.request.started",
                "attempt": 1,
                "correlation_id": "run-1",
                "causation_id": None,
                "payload": {
                    "stage": "conversation",
                    "operation": "chat.completions",
                    "request_id": request_id,
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
                "attempt": 1,
                "correlation_id": "run-1",
                "causation_id": started_id,
                "payload": {
                    "stage": "conversation",
                    "operation": "chat.completions",
                    "request_id": request_id,
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
                "attempt": 1,
                "correlation_id": "run-1",
                "causation_id": "event-2",
                "payload": {},
            },
        ),
    ]

    _, _, score_events, _, failures, _ = _normalize_run_events(
        "run-1", events, "failed"
    )

    score_event_types = [item.type for item in score_events]
    assert "model.request" in score_event_types
    assert event_type not in score_event_types
    assert any(
        failure["kind"] == "provider_request_failure"
        and failure["event_type"] == event_type
        for failure in failures
    )


def test_uncertain_create_response_is_registered_for_scoped_cleanup() -> None:
    class _UncertainCreateClient(_FakeClient):
        async def create_definition(self, **_payload: Any) -> dict[str, Any]:
            raise TimeoutError("creation outcome is unknown")

    async def scenario() -> None:
        scopes = []
        with pytest.raises(CaseStageError, match="definition_setup"):
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


def test_compaction_case_cannot_pass_without_a_versioned_summary_event() -> None:
    async def scenario() -> None:
        case = _Case(
            key="long-history",
            conversations={"primary": ("primary", "primary")},
            turns=(_Turn("primary", "confirm our history"),),
            prelude_messages=(
                _Prelude(
                    conversation_key="primary",
                    count=1,
                    user_template="history {index}",
                    summary="A prior history summary",
                    summary_through_sequence=2,
                ),
            ),
        )

        result = await execute_case(
            client=_FakeClient(),
            case=case,
            namespace="acceptance-summary",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
        )

        assert result.score["pass"] is False
        assert any(
            check["kind"] == "versioned_summary_committed"
            for check in result.infrastructure["failures"]
        )

    asyncio.run(scenario())


def test_initial_facts_use_natural_language_and_verify_public_typed_memory() -> None:
    class _SetupMemoryClient(_FakeClient):
        def __init__(self) -> None:
            super().__init__()
            self.setup_content: list[str] = []
            self.accepted_conversation_ids: list[str] = []

        async def accept_turn(
            self, conversation_id: str, content: str, *args: Any, **kwargs: Any
        ) -> dict[str, Any]:
            del args, kwargs
            self.accepted_conversation_ids.append(conversation_id)
            self.setup_content.append(content)
            return await super().accept_turn()

        async def get_subject_memories(self, subject_id: str) -> dict[str, Any]:
            return {
                "subject_id": subject_id,
                "facts": [
                    {
                        "id": "fact-1",
                        "fact_type": "person.preference",
                        "entity_id": subject_id,
                        "qualifier": "place",
                        "value": "Royal Ontario Museum",
                        "status": "active",
                    }
                ],
            }

    async def scenario() -> None:
        client = _SetupMemoryClient()
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
            namespace="acceptance-typed-setup",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
        )

        assert result.score["pass"] is True
        assert client.setup_content[0] == (
            "My favorite place is Royal Ontario Museum. Please remember it."
        )
        assert (
            client.accepted_conversation_ids[0] != client.accepted_conversation_ids[1]
        )

    asyncio.run(scenario())


def test_missing_public_setup_memory_is_a_safe_stage_specific_failure() -> None:
    class _MissingSetupMemoryClient(_FakeClient):
        async def get_subject_memories(self, subject_id: str) -> dict[str, Any]:
            return {"subject_id": subject_id, "facts": []}

    async def scenario() -> None:
        case = _Case(
            key="typed-setup-missing",
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
        rounds = await run_primary_rounds(
            client=_MissingSetupMemoryClient(),
            cases=(case,),
            canonical_case_keys=(case.key,),
            namespace="acceptance-typed-setup-missing",
            rounds=1,
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
        )

        failed_case = rounds[0].cases[0]
        failure = failed_case.infrastructure["failures"][0]
        assert failure == {
            "kind": "case_execution_error",
            "stage": "initial_fact_memory_verification",
            "pass": False,
            "error_type": "AssertionError",
            "message": "initial fact memory verification failed",
        }
        assert failed_case.setup_run_ids
        assert failed_case.events
        assert failed_case.infrastructure["terminal_statuses"] == ["succeeded"]
        assert failed_case.infrastructure["all_terminal"] is True

    asyncio.run(scenario())


def test_failed_setup_run_preserves_terminal_evidence_before_cleanup() -> None:
    async def scenario() -> None:
        case = _Case(
            key="typed-setup-run-failed",
            conversations={"primary": ("primary", "primary")},
            turns=(_Turn("primary", "hello"),),
            initial_facts=(
                _InitialFact(
                    subject_key="primary",
                    fact_type="person.preference",
                    qualifier="color",
                    value="青色",
                ),
            ),
        )
        rounds = await run_primary_rounds(
            client=_FakeClient(status="failed"),
            cases=(case,),
            canonical_case_keys=(case.key,),
            namespace="acceptance-typed-setup-run-failed",
            rounds=1,
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            timeout_seconds=180,
            retry_count=0,
        )

        failed_case = rounds[0].cases[0]
        assert failed_case.score["pass"] is False
        assert len(failed_case.setup_run_ids) == 1
        assert "run.failed" in {event.event_type for event in failed_case.events}
        assert failed_case.infrastructure["terminal_statuses"] == ["failed"]
        assert failed_case.infrastructure["all_terminal"] is True
        assert {
            "kind": "run_failure",
            "pass": False,
            "run_id": failed_case.setup_run_ids[0],
            "stage": "unknown",
            "error_code": "runtime_validation_error",
            "error_detail_code": "conversation_output_empty",
        } in failed_case.infrastructure["failures"]

    asyncio.run(scenario())
