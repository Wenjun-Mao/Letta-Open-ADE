from __future__ import annotations

import asyncio

import pytest

from workflows.evals.agent_runtime_study.contracts import (
    AgentDefinition,
    Conversation,
    MemoryFactStatus,
    MemoryOperation,
    MemoryProposal,
    MemorySubject,
    MessageRole,
)
from workflows.evals.agent_runtime_study.memory import (
    MemoryPolicy,
    MemoryProposalError,
    MemoryRetriever,
)
from workflows.evals.agent_runtime_study.repository import (
    InMemoryStudyRepository,
    OptimisticConflictError,
)
from workflows.evals.agent_runtime_study.tools import TurnToolSession


def _repository() -> InMemoryStudyRepository:
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
    for subject_id in ("subject-a", "subject-b"):
        repository.add_subject(MemorySubject(id=subject_id, external_key=subject_id))
    repository.add_conversation(
        Conversation(
            id="conversation",
            agent_definition_id="agent",
            memory_subject_id="subject-a",
        )
    )
    repository.add_conversation(
        Conversation(
            id="conversation-b",
            agent_definition_id="agent",
            memory_subject_id="subject-b",
        )
    )
    return repository


def _source(repository: InMemoryStudyRepository, content: str):
    return repository.append_message(
        conversation_id="conversation",
        role=MessageRole.USER,
        content=content,
        run_id="run",
    )


def test_add_correct_and_forget_keep_auditable_revisions() -> None:
    repository = _repository()
    policy = MemoryPolicy(repository)
    source = _source(repository, "I live in Beijing")
    added = policy.apply_batch(
        subject_id="subject-a",
        proposals=(
            MemoryProposal(
                operation=MemoryOperation.ADD,
                key="home_city",
                value="Beijing",
                evidence_quote="live in Beijing",
            ),
        ),
        source_messages=(source,),
        run_id="run-add",
    )[0]
    fact = repository.get_fact(added.fact_id)
    correction_source = _source(repository, "Correction: I now live in Toronto")
    corrected = policy.apply_batch(
        subject_id="subject-a",
        proposals=(
            MemoryProposal(
                operation=MemoryOperation.CORRECT,
                fact_id=fact.id,
                expected_version=1,
                key="home_city",
                value="Toronto",
                evidence_quote="I now live in Toronto",
            ),
        ),
        source_messages=(correction_source,),
        run_id="run-correct",
    )[0]
    corrected_fact = repository.get_fact(fact.id)
    assert corrected_fact.value == "Toronto"
    assert corrected_fact.version == 2
    assert corrected.prior_revision_ids == (added.id,)

    forget_source = _source(repository, "Please forget where I live")
    forgotten = policy.apply_batch(
        subject_id="subject-a",
        proposals=(
            MemoryProposal(
                operation=MemoryOperation.FORGET,
                fact_id=fact.id,
                expected_version=2,
                key="home_city",
                value=None,
                evidence_quote="forget where I live",
            ),
        ),
        source_messages=(forget_source,),
        run_id="run-forget",
    )[0]
    tombstone = repository.get_fact(fact.id)
    assert tombstone.status is MemoryFactStatus.FORGOTTEN
    assert tombstone.version == 3
    assert forgotten.prior_revision_ids == (added.id, corrected.id)
    assert repository.list_subject_facts("subject-a", active_only=True) == ()
    assert len(repository.revisions[fact.id]) == 3


def test_merge_supersedes_sources_and_creates_one_active_projection() -> None:
    repository = _repository()
    policy = MemoryPolicy(repository)
    source = _source(repository, "My dog is Rocky and Rocky is a Husky")
    revisions = policy.apply_batch(
        subject_id="subject-a",
        proposals=(
            MemoryProposal(
                operation=MemoryOperation.ADD,
                key="dog_name",
                value="Rocky",
                evidence_quote="dog is Rocky",
            ),
            MemoryProposal(
                operation=MemoryOperation.ADD,
                key="dog_breed",
                value="Husky",
                evidence_quote="Rocky is a Husky",
            ),
        ),
        source_messages=(source,),
        run_id="run-add",
    )
    merge_source = _source(repository, "Keep Rocky the Husky as one pet profile")
    merged = policy.apply_batch(
        subject_id="subject-a",
        proposals=(
            MemoryProposal(
                operation=MemoryOperation.MERGE,
                key="pet_profile",
                value="Rocky is a Husky",
                evidence_quote="Rocky the Husky",
                target_fact_ids=tuple(revision.fact_id for revision in revisions),
                expected_versions={revision.fact_id: 1 for revision in revisions},
            ),
        ),
        source_messages=(merge_source,),
        run_id="run-merge",
    )[0]
    active = repository.list_subject_facts("subject-a", active_only=True)
    assert len(active) == 1
    assert active[0].id == merged.fact_id
    assert all(
        repository.get_fact(revision.fact_id).status is MemoryFactStatus.SUPERSEDED
        for revision in revisions
    )


