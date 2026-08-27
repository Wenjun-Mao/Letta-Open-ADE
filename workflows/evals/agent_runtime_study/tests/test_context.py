from __future__ import annotations

from workflows.evals.agent_runtime_study.context import ContextBuilder
from workflows.evals.agent_runtime_study.contracts import (
    AgentDefinition,
    ContextBudget,
    Conversation,
    MemoryOperation,
    MemoryProposal,
    MemorySubject,
    MessageRole,
)
from workflows.evals.agent_runtime_study.memory import MemoryPolicy, MemoryRetriever
from workflows.evals.agent_runtime_study.repository import InMemoryStudyRepository


def _context_repository() -> InMemoryStudyRepository:
    repository = InMemoryStudyRepository()
    repository.add_agent_definition(
        AgentDefinition(
            id="agent",
            name="agent",
            model_key="model",
            system_prompt="System prompt",
            persona="Persona",
            tool_names=(),
        )
    )
    for subject in ("subject-a", "subject-b"):
        repository.add_subject(MemorySubject(id=subject, external_key=subject))
    repository.add_conversation(
        Conversation(
            id="conversation-a",
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


def _add_fact(repository, subject_id, conversation_id, key, value):
    message = repository.append_message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=value,
        run_id="seed",
    )
    MemoryPolicy(repository).apply_batch(
        subject_id=subject_id,
        proposals=(
            MemoryProposal(
                operation=MemoryOperation.ADD,
                key=key,
                value=value,
                evidence_quote=value,
            ),
        ),
        source_messages=(message,),
        run_id="seed",
    )


def test_context_order_budget_summary_and_raw_history_contract() -> None:
    repository = _context_repository()
    _add_fact(repository, "subject-a", "conversation-a", "dog", "Rocky is a Husky")
    for index in range(20):
        repository.append_message(
            conversation_id="conversation-a",
            role=MessageRole.USER,
            content=f"old user message {index} " + "x" * 120,
            run_id="history",
        )
        repository.append_message(
            conversation_id="conversation-a",
            role=MessageRole.ASSISTANT,
            content=f"old assistant message {index} " + "y" * 120,
            run_id="history",
        )
    raw_before = repository.list_messages("conversation-a")
    repository.put_summary(
        conversation_id="conversation-a",
        through_sequence=30,
        content="Earlier turns were routine; Rocky is the user's Husky.",
        source_message_ids=tuple(message.id for message in raw_before[:30]),
        expected_version=0,
    )
    current = repository.append_message(
        conversation_id="conversation-a",
        role=MessageRole.USER,
        content="What breed is Rocky?",
        run_id="current",
    )
    budget = ContextBudget(
        total_tokens=900,
        response_reserve_tokens=150,
        agent_tokens=180,
        profile_tokens=100,
        summary_tokens=120,
        retrieved_tokens=100,
        recent_message_tokens=180,
    )
    context = ContextBuilder(repository, MemoryRetriever(repository)).build(
        conversation_id="conversation-a",
        current_user_message=current,
        budget=budget,
        search_limit=4,
        include_episodes=False,
    )
    assert [section.name for section in context.sections] == [
        "agent_prompt_and_persona",
        "active_subject_profile",
        "conversation_summary",
        "automatically_retrieved_memory",
        "recent_raw_messages",
    ]
    assert context.estimated_input_tokens <= 750
    assert "Rocky" in context.system_prompt
    assert context.omitted_message_ids
    assert repository.list_messages("conversation-a") == raw_before + (current,)


def test_context_never_projects_another_subject_memory() -> None:
    repository = _context_repository()
    _add_fact(repository, "subject-a", "conversation-a", "secret", "ALICE-SECRET")
    current = repository.append_message(
        conversation_id="conversation-b",
        role=MessageRole.USER,
        content="What do you know about me?",
        run_id="current",
    )
    context = ContextBuilder(repository, MemoryRetriever(repository)).build(
        conversation_id="conversation-b",
        current_user_message=current,
        budget=ContextBudget(),
        search_limit=8,
        include_episodes=True,
    )
    assert "ALICE-SECRET" not in context.system_prompt
    assert context.retrieved_fact_ids == ()


def test_summary_versions_are_optimistic_and_replaceable() -> None:
    repository = _context_repository()
    first = repository.put_summary(
        conversation_id="conversation-a",
        through_sequence=0,
        content="v1",
        source_message_ids=(),
        expected_version=0,
    )
    second = repository.put_summary(
        conversation_id="conversation-a",
        through_sequence=0,
        content="v2",
        source_message_ids=(),
        expected_version=1,
    )
    assert first.version == 1
    assert second.version == 2
    assert repository.get_summary("conversation-a") == second
    assert repository.list_summary_versions("conversation-a") == (first, second)
