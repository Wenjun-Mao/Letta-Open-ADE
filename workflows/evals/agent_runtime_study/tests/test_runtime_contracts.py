from __future__ import annotations

import asyncio

import pytest

from workflows.evals.agent_runtime_study.contracts import (
    AgentDefinition,
    Conversation,
    ExecutorRequest,
    ExecutorResult,
    MemoryOperation,
    MemorySubject,
    RunEventType,
    RunStatus,
    RuntimePolicy,
    TurnRequest,
)
from workflows.evals.agent_runtime_study.repository import (
    IdempotencyConflictError,
    InMemoryStudyRepository,
)
from workflows.evals.agent_runtime_study.memory_review import (
    MemoryReviewDecision,
    MemoryReviewProposal,
    MemoryReviewRequest,
)
from workflows.evals.agent_runtime_study.runtime import StudyAgentRuntime
from workflows.evals.agent_runtime_study.semantic_retrieval import (
    EmbeddingRequestError,
)
from workflows.evals.agent_runtime_study.scripted import (
    ScriptStep,
    SharedScript,
    scripted_adapter,
)


class _ConcurrencyExecutor:
    name = "concurrency_probe"

    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    async def execute(self, request: ExecutorRequest) -> ExecutorResult:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.03)
        finally:
            self.active -= 1
        return ExecutorResult(
            assistant_text="ok",
            reasoning=(),
            events=(
                (RunEventType.MODEL_REQUEST, {"model_request_index": 1}),
                (RunEventType.MODEL_RESPONSE, {"model_request_index": 1}),
            ),
            raw_messages=(),
            usage={},
            model_request_count=1,
        )


def _runtime() -> tuple[StudyAgentRuntime, _ConcurrencyExecutor]:
    repository = InMemoryStudyRepository()
    repository.add_agent_definition(
        AgentDefinition(
            id="agent",
            name="agent",
            model_key="model",
            system_prompt="system",
            persona="persona",
            tool_names=(),
        )
    )
    repository.add_subject(MemorySubject(id="subject", external_key="user-1"))
    for conversation_id in ("conversation-a", "conversation-b"):
        repository.add_conversation(
            Conversation(
                id=conversation_id,
                agent_definition_id="agent",
                memory_subject_id="subject",
            )
        )
    executor = _ConcurrencyExecutor()
    return StudyAgentRuntime(repository=repository, executor=executor), executor


def test_idempotency_key_rejects_a_different_request_payload() -> None:
    async def scenario() -> None:
        runtime, _ = _runtime()
        first = TurnRequest(
            conversation_id="conversation-a",
            user_content="first",
            idempotency_key="same-key",
            policy=RuntimePolicy(timeout_seconds=2),
        )
        first_result = await runtime.run_turn(first)
        for index, event in enumerate(first_result.events):
            assert event.correlation_id == first_result.run.id
            assert event.causation_id == (
                first_result.events[index - 1].id if index else None
            )
            assert event.visibility.value == "operator"

        with pytest.raises(IdempotencyConflictError, match="different request"):
            await runtime.run_turn(
                TurnRequest(
                    conversation_id="conversation-a",
                    user_content="changed",
                    idempotency_key="same-key",
                    policy=RuntimePolicy(timeout_seconds=2),
                )
            )

    asyncio.run(scenario())


def test_turn_acceptance_rolls_back_run_when_user_message_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        runtime, _ = _runtime()

        def fail_append(**_kwargs):
            raise RuntimeError("message persistence failed")

        monkeypatch.setattr(runtime.repository, "append_message", fail_append)
        with pytest.raises(RuntimeError, match="message persistence failed"):
            await runtime.run_turn(
                TurnRequest(
                    conversation_id="conversation-a",
                    user_content="hello",
                    idempotency_key="acceptance",
                    policy=RuntimePolicy(timeout_seconds=2),
                )
            )

        assert runtime.repository.runs == {}
        assert runtime.repository.idempotency == {}
        assert runtime.repository.list_messages("conversation-a") == ()

    asyncio.run(scenario())


