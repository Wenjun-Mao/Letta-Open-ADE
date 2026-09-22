"""Case-specific scripted writes for the M2 ADE PostgreSQL dialogue slice."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncConnection

from ade_api.features.agent_runtime.contracts import MemoryOperation
from ade_api.features.agent_runtime.memory_commit import commit_memory_review
from ade_api.features.agent_runtime.memory_policy import prepare_memory_review
from ade_api.features.agent_runtime.memory_review import (
    AddProposal,
    CorrectProposal,
    ForgetProposal,
    ReviewDecision,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definition_versions,
    agent_definitions,
    conversations,
    memory_entities,
    memory_subjects,
    messages,
    runs,
    workspaces,
)
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository


@dataclass(frozen=True)
class CaseResources:
    workspace_id: str
    subject_ids: dict[str, str]
    conversation_ids: dict[str, str]


@dataclass(frozen=True)
class ScriptedAction:
    key: str
    operation: MemoryOperation
    subject_key: str
    conversation_key: str
    sequence: int
    source_text: str
    evidence_quote: str
    value: str | None = None
    qualifier: str | None = None
    predecessor_key: str | None = None


async def create_case_resources(connection: AsyncConnection) -> CaseResources:
    """Create fresh synthetic runtime ownership resources; never reuse test data."""

    ids = {
        name: str(uuid4())
        for name in (
            "workspace",
            "definition",
            "definition_version",
            "subject_one",
            "subject_two",
            "conversation_one",
            "conversation_two",
            "conversation_other_subject",
        )
    }
    suffix = ids["workspace"].replace("-", "")[:16]
    definition_key = f"m2-pg-luna-{suffix}"
    await connection.execute(
        insert(workspaces).values(
            id=ids["workspace"],
            workspace_key=f"m2-pg-luna-{suffix}",
            name="M2 PostgreSQL Luna synthetic case",
        )
    )
    await connection.execute(
        insert(agent_definitions).values(
            id=ids["definition"],
            workspace_id=ids["workspace"],
            definition_key=definition_key,
            name="M2 PostgreSQL Luna synthetic case",
        )
    )
    await connection.execute(
        insert(agent_definition_versions).values(
            id=ids["definition_version"],
            workspace_id=ids["workspace"],
            agent_definition_id=ids["definition"],
            definition_key=definition_key,
            version=1,
            name="M2 PostgreSQL Luna synthetic case",
            model_key="development::scripted",
            reviewer_model_key="development::scripted",
            embedding_model_key="development::none",
            prompt_key="m2-postgres-luna-scripted",
            prompt_sha256="0" * 64,
            prompt_content="",
            persona_key="chat_linxiaotang",
            persona_sha256="1" * 64,
            persona_content="",
            tool_names=[],
            memory_policy_version="m2-postgres-luna-scripted-v1",
            qualification_state="unqualified",
            deployment_snapshot=[],
        )
    )
    await connection.execute(
        update(agent_definitions)
        .where(agent_definitions.c.id == ids["definition"])
        .values(current_version_id=ids["definition_version"])
    )
    await connection.execute(
        insert(memory_subjects),
        [
            {
                "id": ids[key],
                "workspace_id": ids["workspace"],
                "external_key": f"{key}-{suffix}",
                "display_name": label,
            }
            for key, label in (
                ("subject_one", "Synthetic Subject One"),
                ("subject_two", "Synthetic Subject Two"),
            )
        ],
    )
    await connection.execute(
        insert(memory_entities),
        [
            {
                "id": ids[key],
                "workspace_id": ids["workspace"],
                "subject_id": ids[key],
                "kind": "subject",
                "label": label,
            }
            for key, label in (
                ("subject_one", "Synthetic Subject One"),
                ("subject_two", "Synthetic Subject Two"),
            )
        ],
    )
    await connection.execute(
        insert(conversations),
        [
            {
                "id": ids[key],
                "workspace_id": ids["workspace"],
                "agent_definition_version_id": ids["definition_version"],
                "memory_subject_id": ids[subject_key],
                "title": title,
            }
            for key, subject_key, title in (
                ("conversation_one", "subject_one", "Subject One Conversation 1"),
                ("conversation_two", "subject_one", "Subject One Conversation 2"),
                (
                    "conversation_other_subject",
                    "subject_two",
                    "Subject Two Conversation 1",
                ),
            )
        ],
    )
    return CaseResources(
        workspace_id=ids["workspace"],
        subject_ids={
            "subject_one": ids["subject_one"],
            "subject_two": ids["subject_two"],
        },
        conversation_ids={
            key: ids[key]
            for key in (
                "conversation_one",
                "conversation_two",
                "conversation_other_subject",
            )
        },
    )


async def commit_scripted_action(
    connection: AsyncConnection,
    *,
    resources: CaseResources,
    action: ScriptedAction,
    committed: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Pass a deterministic typed proposal through ADE validation and commit."""

    workspace_id = resources.workspace_id
    subject_id = resources.subject_ids[action.subject_key]
    conversation_id = resources.conversation_ids[action.conversation_key]
    run_id, message_id = str(uuid4()), str(uuid4())
    await connection.execute(
        insert(runs).values(
            id=run_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            idempotency_key=f"m2-scripted-{run_id}",
            request_hash=hashlib.sha256(
                f"{action.key}:{action.source_text}".encode()
            ).hexdigest(),
            status="succeeded",
            qualification_state="unqualified",
            accepted_runtime_mode="development",
            timeout_seconds=180,
            retry_count=0,
            accepted_conversation_version=1,
            attempt_count=1,
        )
    )
    await connection.execute(
        insert(messages).values(
            id=message_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            sequence=action.sequence,
            role="user",
            content=action.source_text,
            content_sha256=hashlib.sha256(action.source_text.encode()).hexdigest(),
            run_id=run_id,
        )
    )
    source_message = {
        "id": message_id,
        "run_id": run_id,
        "content": action.source_text,
    }
    repository = MemoryRepository(connection)
    active_facts = await repository.list_active_facts(subject_id)
    if action.operation is MemoryOperation.ADD:
        proposal = AddProposal(
            operation=action.operation,
            fact_type="person.preference",
            qualifier=action.qualifier,
            value=action.value or "",
            evidence_quote=action.evidence_quote,
        )
    elif action.operation is MemoryOperation.CORRECT:
        predecessor = committed[action.predecessor_key or ""]
        fact = next(
            fact for fact in active_facts if fact["id"] == predecessor["fact_id"]
        )
        proposal = CorrectProposal(
            operation=action.operation,
            fact_id=predecessor["fact_id"],
            expected_version=int(fact["version"]),
            value=action.value or "",
            evidence_quote=action.evidence_quote,
        )
    else:
        predecessor = committed[action.predecessor_key or ""]
        fact = next(
            fact for fact in active_facts if fact["id"] == predecessor["fact_id"]
        )
        proposal = ForgetProposal(
            operation=action.operation,
            fact_id=predecessor["fact_id"],
            expected_version=int(fact["version"]),
            value=None,
            evidence_quote=action.evidence_quote,
        )
    decision = ReviewDecision(proposals=[proposal])
    prepared = prepare_memory_review(
        decision=decision,
        subject_id=subject_id,
        current_user_message=source_message,
        active_facts=active_facts,
        entities=[
            {
                "id": subject_id,
                "subject_id": subject_id,
                "kind": "subject",
                "label": "Synthetic subject",
            }
        ],
    )
    results = await commit_memory_review(
        connection,
        workspace_id=workspace_id,
        subject_id=subject_id,
        run_id=run_id,
        review=prepared,
        operation_embeddings=(None,),
        embedding_fingerprint="scripted-no-embedding",
        embedding_dimensions=0,
        retrieval_policy_version="m2-postgres-luna-scripted-v1",
    )
    result = results[0]
    return {
        **result,
        "source_message_id": message_id,
        "source_quote": action.evidence_quote,
        "source_text": action.source_text,
        "subject_id": subject_id,
        "conversation_id": conversation_id,
        "run_id": run_id,
    }