def test_evidence_uncertainty_subject_and_version_are_validated() -> None:
    repository = _repository()
    policy = MemoryPolicy(repository)
    source = _source(repository, "Maybe I will get a cat named Milo")
    with pytest.raises(MemoryProposalError, match="uncertain"):
        policy.apply_batch(
            subject_id="subject-a",
            proposals=(
                MemoryProposal(
                    operation=MemoryOperation.ADD,
                    key="cat_name",
                    value="Milo",
                    evidence_quote="Maybe I will get a cat named Milo",
                ),
            ),
            source_messages=(source,),
            run_id="run",
        )
    with pytest.raises(MemoryProposalError, match="exact excerpt"):
        policy.apply_batch(
            subject_id="subject-a",
            proposals=(
                MemoryProposal(
                    operation=MemoryOperation.ADD,
                    key="name",
                    value="Alice",
                    evidence_quote="I am Alice",
                ),
            ),
            source_messages=(source,),
            run_id="run",
        )

    wrong_subject_source = repository.append_message(
        conversation_id="conversation-b",
        role=MessageRole.USER,
        content="My name is Mallory",
        run_id="run",
    )
    with pytest.raises(MemoryProposalError, match="bound to the subject"):
        policy.apply_batch(
            subject_id="subject-a",
            proposals=(
                MemoryProposal(
                    operation=MemoryOperation.ADD,
                    key="name",
                    value="Mallory",
                    evidence_quote="name is Mallory",
                ),
            ),
            source_messages=(wrong_subject_source,),
            run_id="run",
        )

    unsupported = _source(repository, "My name is Bob")
    with pytest.raises(MemoryProposalError, match="not supported"):
        policy.apply_batch(
            subject_id="subject-a",
            proposals=(
                MemoryProposal(
                    operation=MemoryOperation.ADD,
                    key="name",
                    value="Alice",
                    evidence_quote="My name is Bob",
                ),
            ),
            source_messages=(unsupported,),
            run_id="run",
        )

    explicit = _source(repository, "My name is Alice")
    revision = policy.apply_batch(
        subject_id="subject-a",
        proposals=(
            MemoryProposal(
                operation=MemoryOperation.ADD,
                key="name",
                value="Alice",
                evidence_quote="name is Alice",
            ),
        ),
        source_messages=(explicit,),
        run_id="run",
    )[0]
    assert revision.evidence_spans[0].message_id == explicit.id
    assert revision.evidence_spans[0].quote == "name is Alice"
    assert len(revision.evidence_spans[0].message_sha256) == 64
    correction = repository.append_message(
        conversation_id="conversation-b",
        role=MessageRole.USER,
        content="My name is Alicia",
        run_id="run",
    )
    with pytest.raises(MemoryProposalError, match="bound subject"):
        policy.apply_batch(
            subject_id="subject-b",
            proposals=(
                MemoryProposal(
                    operation=MemoryOperation.CORRECT,
                    fact_id=revision.fact_id,
                    expected_version=1,
                    key="name",
                    value="Alicia",
                    evidence_quote="name is Alicia",
                ),
            ),
            source_messages=(correction,),
            run_id="run",
        )
    version_correction = _source(repository, "My name is Alicia")
    with pytest.raises(OptimisticConflictError):
        policy.apply_batch(
            subject_id="subject-a",
            proposals=(
                MemoryProposal(
                    operation=MemoryOperation.CORRECT,
                    fact_id=revision.fact_id,
                    expected_version=99,
                    key="name",
                    value="Alicia",
                    evidence_quote="name is Alicia",
                ),
            ),
            source_messages=(version_correction,),
            run_id="run",
        )


def test_repository_transaction_rolls_back_partial_memory_batch() -> None:
    repository = _repository()
    policy = MemoryPolicy(repository)
    source = _source(repository, "My name is Alice and I repeat Alice")
    proposals = (
        MemoryProposal(
            operation=MemoryOperation.ADD,
            key="name",
            value="Alice",
            evidence_quote="name is Alice",
        ),
        MemoryProposal(
            operation=MemoryOperation.ADD,
            key="name",
            value="Alice",
            evidence_quote="repeat Alice",
        ),
    )
    with pytest.raises(MemoryProposalError), repository.transaction():
        policy.apply_batch(
            subject_id="subject-a",
            proposals=proposals,
            source_messages=(source,),
            run_id="run",
        )
    assert repository.list_subject_facts("subject-a") == ()


def test_duplicate_staged_key_is_reported_before_model_loop_finishes() -> None:
    async def scenario() -> None:
        repository = _repository()
        source = _source(repository, "My name is Alice")
        session = TurnToolSession(
            subject_id="subject-a",
            conversation_id="conversation",
            source_messages=(source,),
            memory_policy=MemoryPolicy(repository),
            memory_retriever=MemoryRetriever(repository),
            search_limit=8,
            include_episodes=False,
        )
        arguments = {
            "operation": "add",
            "key": "name",
            "value": "Alice",
            "evidence_quote": "name is Alice",
        }

        first = await session.execute("propose_memory_change", arguments, "call-1")
        duplicate = await session.execute("propose_memory_change", arguments, "call-2")

        assert first["ok"] is True
        assert duplicate["ok"] is False
        assert "already uses key" in duplicate["error"]
        assert len(session.pending_proposals) == 1

    asyncio.run(scenario())


def test_batch_rejects_multiple_mutations_of_one_fact() -> None:
    repository = _repository()
    policy = MemoryPolicy(repository)
    source = _source(repository, "My name is Alice")
    revision = policy.apply_batch(
        subject_id="subject-a",
        proposals=(
            MemoryProposal(
                operation=MemoryOperation.ADD,
                key="name",
                value="Alice",
                evidence_quote="name is Alice",
            ),
        ),
        source_messages=(source,),
        run_id="run-add",
    )[0]
    correction = _source(repository, "Call me Alicia or Ally")

    with pytest.raises(MemoryProposalError, match="only once"):
        policy.validate_batch(
            subject_id="subject-a",
            proposals=(
                MemoryProposal(
                    operation=MemoryOperation.CORRECT,
                    fact_id=revision.fact_id,
                    expected_version=1,
                    key="name",
                    value="Alicia",
                    evidence_quote="Alicia",
                ),
                MemoryProposal(
                    operation=MemoryOperation.CORRECT,
                    fact_id=revision.fact_id,
                    expected_version=1,
                    key="name",
                    value="Ally",
                    evidence_quote="Ally",
                ),
            ),
            source_messages=(correction,),
        )