def test_reviewed_memory_commit_failure_has_no_tool_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        runtime, _ = _runtime()
        script = SharedScript((ScriptStep(text="hello"),))
        runtime.executor = scripted_adapter("custom_loop", script)

        class Reviewer:
            model_key = "reviewer"

            async def review(
                self, request: MemoryReviewRequest
            ) -> MemoryReviewDecision:
                return MemoryReviewDecision(
                    reviewer_model_key=self.model_key,
                    proposals=(
                        MemoryReviewProposal(
                            operation=MemoryOperation.ADD,
                            fact_type="person.name",
                            value="Alice",
                            evidence_quote="name is Alice",
                        ),
                    ),
                    raw_responses=(),
                    usage={},
                    model_request_count=1,
                    protocol_repaired=False,
                )

        runtime.memory_reviewer = Reviewer()

        def fail_commit(**_kwargs):
            raise RuntimeError("commit failed")

        monkeypatch.setattr(runtime.memory_policy, "apply_batch", fail_commit)
        result = await runtime.run_turn(
            TurnRequest(
                conversation_id="conversation-a",
                user_content="My name is Alice",
                idempotency_key="commit-failure",
                policy=RuntimePolicy(timeout_seconds=2),
            )
        )

        assert result.run.error_message == "commit failed"
        assert result.tool_executions == ()

    asyncio.run(scenario())


def test_cancellation_after_review_prevents_late_atomic_commit() -> None:
    async def scenario() -> None:
        runtime, _ = _runtime()

        class Signal:
            cancelled = False

            def is_set(self) -> bool:
                return self.cancelled

        signal = Signal()

        class Reviewer:
            model_key = "reviewer"

            async def review(
                self, request: MemoryReviewRequest
            ) -> MemoryReviewDecision:
                return MemoryReviewDecision(
                    reviewer_model_key=self.model_key,
                    proposals=(),
                    raw_responses=(),
                    usage={},
                    model_request_count=1,
                    protocol_repaired=False,
                )

        runtime.memory_reviewer = Reviewer()
        original_review_with_controls = runtime._review_with_controls

        async def review_then_cancel(*args, **kwargs):
            decision = await original_review_with_controls(*args, **kwargs)
            signal.cancelled = True
            return decision

        runtime._review_with_controls = review_then_cancel
        result = await runtime.run_turn(
            TurnRequest(
                conversation_id="conversation-a",
                user_content="cancel before commit",
                idempotency_key="late-cancel",
                policy=RuntimePolicy(timeout_seconds=2),
                cancellation=signal,
            )
        )

        assert result.run.status is RunStatus.CANCELLED
        assert result.assistant_message is None
        assert runtime.repository.list_subject_facts("subject", active_only=False) == ()

    asyncio.run(scenario())


@pytest.mark.parametrize(("retryable", "expected_attempts"), ((False, 1), (True, 2)))
def test_context_embedding_failures_use_exact_ade_retry_policy(
    monkeypatch: pytest.MonkeyPatch,
    retryable: bool,
    expected_attempts: int,
) -> None:
    async def scenario() -> None:
        runtime, _ = _runtime()
        calls = 0

        def fail_context(**_kwargs):
            nonlocal calls
            calls += 1
            raise EmbeddingRequestError("embedding failed", retryable=retryable)

        monkeypatch.setattr(runtime.context_builder, "build", fail_context)
        result = await runtime.run_turn(
            TurnRequest(
                conversation_id="conversation-a",
                user_content="trigger retrieval",
                idempotency_key=f"embedding-{retryable}",
                policy=RuntimePolicy(timeout_seconds=2, retry_count=1),
            )
        )

        assert result.run.status is RunStatus.FAILED
        assert result.run.attempt_count == expected_attempts
        assert calls == expected_attempts

    asyncio.run(scenario())


def test_conversations_sharing_a_subject_execute_concurrently() -> None:
    async def scenario() -> int:
        runtime, executor = _runtime()
        await asyncio.gather(
            runtime.run_turn(
                TurnRequest(
                    conversation_id="conversation-a",
                    user_content="one",
                    idempotency_key="one",
                    policy=RuntimePolicy(timeout_seconds=2),
                )
            ),
            runtime.run_turn(
                TurnRequest(
                    conversation_id="conversation-b",
                    user_content="two",
                    idempotency_key="two",
                    policy=RuntimePolicy(timeout_seconds=2),
                )
            ),
        )
        return executor.max_active

    assert asyncio.run(scenario()) == 2


def test_turns_in_one_conversation_are_serialized() -> None:
    async def scenario() -> int:
        runtime, executor = _runtime()
        await asyncio.gather(
            runtime.run_turn(
                TurnRequest(
                    conversation_id="conversation-a",
                    user_content="one",
                    idempotency_key="one",
                    policy=RuntimePolicy(timeout_seconds=2),
                )
            ),
            runtime.run_turn(
                TurnRequest(
                    conversation_id="conversation-a",
                    user_content="two",
                    idempotency_key="two",
                    policy=RuntimePolicy(timeout_seconds=2),
                )
            ),
        )
        return executor.max_active

    assert asyncio.run(scenario()) == 1
