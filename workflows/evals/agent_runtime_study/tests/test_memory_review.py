from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from agent_runtime_eval_contracts import (
    AssistantAssertion,
    FixtureTurn,
    StudyCase,
    score_case,
)

from workflows.evals.agent_runtime_study.contracts import (
    AgentDefinition,
    Conversation,
    ExecutorRequest,
    ExecutorResult,
    MemoryOperation,
    MemorySubject,
    MessageRole,
    RunEventType,
    RunStatus,
    RuntimePolicy,
    TurnRequest,
)
from workflows.evals.agent_runtime_study.memory import MemoryPolicy
from workflows.evals.agent_runtime_study.memory_review import (
    FactRegistryError,
    MemoryEntityKind,
    MemoryReviewCoordinator,
    MemoryReviewDecision,
    MemoryReviewError,
    MemoryReviewProposal,
    MemoryReviewRequest,
    ReviewProtocolError,
    RouterMemoryReviewer,
    fact_key,
    parse_review_payload,
)
from workflows.evals.agent_runtime_study.repository import InMemoryStudyRepository
from workflows.evals.agent_runtime_study.runtime import StudyAgentRuntime
from workflows.evals.agent_runtime_study.observation_normalization import normalize_turn


def _repository() -> InMemoryStudyRepository:
    repository = InMemoryStudyRepository()
    repository.add_agent_definition(
        AgentDefinition(
            id="agent",
            name="agent",
            model_key="conversation-model",
            system_prompt="system",
            persona="persona",
            tool_names=("search_memory", "get_weather"),
        )
    )
    for subject_id in ("subject-a", "subject-b"):
        repository.add_subject(MemorySubject(id=subject_id, external_key=subject_id))
        repository.add_conversation(
            Conversation(
                id=f"conversation-{subject_id[-1]}",
                agent_definition_id="agent",
                memory_subject_id=subject_id,
            )
        )
    return repository


def test_fact_registry_derives_keys_and_rejects_unknown_qualifiers() -> None:
    assert fact_key("person.name", "subject-a", None) == "person.name|subject-a"
    assert (
        fact_key("person.preference", "subject-a", "music")
        == "person.preference|subject-a|music"
    )
    with pytest.raises(FactRegistryError, match="qualifier"):
        fact_key("person.preference", "subject-a", "unbounded-topic")
    with pytest.raises(FactRegistryError, match="Unknown fact type"):
        fact_key("custom.free_form", "subject-a", None)


def test_review_coordinator_assigns_one_server_entity_for_pet_facts() -> None:
    repository = _repository()
    user = repository.append_message(
        conversation_id="conversation-a",
        role=MessageRole.USER,
        content="My dog is Rocky and Rocky is a Husky.",
        run_id="run",
    )
    decision = MemoryReviewDecision(
        reviewer_model_key="reviewer",
        proposals=(
            MemoryReviewProposal(
                operation=MemoryOperation.ADD,
                fact_type="pet.name",
                value="Rocky",
                evidence_quote="dog is Rocky",
                entity_ref="new:pet-1",
                new_entity_label="Rocky",
            ),
            MemoryReviewProposal(
                operation=MemoryOperation.ADD,
                fact_type="pet.breed",
                value="Husky",
                evidence_quote="Rocky is a Husky",
                entity_ref="new:pet-1",
                new_entity_label="Rocky",
            ),
        ),
        raw_responses=('{"proposals": []}',),
        usage={},
        model_request_count=1,
        protocol_repaired=False,
    )
    prepared = MemoryReviewCoordinator(repository).prepare(
        subject_id="subject-a",
        current_user_message=user,
        decision=decision,
    )

    assert len(prepared.new_entities) == 1
    assert len({proposal.entity_id for proposal in prepared.proposals}) == 1
    assert {proposal.fact_type for proposal in prepared.proposals} == {
        "pet.name",
        "pet.breed",
    }
    with repository.transaction():
        for entity in prepared.new_entities:
            repository.add_memory_entity(entity)
        MemoryPolicy(repository).apply_batch(
            subject_id="subject-a",
            proposals=prepared.proposals,
            source_messages=(user,),
            run_id="run",
        )
    active = repository.list_subject_facts("subject-a", active_only=True)
    assert {fact.value for fact in active} == {"Rocky", "Husky"}
    assert len({fact.entity_id for fact in active}) == 1


