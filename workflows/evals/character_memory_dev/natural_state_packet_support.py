"""Source-backed synthetic lifecycle setup for isolated worker packet probes."""

from __future__ import annotations

import hashlib
from uuid import uuid4

from sqlalchemy import insert, select, update

from ade_api.features.agent_runtime.compaction import (
    CompactionPlan,
    compaction_input_sha256,
    compaction_policy_sha256,
    compaction_prompt_sha256,
)
from ade_api.features.agent_runtime.embeddings import NATURAL_RETRIEVAL_POLICY_VERSION
from ade_api.features.agent_runtime.persistence.metadata import (
    conversation_summaries,
    conversations,
    memory_embeddings,
    memory_entities,
    memory_facts,
    memory_revision_predecessors,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
    messages,
    runs,
    summary_sources,
)


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


async def seed_state_packet(
    engine,
    session: dict,
    *,
    token: str,
    history: list[tuple[str, str]],
    facts: list[dict],
    summary_content: str = "",
) -> dict:
    """Insert completed exchanges, lifecycle revision chains and optional summary."""

    subject_id = session["memory_subject"]["id"]
    conversation_id = session["conversation"]["id"]
    setup_id = str(uuid4())
    message_ids: list[str] = []
    fact_ids: list[str] = []
    async with engine.begin() as connection:
        workspace_id = (
            await connection.execute(
                select(memory_subjects.c.workspace_id).where(
                    memory_subjects.c.id == subject_id
                )
            )
        ).scalar_one()
        entity_id = (
            await connection.execute(
                select(memory_entities.c.id).where(
                    memory_entities.c.subject_id == subject_id,
                    memory_entities.c.kind == "subject",
                )
            )
        ).scalar_one()
        await connection.execute(
            insert(conversations).values(
                id=setup_id,
                workspace_id=workspace_id,
                agent_definition_version_id=session["conversation"][
                    "agent_definition_id"
                ],
                memory_subject_id=subject_id,
                title="Synthetic lifecycle source",
                purpose="evaluation",
            )
        )

        async def source_message(content: str, *, sequence: int) -> tuple[str, str]:
            run_id, message_id = str(uuid4()), str(uuid4())
            await connection.execute(
                insert(runs).values(
                    id=run_id,
                    workspace_id=workspace_id,
                    conversation_id=setup_id,
                    idempotency_key=f"source-{token}-{sequence}",
                    request_hash=_digest(f"source-{token}-{sequence}"),
                    status="succeeded",
                    qualification_state="unqualified",
                    accepted_runtime_mode="development",
                    timeout_seconds=30,
                    retry_count=0,
                    accepted_conversation_version=sequence,
                    accepted_memory_generation=1,
                    attempt_count=1,
                )
            )
            await connection.execute(
                insert(messages).values(
                    id=message_id,
                    workspace_id=workspace_id,
                    conversation_id=setup_id,
                    sequence=sequence,
                    role="user",
                    content=content,
                    content_sha256=_digest(content),
                    run_id=run_id,
                )
            )
            return run_id, message_id

        source_sequence = 0
        for index, fact in enumerate(facts):
            fact_id = str(uuid4())
            fact_ids.append(fact_id)
            fact_entity_id = entity_id
            if fact["fact_type"] == "relationship.person":
                fact_entity_id = str(uuid4())
                await connection.execute(
                    insert(memory_entities).values(
                        id=fact_entity_id,
                        workspace_id=workspace_id,
                        subject_id=subject_id,
                        kind="related_person",
                        label="Xiao Wang",
                    )
                )
            transitions = [("add", None, fact["assertion"])] + [
                (transition["operation"], transition["reason"], transition["source"])
                for transition in fact.get("transitions", [])
            ]
            await connection.execute(
                insert(memory_facts).values(
                    id=fact_id,
                    workspace_id=workspace_id,
                    subject_id=subject_id,
                    entity_id=fact_entity_id,
                    normalized_key=f"{fact['fact_type']}|subject|case-{index}",
                    fact_type=fact["fact_type"],
                    qualifier=fact.get("qualifier"),
                    value=fact["value"],
                    status=fact["status"],
                    assertion_schema_version=2,
                    version=len(transitions),
                )
            )
            prior_revision = None
            first_revision = None
            for version, (operation, reason, content) in enumerate(transitions, 1):
                source_sequence += 1
                run_id, message_id = await source_message(
                    content, sequence=source_sequence
                )
                revision_id = str(uuid4())
                if first_revision is None:
                    first_revision = revision_id
                await connection.execute(
                    insert(memory_revisions).values(
                        id=revision_id,
                        fact_id=fact_id,
                        workspace_id=workspace_id,
                        subject_id=subject_id,
                        operation=operation,
                        fact_version=version,
                        value=fact["value"],
                        run_id=run_id,
                        reason=reason,
                    )
                )
                await connection.execute(
                    insert(memory_revision_sources).values(
                        id=str(uuid4()),
                        revision_id=revision_id,
                        message_id=message_id,
                        start_char=0,
                        end_char=len(content),
                        quote=content,
                        message_sha256=_digest(content),
                        authority_role="user_assertion",
                    )
                )
                if prior_revision is not None:
                    await connection.execute(
                        insert(memory_revision_predecessors).values(
                            revision_id=revision_id,
                            predecessor_revision_id=prior_revision,
                        )
                    )
                prior_revision = revision_id
            await connection.execute(
                update(memory_facts)
                .where(memory_facts.c.id == fact_id)
                .values(current_revision_id=prior_revision)
            )
            if fact.get("index_prior"):
                await connection.execute(
                    insert(memory_embeddings).values(
                        id=str(uuid4()),
                        workspace_id=workspace_id,
                        subject_id=subject_id,
                        fact_id=fact_id,
                        revision_id=prior_revision
                        if fact["status"] != "forgotten"
                        else first_revision,
                        model_fingerprint="3" * 64,
                        dimensions=3,
                        normalized=True,
                        retrieval_policy_version=NATURAL_RETRIEVAL_POLICY_VERSION,
                        embedding=[1.0, 0.0, 0.0],
                    )
                )

        history_run_ids = []
        for turn, (user_content, assistant_content) in enumerate(history, 1):
            run_id = str(uuid4())
            history_run_ids.append(run_id)
            await connection.execute(
                insert(runs).values(
                    id=run_id,
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    idempotency_key=f"history-{token}-{turn}",
                    request_hash=_digest(f"history-{token}-{turn}"),
                    status="succeeded",
                    qualification_state="unqualified",
                    accepted_runtime_mode="development",
                    timeout_seconds=30,
                    retry_count=0,
                    accepted_conversation_version=turn,
                    accepted_memory_generation=1,
                    attempt_count=1,
                )
            )
            for role, content in (
                ("user", user_content),
                ("assistant", assistant_content),
            ):
                message_id = str(uuid4())
                message_ids.append(message_id)
                await connection.execute(
                    insert(messages).values(
                        id=message_id,
                        workspace_id=workspace_id,
                        conversation_id=conversation_id,
                        sequence=len(message_ids),
                        role=role,
                        content=content,
                        content_sha256=_digest(content),
                        run_id=run_id,
                    )
                )
        if summary_content:
            assert history_run_ids and len(message_ids) >= 2
            summary_id = str(uuid4())
            # This supplied-summary fixture is deliberately hand-authored. Its
            # metadata still hashes the exact synthetic source packet rather
            # than carrying arbitrary placeholder digests.
            first_user, first_assistant = history[0]
            summary_plan = CompactionPlan(
                previous_summary_id=None,
                expected_summary_version=0,
                previous_summary_content="",
                through_sequence=2,
                source_message_ids=tuple(message_ids[:2]),
                incremental_messages=(
                    {"sequence": 1, "role": "user", "content": first_user},
                    {"sequence": 2, "role": "assistant", "content": first_assistant},
                ),
            )
            await connection.execute(
                insert(conversation_summaries).values(
                    id=summary_id,
                    conversation_id=conversation_id,
                    version=1,
                    through_sequence=2,
                    content=summary_content,
                    run_id=history_run_ids[0],
                    model_key="fake::conversation",
                    model_fingerprint="1" * 64,
                    provider_request_id=f"scripted-summary-{token}",
                    content_sha256=_digest(summary_content),
                    prompt_sha256=compaction_prompt_sha256(),
                    input_sha256=compaction_input_sha256(summary_plan),
                    policy_sha256=compaction_policy_sha256(),
                )
            )
            await connection.execute(
                insert(summary_sources),
                [
                    {"summary_id": summary_id, "message_id": message_id}
                    for message_id in message_ids[:2]
                ],
            )
        await connection.execute(
            update(memory_subjects)
            .where(memory_subjects.c.id == subject_id)
            .values(memory_generation=2)
        )
    return {"fact_ids": fact_ids, "history_message_ids": message_ids}
