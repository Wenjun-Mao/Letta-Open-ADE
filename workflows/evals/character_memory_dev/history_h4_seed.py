"""Replay frozen H4 setup as completed, source-linked PostgreSQL history."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import insert, select, update

from .history_h4_facts import seed_fact_chains, selected_transitions

from ade_api.features.agent_runtime.embeddings import (
    EmbeddingClient,
    NATURAL_RETRIEVAL_POLICY_VERSION,
    embedding_space_key,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definition_versions,
    agent_definitions,
    conversations,
    memory_embeddings,
    memory_entities,
    memory_subjects,
    messages,
    runs,
    workspaces,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class SeededHistory:
    exchange_ids: dict[str, str]
    message_ids: dict[str, str]
    fact_ids: dict[str, str]
    target_conversation_id: str
    subject_id: str
    memory_generation: int
    setup_embedding_dispatches: int


def selected_setup(
    case: dict, through: str | None = None, *, empty_setup: bool = False
) -> list[dict]:
    if empty_setup:
        return []
    if through is None:
        return list(case["setup"])
    ids = [item["id"] for item in case["setup"]]
    return list(case["setup"][: ids.index(through) + 1])


async def seed_history_case(
    engine,
    session: dict,
    *,
    case: dict,
    token: str,
    transport,
    embedding_model: str,
    through: str | None = None,
    empty_setup: bool = False,
) -> SeededHistory:
    """Seed only setup visible at target time; every message has a completed run."""
    setup = selected_setup(case, through, empty_setup=empty_setup)
    included = {item["id"] for item in setup}
    full = len(setup) == len(case["setup"])
    exchange_ids: dict[str, str] = {}
    message_ids: dict[str, str] = {}
    fact_ids: dict[str, str] = {}
    indexed: list[tuple[str, str, str, str, str, str | None, str | None]] = []
    subject_id = session["memory_subject"]["id"]
    target_id = session["conversation"]["id"]
    target_version_id = session["conversation"]["agent_definition_id"]
    async with engine.begin() as connection:
        base_version = (
            (
                await connection.execute(
                    select(agent_definition_versions).where(
                        agent_definition_versions.c.id == target_version_id
                    )
                )
            )
            .mappings()
            .one()
        )
        base_root = (
            (
                await connection.execute(
                    select(agent_definitions).where(
                        agent_definitions.c.id == base_version["agent_definition_id"]
                    )
                )
            )
            .mappings()
            .one()
        )
        workspace_id = str(base_version["workspace_id"])
        subject_entity_id = await connection.scalar(
            select(memory_entities.c.id).where(
                memory_entities.c.subject_id == subject_id,
                memory_entities.c.kind == "subject",
            )
        )
        assert subject_entity_id is not None
        alternative_workspace_id = str(uuid4())
        alternative_root_ids: dict[tuple[str, str], str] = {}
        purpose_version_id: str | None = None
        version_ids: dict[tuple[str, str, str, int], str] = {
            ("primary", "primary", "evaluation", 1): str(target_version_id)
        }
        subject_ids = {
            ("primary", "primary"): str(subject_id),
        }

        async def ensure_version(
            workspace: str, root: str, purpose: str, version: int
        ) -> str:
            key = (workspace, root, purpose, version)
            if key in version_ids:
                return version_ids[key]
            target_workspace = (
                workspace_id if workspace == "primary" else alternative_workspace_id
            )
            alternative_root = not (workspace == "primary" and root == "primary")
            target_root = (
                alternative_root_ids.setdefault((workspace, root), str(uuid4()))
                if alternative_root
                else str(base_root["id"])
            )
            if alternative_root:
                exists = await connection.scalar(
                    select(agent_definitions.c.id).where(
                        agent_definitions.c.id == target_root
                    )
                )
                if exists is None:
                    await connection.execute(
                        insert(agent_definitions).values(
                            id=target_root,
                            workspace_id=target_workspace,
                            definition_key=f"h4_alt_{token}_{workspace}_{root}",
                            name="H4 excluded root",
                            purpose=purpose,
                        )
                    )
            version_id = str(uuid4())
            fields = {
                field: base_version[field]
                for field in (
                    "name",
                    "model_key",
                    "reviewer_model_key",
                    "embedding_model_key",
                    "prompt_key",
                    "prompt_sha256",
                    "prompt_content",
                    "persona_key",
                    "persona_sha256",
                    "persona_content",
                    "tool_names",
                    "memory_policy_version",
                    "qualification_state",
                    "deployment_snapshot",
                )
            }
            await connection.execute(
                insert(agent_definition_versions).values(
                    id=version_id,
                    workspace_id=target_workspace,
                    agent_definition_id=target_root,
                    definition_key=(
                        base_root["definition_key"]
                        if not alternative_root
                        else f"h4_alt_{token}_{workspace}_{root}"
                    ),
                    version=version,
                    purpose=purpose,
                    **fields,
                )
            )
            version_ids[key] = version_id
            if alternative_root:
                await connection.execute(
                    update(agent_definitions)
                    .where(agent_definitions.c.id == target_root)
                    .values(current_version_id=version_id)
                )
            return version_id

        async def ensure_subject(workspace: str, subject: str) -> str:
            key = (workspace, subject)
            if key in subject_ids:
                return subject_ids[key]
            target_workspace = (
                workspace_id if workspace == "primary" else alternative_workspace_id
            )
            target_subject = str(uuid4())
            await connection.execute(
                insert(memory_subjects).values(
                    id=target_subject,
                    workspace_id=target_workspace,
                    external_key=f"h4-excluded-{token}-{workspace}-{subject}",
                    display_name="H4 excluded subject",
                    purpose="evaluation",
                )
            )
            await connection.execute(
                insert(memory_entities).values(
                    id=str(uuid4()),
                    workspace_id=target_workspace,
                    subject_id=target_subject,
                    kind="subject",
                    label="H4 excluded subject",
                )
            )
            subject_ids[key] = target_subject
            return target_subject

        if any(item.get("workspace") == "different" for item in setup):
            await connection.execute(
                insert(workspaces).values(
                    id=alternative_workspace_id,
                    workspace_key=f"h4-excluded-{token}",
                    name="H4 excluded workspace",
                )
            )
        if any(item.get("purpose") == "preview" for item in setup):
            purpose_version_id = await ensure_version(
                "primary", "primary", "preview", 2
            )
        chat_ids: dict[str, str] = {}
        chat_counts: dict[str, int] = {}
        write_exchange_ids = {
            transition["source"].split(":", 1)[0]
            for fact in case["facts"]
            for transition in selected_transitions(fact, included, full=full)
            if transition["source"] is not None
        }
        generation = 1
        for exchange in setup:
            chat = exchange["chat"]
            source_workspace = exchange.get("workspace", "primary")
            source_subject = exchange.get("subject", "primary")
            source_root = exchange.get("root", "primary")
            source_purpose = exchange.get("purpose", "evaluation")
            version = exchange.get("version", 1)
            if chat not in chat_ids:
                source_version_id = (
                    purpose_version_id
                    if source_purpose == "preview"
                    else await ensure_version(
                        source_workspace, source_root, source_purpose, version
                    )
                )
                source_subject_id = await ensure_subject(
                    source_workspace, source_subject
                )
                chat_ids[chat] = str(uuid4())
                chat_counts[chat] = 0
                await connection.execute(
                    insert(conversations).values(
                        id=chat_ids[chat],
                        workspace_id=(
                            workspace_id
                            if source_workspace == "primary"
                            else alternative_workspace_id
                        ),
                        agent_definition_version_id=source_version_id,
                        memory_subject_id=source_subject_id,
                        title=f"H4 setup {case['id']} {chat}",
                        purpose=source_purpose,
                        archived_at=(
                            datetime.fromisoformat(exchange["assistant_at"])
                            if exchange.get("archived")
                            else None
                        ),
                    )
                )
            chat_counts[chat] += 1
            run_id = str(uuid4())
            exchange_ids[exchange["id"]] = run_id
            source_workspace_id = (
                workspace_id
                if source_workspace == "primary"
                else alternative_workspace_id
            )
            await connection.execute(
                insert(runs).values(
                    id=run_id,
                    workspace_id=source_workspace_id,
                    conversation_id=chat_ids[chat],
                    idempotency_key=f"h4-setup-{token}-{exchange['id']}",
                    request_hash=_digest(exchange["user"]),
                    status="succeeded",
                    qualification_state="unqualified",
                    accepted_runtime_mode="development",
                    timeout_seconds=180,
                    retry_count=0,
                    accepted_conversation_version=chat_counts[chat],
                    accepted_memory_generation=generation,
                    attempt_count=1,
                    created_at=datetime.fromisoformat(exchange["user_at"]),
                    started_at=datetime.fromisoformat(exchange["user_at"]),
                    finished_at=datetime.fromisoformat(exchange["assistant_at"]),
                )
            )
            for role in ("user", "assistant"):
                content = exchange[role]
                message_id = str(uuid4())
                message_ids[f"{exchange['id']}:{role}"] = message_id
                await connection.execute(
                    insert(messages).values(
                        id=message_id,
                        workspace_id=source_workspace_id,
                        conversation_id=chat_ids[chat],
                        sequence=exchange[f"{role}_sequence"],
                        role=role,
                        content=content,
                        content_sha256=_digest(content),
                        run_id=run_id,
                        created_at=datetime.fromisoformat(exchange[f"{role}_at"]),
                    )
                )
            if exchange["id"] in write_exchange_ids:
                generation += 1
        for chat, conversation_id in chat_ids.items():
            await connection.execute(
                update(conversations)
                .where(conversations.c.id == conversation_id)
                .values(version=chat_counts[chat] + 1)
            )
        target_version = case.get("target", {}).get("version", 1)
        if target_version != 1:
            target_definition_version_id = await ensure_version(
                "primary", "primary", "evaluation", target_version
            )
            await connection.execute(
                update(conversations)
                .where(conversations.c.id == target_id)
                .values(agent_definition_version_id=target_definition_version_id)
            )
            await connection.execute(
                update(agent_definitions)
                .where(agent_definitions.c.id == base_root["id"])
                .values(current_version_id=target_definition_version_id)
            )

        fact_ids, indexed, generation = await seed_fact_chains(
            connection,
            case=case,
            setup=setup,
            included=included,
            full=full,
            workspace_id=workspace_id,
            subject_id=subject_id,
            subject_entity_id=str(subject_entity_id),
            exchange_ids=exchange_ids,
            message_ids=message_ids,
            token=token,
            generation=generation,
        )
        await connection.execute(
            update(memory_subjects)
            .where(memory_subjects.c.id == subject_id)
            .values(memory_generation=generation)
        )

    if indexed:
        deployment = next(
            item
            for item in session["agent_definition"]["deployments"]
            if item["role"] == "retriever"
        )
        space_key = embedding_space_key(deployment)
        documents = [
            f"lifecycle_status: {status}\nfact_type: {fact_type}\n"
            f"qualifier: {qualifier or ''}\nvalue: {value}"
            for _, _, status, fact_type, value, qualifier, _ in indexed
        ]
        vectors = await EmbeddingClient(transport).embed(
            model_key=embedding_model, inputs=documents, timeout_seconds=180
        )
        if any(len(vector) != 1024 for vector in vectors):
            raise RuntimeError("H4 setup vector dimensions differ from H2 binding")
        async with engine.begin() as connection:
            for (fact_id, revision_id, _, _, _, _, _), vector in zip(
                indexed, vectors, strict=True
            ):
                await connection.execute(
                    insert(memory_embeddings).values(
                        id=str(uuid4()),
                        workspace_id=workspace_id,
                        subject_id=subject_id,
                        fact_id=fact_id,
                        revision_id=revision_id,
                        model_fingerprint=space_key,
                        dimensions=1024,
                        normalized=True,
                        retrieval_policy_version=NATURAL_RETRIEVAL_POLICY_VERSION,
                        embedding=vector,
                    )
                )
    return SeededHistory(
        exchange_ids=exchange_ids,
        message_ids=message_ids,
        fact_ids=fact_ids,
        target_conversation_id=target_id,
        subject_id=subject_id,
        memory_generation=generation,
        setup_embedding_dispatches=int(bool(indexed)),
    )