def test_entity_defining_name_can_create_an_unbound_pet() -> None:
    repository = _repository()
    user = repository.append_message(
        conversation_id="conversation-a",
        role=MessageRole.USER,
        content="My dog is Rocky.",
        run_id="run",
    )
    decision = MemoryReviewDecision(
        reviewer_model_key="reviewer",
        proposals=(
            MemoryReviewProposal(
                operation=MemoryOperation.ADD,
                fact_type="pet.name",
                value="Rocky",
                evidence_quote="dog is Rocky",
                new_entity_label="Rocky",
            ),
        ),
        raw_responses=(),
        usage={},
        model_request_count=1,
        protocol_repaired=False,
    )

    prepared = MemoryReviewCoordinator(repository).prepare(
        subject_id="subject-a",
        current_user_message=user,
        decision=decision,
    )

    assert len(prepared.new_entities) == 1
    assert prepared.new_entities[0].kind is MemoryEntityKind.PET
    assert prepared.new_entities[0].label == "Rocky"
    assert prepared.proposals[0].entity_id == prepared.new_entities[0].id


def test_unbound_pet_attribute_does_not_create_a_duplicate_entity() -> None:
    repository = _repository()
    user = repository.append_message(
        conversation_id="conversation-a",
        role=MessageRole.USER,
        content="It is a Husky.",
        run_id="run",
    )
    decision = MemoryReviewDecision(
        reviewer_model_key="reviewer",
        proposals=(
            MemoryReviewProposal(
                operation=MemoryOperation.ADD,
                fact_type="pet.breed",
                value="Husky",
                evidence_quote="It is a Husky",
            ),
        ),
        raw_responses=(),
        usage={},
        model_request_count=1,
        protocol_repaired=False,
    )

    with pytest.raises(MemoryReviewError, match="existing:<id> or new:<local-ref>"):
        MemoryReviewCoordinator(repository).prepare(
            subject_id="subject-a",
            current_user_message=user,
            decision=decision,
        )


def test_review_output_cannot_choose_subject_key_or_entity_kind() -> None:
    for forbidden_field in (
        "subject_id",
        "key",
        "entity_id",
        "new_entity_kind",
        "new_entity_ref",
    ):
        payload = {
            "proposals": [
                {
                    "operation": "add",
                    "fact_type": "person.name",
                    "value": "Alice",
                    "evidence_quote": "Alice",
                    forbidden_field: "attacker-controlled",
                }
            ]
        }
        with pytest.raises(ReviewProtocolError, match="Unexpected"):
            parse_review_payload(payload, reviewer_model_key="reviewer")


def test_review_cannot_reference_an_entity_from_another_subject() -> None:
    repository = _repository()
    foreign = repository.create_memory_entity(
        subject_id="subject-b",
        kind=MemoryEntityKind.PET,
        label="Mallory's pet",
    )
    user = repository.append_message(
        conversation_id="conversation-a",
        role=MessageRole.USER,
        content="My dog is Rocky.",
        run_id="run",
    )
    decision = MemoryReviewDecision(
        reviewer_model_key="reviewer",
        proposals=(
            MemoryReviewProposal(
                operation=MemoryOperation.ADD,
                fact_type="pet.name",
                value="Rocky",
                evidence_quote="dog is Rocky",
                entity_ref=f"existing:{foreign.id}",
            ),
        ),
        raw_responses=(),
        usage={},
        model_request_count=1,
        protocol_repaired=False,
    )
    with pytest.raises(MemoryReviewError, match="bound subject"):
        MemoryReviewCoordinator(repository).prepare(
            subject_id="subject-a",
            current_user_message=user,
            decision=decision,
        )


def test_review_evidence_must_be_an_exact_current_turn_excerpt() -> None:
    repository = _repository()
    repository.append_message(
        conversation_id="conversation-a",
        role=MessageRole.USER,
        content="My name is Alice.",
        run_id="prior",
    )
    current = repository.append_message(
        conversation_id="conversation-a",
        role=MessageRole.USER,
        content="How are you?",
        run_id="run",
    )
    decision = MemoryReviewDecision(
        reviewer_model_key="reviewer",
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
    with pytest.raises(MemoryReviewError, match="current user message"):
        MemoryReviewCoordinator(repository).prepare(
            subject_id="subject-a",
            current_user_message=current,
            decision=decision,
        )


class _ScriptedReviewTransport:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, object]] = []

    async def complete(
        self, payload: dict[str, object], *, timeout_seconds: float
    ) -> dict[str, object]:
        self.requests.append(payload)
        return self.responses.pop(0)


def _completion(content: str) -> dict[str, object]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4},
    }


