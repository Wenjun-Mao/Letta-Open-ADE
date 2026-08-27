from __future__ import annotations

from dataclasses import dataclass

from .contracts import (
    AgentDefinition,
    Conversation,
    MemoryOperation,
    MemoryProposal,
    MemorySubject,
    MessageRole,
)
from .fixtures import StudyCase
from .memory import MemoryPolicy
from .product_material import CHAT_PERSONA, CHAT_SYSTEM_PROMPT
from .repository import InMemoryStudyRepository
from .tools import CURATED_TOOL_DEFINITIONS


@dataclass(frozen=True)
class CaseWorld:
    repository: InMemoryStudyRepository
    agent_ids: dict[str, str]
    subject_ids: dict[str, str]
    conversation_ids: dict[str, str]


def build_case_world(case: StudyCase, *, model_key: str) -> CaseWorld:
    repository = InMemoryStudyRepository()
    agent_ids: dict[str, str] = {}
    subject_ids: dict[str, str] = {}
    conversation_ids: dict[str, str] = {}
    tool_names = tuple(definition.name for definition in CURATED_TOOL_DEFINITIONS)

    for key in case.agent_keys:
        agent_id = f"agent_{case.key}_{key}"
        repository.add_agent_definition(
            AgentDefinition(
                id=agent_id,
                name=f"{case.key}:{key}",
                model_key=model_key,
                system_prompt=CHAT_SYSTEM_PROMPT,
                persona=(
                    CHAT_PERSONA
                    if key == "companion"
                    else f"{CHAT_PERSONA}\n\nPersona study variant: {key}."
                ),
                tool_names=tool_names,
            )
        )
        agent_ids[key] = agent_id
    for key in case.subject_keys:
        subject_id = f"subject_{case.key}_{key}"
        repository.add_subject(
            MemorySubject(id=subject_id, external_key=key, display_name=key)
        )
        subject_ids[key] = subject_id
    for key, (agent_key, subject_key) in case.conversations.items():
        conversation_id = f"conversation_{case.key}_{key}"
        repository.add_conversation(
            Conversation(
                id=conversation_id,
                agent_definition_id=agent_ids[agent_key],
                memory_subject_id=subject_ids[subject_key],
            )
        )
        conversation_ids[key] = conversation_id

    _seed_facts(case, repository, subject_ids, conversation_ids)
    _seed_prelude(case, repository, conversation_ids)
    return CaseWorld(
        repository=repository,
        agent_ids=agent_ids,
        subject_ids=subject_ids,
        conversation_ids=conversation_ids,
    )


def _seed_facts(
    case: StudyCase,
    repository: InMemoryStudyRepository,
    subject_ids: dict[str, str],
    conversation_ids: dict[str, str],
) -> None:
    policy = MemoryPolicy(repository)
    for index, initial in enumerate(case.initial_facts, 1):
        subject_id = subject_ids[initial.subject_key]
        bound_conversation_id = next(
            value
            for key, value in conversation_ids.items()
            if case.conversations[key][1] == initial.subject_key
        )
        bound_conversation = repository.get_conversation(bound_conversation_id)
        conversation_id = f"fixture_seed_{case.key}_{initial.subject_key}"
        if conversation_id not in repository.conversations:
            repository.add_conversation(
                Conversation(
                    id=conversation_id,
                    agent_definition_id=bound_conversation.agent_definition_id,
                    memory_subject_id=subject_id,
                )
            )
        source = repository.append_message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=f"{initial.key}: {initial.value}",
            run_id="fixture_seed",
        )
        proposal = MemoryProposal(
            operation=MemoryOperation.ADD,
            key=initial.key,
            value=initial.value,
            evidence_quote=initial.value,
        )
        with repository.transaction():
            policy.apply_batch(
                subject_id=subject_id,
                proposals=(proposal,),
                source_messages=(source,),
                run_id=f"fixture_seed_{index}",
            )


def _seed_prelude(
    case: StudyCase,
    repository: InMemoryStudyRepository,
    conversation_ids: dict[str, str],
) -> None:
    for prelude in case.prelude_messages:
        conversation_id = conversation_ids[prelude.conversation_key]
        for index in range(1, prelude.count + 1):
            repository.append_message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=prelude.user_template.format(index=index),
                run_id="fixture_prelude",
            )
            repository.append_message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=prelude.assistant_template.format(index=index),
                run_id="fixture_prelude",
            )
        if prelude.summary:
            messages = repository.list_messages(conversation_id)
            through = min(prelude.summary_through_sequence, len(messages))
            source_ids = tuple(
                message.id for message in messages if message.sequence <= through
            )
            repository.put_summary(
                conversation_id=conversation_id,
                through_sequence=through,
                content=prelude.summary,
                source_message_ids=source_ids,
                expected_version=0,
            )
