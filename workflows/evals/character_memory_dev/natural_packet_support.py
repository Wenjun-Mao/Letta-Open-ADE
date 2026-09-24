"""Synthetic source-backed histories and fake router for serialized packet probes."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from sqlalchemy import insert, select, update

from ade_api.features.agent_runtime.persistence.metadata import (
    conversations,
    memory_entities,
    memory_facts,
    memory_revision_predecessors,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
    messages,
    runs,
)


class PacketTransport:
    def __init__(self, catalog: dict) -> None:
        self._catalog = catalog
        self.calls: list[str] = []

    async def catalog(self, *, timeout_seconds):
        return self._catalog

    async def embeddings(self, payload, *, timeout_seconds):
        self.calls.append("embedding")
        return {
            "data": [
                {"index": index, "embedding": [1.0, 0.0, 0.0]}
                for index, _ in enumerate(payload["input"])
            ]
        }

    async def chat_completion(self, payload, *, timeout_seconds):
        model = payload["model"]
        self.calls.append(model)
        content = (
            "Roxy is your Husky."
            if model == "fake::conversation"
            else json.dumps({"proposals": [], "claim_dispositions": []})
        )
        return {
            "id": f"packet-{uuid4()}",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        }


async def seed_pressure_state(engine, session: dict, *, token: str) -> None:
    """Insert complete prior exchanges and source-backed unrelated facts as setup."""

    subject = session["memory_subject"]
    conversation = session["conversation"]
    subject_id = subject["id"]
    conversation_id = conversation["id"]
    setup_run_id = str(uuid4())
    history_run_id = str(uuid4())
    values = [f"unrelated-{index:02d}-" + "x" * 15 for index in range(48)]
    source_lines = [
        f"For topic-{index:03d} I prefer {value}." for index, value in enumerate(values)
    ]
    source_content = "\n".join(source_lines)
    source_id = str(uuid4())
    setup_conversation_id = str(uuid4())
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
                id=setup_conversation_id,
                workspace_id=workspace_id,
                agent_definition_version_id=conversation["agent_definition_id"],
                memory_subject_id=subject_id,
                title="Synthetic fact setup source",
                purpose="evaluation",
            )
        )
        await connection.execute(
            insert(runs).values(
                id=setup_run_id,
                workspace_id=workspace_id,
                conversation_id=setup_conversation_id,
                idempotency_key=f"setup-{token}",
                request_hash=hashlib.sha256(token.encode()).hexdigest(),
                status="succeeded",
                qualification_state="unqualified",
                accepted_runtime_mode="development",
                timeout_seconds=30,
                retry_count=0,
                accepted_conversation_version=1,
                accepted_memory_generation=1,
                attempt_count=1,
            )
        )
        await connection.execute(
            insert(runs).values(
                id=history_run_id,
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                idempotency_key=f"history-{token}",
                request_hash=hashlib.sha256(f"history-{token}".encode()).hexdigest(),
                status="succeeded",
                qualification_state="unqualified",
                accepted_runtime_mode="development",
                timeout_seconds=30,
                retry_count=0,
                accepted_conversation_version=1,
                accepted_memory_generation=1,
                attempt_count=1,
            )
        )
        prior = [
            ("user", "My dog Roxy is a Husky."),
            ("assistant", "Roxy is your Husky."),
            ("user", "I am asking about Roxy again."),
            ("assistant", "I remember Roxy."),
        ]
        for sequence, (role, content) in enumerate(prior, start=1):
            await connection.execute(
                insert(messages).values(
                    id=str(uuid4()),
                    workspace_id=workspace_id,
                    conversation_id=conversation_id,
                    sequence=sequence,
                    role=role,
                    content=content,
                    content_sha256=hashlib.sha256(content.encode()).hexdigest(),
                    run_id=history_run_id,
                )
            )
        await connection.execute(
            insert(messages).values(
                id=source_id,
                workspace_id=workspace_id,
                conversation_id=setup_conversation_id,
                sequence=1,
                role="user",
                content=source_content,
                content_sha256=hashlib.sha256(source_content.encode()).hexdigest(),
                run_id=setup_run_id,
            )
        )
        # A separate source conversation keeps the probe's local suffix paired.
        source_offset = 0
        for index in range(48):
            fact_id, revision_id = str(uuid4()), str(uuid4())
            inactive = index % 3 == 0
            value = values[index]
            source_line = source_lines[index]
            await connection.execute(
                insert(memory_facts).values(
                    id=fact_id,
                    workspace_id=workspace_id,
                    subject_id=subject_id,
                    entity_id=entity_id,
                    normalized_key=f"person.preference|subject|{index:03d}",
                    fact_type="person.preference",
                    qualifier=f"topic-{index:03d}",
                    value=value,
                    status="inactive" if inactive else "active",
                    assertion_schema_version=2,
                    version=2 if inactive else 1,
                )
            )
            await connection.execute(
                insert(memory_revisions).values(
                    id=revision_id,
                    fact_id=fact_id,
                    workspace_id=workspace_id,
                    subject_id=subject_id,
                    operation="add",
                    fact_version=1,
                    value=value,
                    run_id=setup_run_id,
                )
            )
            await connection.execute(
                insert(memory_revision_sources).values(
                    id=str(uuid4()),
                    revision_id=revision_id,
                    message_id=source_id,
                    start_char=source_offset,
                    end_char=source_offset + len(source_line),
                    quote=source_line,
                    message_sha256=hashlib.sha256(source_content.encode()).hexdigest(),
                    authority_role="user_assertion",
                )
            )
            current_revision_id = revision_id
            if inactive:
                current_revision_id = str(uuid4())
                await connection.execute(
                    insert(memory_revisions).values(
                        id=current_revision_id,
                        fact_id=fact_id,
                        workspace_id=workspace_id,
                        subject_id=subject_id,
                        operation="end",
                        fact_version=2,
                        value=value,
                        run_id=setup_run_id,
                        reason="ended",
                    )
                )
                await connection.execute(
                    insert(memory_revision_predecessors).values(
                        revision_id=current_revision_id,
                        predecessor_revision_id=revision_id,
                    )
                )
            await connection.execute(
                update(memory_facts)
                .where(memory_facts.c.id == fact_id)
                .values(current_revision_id=current_revision_id)
            )
            source_offset += len(source_line) + 1
        await connection.execute(
            update(memory_subjects)
            .where(memory_subjects.c.id == subject_id)
            .values(memory_generation=2)
        )