def test_router_reviewer_uses_one_explicit_schema_repair() -> None:
    async def scenario() -> None:
        transport = _ScriptedReviewTransport(
            [
                _completion("not-json"),
                _completion(
                    '{"proposals":[{"operation":"add",'
                    '"fact_type":"person.name","value":"Alice",'
                    '"evidence_quote":"name is Alice"}]}'
                ),
            ]
        )
        reviewer = RouterMemoryReviewer(
            model_key="dgx_vllm::reviewer",
            transport=transport,
        )
        repository = _repository()
        prior_user = repository.append_message(
            conversation_id="conversation-a",
            role=MessageRole.USER,
            content="I have a dog.",
            run_id="prior",
        )
        prior_assistant = repository.append_message(
            conversation_id="conversation-a",
            role=MessageRole.ASSISTANT,
            content="I am Lin Xiaotang.",
            run_id="prior",
        )
        current = repository.append_message(
            conversation_id="conversation-a",
            role=MessageRole.USER,
            content="My name is Alice",
            run_id="run",
        )
        decision = await reviewer.review(
            MemoryReviewRequest(
                current_user_message=current,
                recent_user_messages=(prior_user, prior_assistant),
                active_facts=(),
                entities=repository.list_subject_entities("subject-a"),
                timeout_seconds=2,
            )
        )

        assert decision.protocol_repaired is True
        assert decision.model_request_count == 2
        assert len(decision.proposals) == 1
        assert len(transport.requests) == 2
        for payload in transport.requests:
            assert payload["temperature"] == 0
            assert payload["chat_template_kwargs"] == {"enable_thinking": False}
            reviewer_input = payload["messages"][1]["content"]
            assert "subject-a" not in reviewer_input
            assert "non_subject_entities" in reviewer_input
            assert "I have a dog." in reviewer_input
            assert "I am Lin Xiaotang." not in reviewer_input

    asyncio.run(scenario())


@dataclass
class _ReplyExecutor:
    request_count: int = 0

    name = "reply"

    async def execute(self, request: ExecutorRequest) -> ExecutorResult:
        self.request_count += 1
        assert all(tool.name != "propose_memory_change" for tool in request.tools)
        return ExecutorResult(
            assistant_text="Hi Alice",
            reasoning=(),
            events=(
                (RunEventType.MODEL_REQUEST, {"model_request_index": 1}),
                (RunEventType.MODEL_RESPONSE, {"model_request_index": 1}),
            ),
            raw_messages=(),
            usage={},
            model_request_count=1,
        )


class _StaticReviewer:
    model_key = "reviewer"

    async def review(self, request: MemoryReviewRequest) -> MemoryReviewDecision:
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


class _FailingReviewer:
    model_key = "reviewer"

    async def review(self, request: MemoryReviewRequest) -> MemoryReviewDecision:
        raise ReviewProtocolError("review schema remained invalid after repair")


def test_runtime_commits_reviewed_memory_without_a_conversation_write_tool() -> None:
    async def scenario() -> None:
        repository = _repository()
        runtime = StudyAgentRuntime(
            repository=repository,
            executor=_ReplyExecutor(),
            memory_reviewer=_StaticReviewer(),
        )
        result = await runtime.run_turn(
            TurnRequest(
                conversation_id="conversation-a",
                user_content="My name is Alice",
                idempotency_key="reviewed",
                policy=RuntimePolicy(timeout_seconds=2),
            )
        )

        assert result.run.status is RunStatus.SUCCEEDED
        assert result.assistant_message is not None
        assert len(result.memory_revisions) == 1
        fact = repository.list_subject_facts("subject-a", active_only=True)[0]
        assert fact.fact_type == "person.name"
        assert fact.entity_id == "subject-a"
        assert any(
            event.type is RunEventType.MEMORY_REVIEWED for event in result.events
        )

    asyncio.run(scenario())


def test_reviewer_failure_commits_neither_assistant_nor_memory() -> None:
    async def scenario() -> None:
        repository = _repository()
        runtime = StudyAgentRuntime(
            repository=repository,
            executor=_ReplyExecutor(),
            memory_reviewer=_FailingReviewer(),
        )
        result = await runtime.run_turn(
            TurnRequest(
                conversation_id="conversation-a",
                user_content="My name is Alice",
                idempotency_key="review-failed",
                policy=RuntimePolicy(timeout_seconds=2),
            )
        )

        assert result.run.status is RunStatus.FAILED
        assert result.assistant_message is None
        assert result.candidate_assistant_text == "Hi Alice"
        assert result.memory_revisions == ()
        assert repository.list_subject_facts("subject-a", active_only=False) == ()
        assert [
            message.role for message in repository.list_messages("conversation-a")
        ] == [MessageRole.USER]
        case = StudyCase(
            key="review-failure",
            description="role attribution",
            agent_keys=("primary",),
            subject_keys=("primary",),
            conversations={"primary": ("primary", "primary")},
            initial_facts=(),
            prelude_messages=(),
            turns=(FixtureTurn(conversation_key="primary", user="My name is Alice"),),
            fact_assertions=(),
            assistant_assertions=(
                AssistantAssertion(
                    conversation_key="primary",
                    contains_any=("Hi Alice",),
                ),
            ),
            enabled_tools=(),
            expected_tool_observations=(),
            require_failed_tool_result=False,
            profile_token_override=None,
        )
        score = score_case(
            case=case,
            facts_by_subject={"primary": ()},
            results_by_conversation={"primary": (normalize_turn(result),)},
        )
        assert score["role_scores"]["conversation"]["pass"] is True
        assert score["role_scores"]["reviewer"]["pass"] is False

    asyncio.run(scenario())
