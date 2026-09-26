"""Disposable PostgreSQL seed helpers for the historical reader tests."""

from __future__ import annotations

import hashlib
import re
from uuid import uuid4

from sqlalchemy import insert, update
from sqlalchemy.engine import make_url

from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definition_versions,
    conversations,
    memory_actions,
    memory_facts,
    memory_revision_predecessors,
    memory_revision_sources,
    memory_revisions,
    messages,
    runs,
)


def require_disposable_database_url(database_url: str) -> None:
    url = make_url(database_url)
    assert (
        url.drivername == "postgresql+psycopg"
        and url.host in {"localhost", "127.0.0.1", "::1"}
        and url.username == "ade_owner"
        and url.password is None
        and url.database is not None
        and re.fullmatch(r"ade_history_test_[0-9a-f]{8,}", url.database)
    ), (
        "history tests require a disposable passwordless loopback ade_history_test_<hex> database"
    )


async def turn(
    connection,
    workspace_id,
    conversation_id,
    user_text,
    *,
    status="succeeded",
    sequence=1,
):
    run_id, user_id = str(uuid4()), str(uuid4())
    await connection.execute(
        insert(runs).values(
            id=run_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            idempotency_key=run_id,
            request_hash="a" * 64,
            status=status,
            qualification_state="unqualified",
            timeout_seconds=180,
            retry_count=0,
            accepted_conversation_version=1,
        )
    )
    await connection.execute(
        insert(messages).values(
            id=user_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            sequence=sequence,
            role="user",
            content=user_text,
            content_sha256=hashlib.sha256(user_text.encode()).hexdigest(),
            run_id=run_id,
        )
    )
    return {"run_id": run_id, "user_id": user_id, "sequence": sequence}


async def assistant(
    connection, workspace_id, conversation_id, turn, text="Understood."
):
    message_id = str(uuid4())
    await connection.execute(
        insert(messages).values(
            id=message_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            sequence=turn["sequence"] + 1,
            role="assistant",
            content=text,
            content_sha256=hashlib.sha256(text.encode()).hexdigest(),
            run_id=turn["run_id"],
        )
    )
    return message_id


async def version(connection, ids, *, root_id, version, purpose="development"):
    version_id = str(uuid4())
    await connection.execute(
        insert(agent_definition_versions).values(
            id=version_id,
            workspace_id=ids["workspace"],
            agent_definition_id=root_id,
            definition_key=f"history-{root_id[:8]}",
            version=version,
            name="History test",
            model_key="synthetic::chat",
            reviewer_model_key="synthetic::reviewer",
            embedding_model_key="synthetic::embedding",
            prompt_key="synthetic",
            prompt_sha256="0" * 64,
            prompt_content="",
            persona_key="synthetic",
            persona_sha256="1" * 64,
            persona_content="",
            tool_names=[],
            memory_policy_version="old-readable-policy",
            qualification_state="unqualified",
            deployment_snapshot=[],
            purpose=purpose,
        )
    )
    return version_id


async def conversation(
    connection, ids, *, version_id, subject_id, purpose="development", archived=False
):
    conversation_id = str(uuid4())
    await connection.execute(
        insert(conversations).values(
            id=conversation_id,
            workspace_id=ids["workspace"],
            agent_definition_version_id=version_id,
            memory_subject_id=subject_id,
            purpose=purpose,
            archived_at="2026-01-01T00:00:00Z" if archived else None,
        )
    )
    return conversation_id


async def action(connection, ids):
    action_id = str(uuid4())
    await connection.execute(
        insert(memory_actions).values(
            id=action_id,
            workspace_id=ids["workspace"],
            subject_id=ids["subject_one"],
            idempotency_key=action_id,
            request_sha256="b" * 64,
            expected_memory_generation=1,
            resulting_memory_generation=2,
            targets=[],
            revision_ids=[],
            outcome="committed",
            actor_label="history fixture",
        )
    )
    return action_id


async def fact(
    connection,
    ids,
    *,
    source_id,
    source_run_id,
    content,
    quote=None,
    status="active",
    subject_key="subject_one",
    fact_type="person.preference",
    qualifier="drink",
    value="早上更喜欢咖啡",
):
    quote = quote or content
    fact_id, revision_id = str(uuid4()), str(uuid4())
    await connection.execute(
        insert(memory_facts).values(
            id=fact_id,
            workspace_id=ids["workspace"],
            subject_id=ids[subject_key],
            entity_id=ids[subject_key],
            normalized_key=f"history-{fact_id}",
            fact_type=fact_type,
            qualifier=qualifier,
            value=value,
            status=status,
            version=1,
        )
    )
    await connection.execute(
        insert(memory_revisions).values(
            id=revision_id,
            fact_id=fact_id,
            workspace_id=ids["workspace"],
            subject_id=ids[subject_key],
            operation="add",
            fact_version=1,
            value=value,
            run_id=source_run_id,
        )
    )
    await connection.execute(
        update(memory_facts)
        .where(memory_facts.c.id == fact_id)
        .values(current_revision_id=revision_id)
    )
    await connection.execute(
        insert(memory_revision_sources).values(
            id=str(uuid4()),
            revision_id=revision_id,
            message_id=source_id,
            start_char=content.index(quote),
            end_char=content.index(quote) + len(quote),
            quote=quote,
            message_sha256=hashlib.sha256(content.encode()).hexdigest(),
            authority_role="user_assertion",
        )
    )
    return fact_id, revision_id


async def append_revision(
    connection,
    ids,
    *,
    fact_id,
    predecessor_id,
    fact_version,
    operation,
    reason,
    value,
    status,
    run_id,
    source_id,
    content,
):
    revision_id = str(uuid4())
    await connection.execute(
        insert(memory_revisions).values(
            id=revision_id,
            fact_id=fact_id,
            workspace_id=ids["workspace"],
            subject_id=ids["subject_one"],
            operation=operation,
            fact_version=fact_version,
            value=value,
            reason=reason,
            run_id=run_id,
        )
    )
    await connection.execute(
        insert(memory_revision_predecessors).values(
            revision_id=revision_id, predecessor_revision_id=predecessor_id
        )
    )
    await connection.execute(
        insert(memory_revision_sources).values(
            id=str(uuid4()),
            revision_id=revision_id,
            message_id=source_id,
            start_char=0,
            end_char=len(content),
            quote=content,
            message_sha256=hashlib.sha256(content.encode()).hexdigest(),
            authority_role="user_assertion",
        )
    )
    await connection.execute(
        update(memory_facts)
        .where(memory_facts.c.id == fact_id)
        .values(
            version=fact_version,
            status=status,
            value=value,
            current_revision_id=revision_id,
        )
    )
    return revision_id
