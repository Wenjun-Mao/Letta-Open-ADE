"""Real PostgreSQL source integrity, atomic outbox intent and relationship order."""

import asyncio
from dataclasses import replace
import hashlib
import json
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError

from ade_api.features.agent_runtime.persistence.base import IdempotencyConflictError
from ade_api.features.agent_runtime.persistence.memory_deliveries import (
    MemoryDeliveryRepository,
)
from ade_api.features.agent_runtime.persistence.memory_relationships import (
    MemoryRelationshipRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definition_versions,
    conversations,
    memory_deliveries,
    memory_relationships,
    messages,
    runs,
)
from ade_api.integrations.hindsight_sources import prepare_memory_delivery

from .hindsight_support import DATABASE_URL, engine, message, scope


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable ADE_TEST_DATABASE_URL is required"
)


def test_source_and_delivery_intent_rollback_together():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
            with pytest.raises(RuntimeError, match="injected"):
                async with db.begin() as connection:
                    source, _ = await message(connection, owner)
                    await MemoryDeliveryRepository(connection).enqueue(source)
                    raise RuntimeError("injected failure before acceptance commit")
            async with db.connect() as connection:
                for table in (messages, memory_deliveries, memory_relationships):
                    assert (
                        await connection.scalar(
                            select(func.count())
                            .select_from(table)
                            .where(
                                table.c.workspace_id == owner.relationship.workspace_id,
                            )
                        )
                        == 0
                    )
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_idempotent_delivery_keeps_original_time_payload_and_sequence():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
                source, _ = await message(
                    connection, owner, content="Original attributed source"
                )
                repository = MemoryDeliveryRepository(connection)
                first = await repository.enqueue(source)
                second = await repository.enqueue(source)
                assert first["operation_id"] == second["operation_id"]
                assert first["payload"] == second["payload"]
                assert second["relationship_sequence"] == 1
                payload = json.loads(bytes(second["payload"]))
                assert (
                    payload["items"][0]["timestamp"] == source.occurred_at.isoformat()
                )
                assert (
                    await MemoryRelationshipRepository(connection).get(
                        source.relationship.bank_id,
                        workspace_id=owner.relationship.workspace_id,
                    )
                )["next_sequence"] == 2
                with pytest.raises(IdempotencyConflictError):
                    await repository.enqueue(replace(source, content="rewritten"))
        finally:
            await db.dispose()

    asyncio.run(scenario())


@pytest.mark.parametrize("target", ["message", "definition", "binding", "payload"])
def test_database_rejects_rewriting_original_sources_and_delivery_identity(target):
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
                source, _ = await message(connection, owner)
                delivery = await MemoryDeliveryRepository(connection).enqueue(source)
            with pytest.raises(IntegrityError):
                async with db.begin() as connection:
                    if target == "message":
                        statement = (
                            update(messages)
                            .where(messages.c.id == source.message_id)
                            .values(content="rewrite")
                        )
                    elif target == "definition":
                        statement = (
                            update(agent_definition_versions)
                            .where(
                                agent_definition_versions.c.id == owner.definition["id"]
                            )
                            .values(persona_content="rewrite")
                        )
                    elif target == "binding":
                        statement = (
                            update(conversations)
                            .where(conversations.c.id == owner.conversation["id"])
                            .values(memory_subject_id=str(uuid4()))
                        )
                    else:
                        raw = bytes(delivery["payload"]) + b" "
                        statement = (
                            update(memory_deliveries)
                            .where(
                                memory_deliveries.c.operation_id
                                == delivery["operation_id"]
                            )
                            .values(
                                payload=raw,
                                payload_sha256=hashlib.sha256(raw).hexdigest(),
                            )
                        )
                    await connection.execute(statement)
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_native_delivery_bank_cannot_be_forged_for_another_character():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                first = await scope(connection)
                second = await scope(
                    connection,
                    workspace_id=first.relationship.workspace_id,
                    subject_id=first.relationship.subject_id,
                )
                source, _ = await message(connection, first)
                relationship = await MemoryRelationshipRepository(connection).ensure(
                    second.relationship
                )
                payload = prepare_memory_delivery(source)
            with pytest.raises(IntegrityError, match="source ownership mismatch"):
                async with db.begin() as connection:
                    await connection.execute(
                        insert(memory_deliveries).values(
                            operation_id=payload.operation_id,
                            workspace_id=first.relationship.workspace_id,
                            bank_id=second.relationship.bank_id,
                            configuration_sha256=relationship["configuration_sha256"],
                            message_id=source.message_id,
                            document_id=payload.document_id,
                            relationship_sequence=1,
                            payload=payload.payload,
                            payload_sha256=payload.payload_sha256,
                        )
                    )
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_postgresql_checks_payload_bytes_instead_of_trusting_the_supplied_hash():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
                source, _ = await message(connection, owner)
                relationship = await MemoryRelationshipRepository(connection).ensure(
                    owner.relationship
                )
                payload = prepare_memory_delivery(source)
            with pytest.raises(IntegrityError, match="payload_hash"):
                async with db.begin() as connection:
                    await connection.execute(
                        insert(memory_deliveries).values(
                            operation_id=payload.operation_id,
                            workspace_id=owner.relationship.workspace_id,
                            bank_id=owner.relationship.bank_id,
                            configuration_sha256=relationship["configuration_sha256"],
                            message_id=source.message_id,
                            document_id=payload.document_id,
                            relationship_sequence=1,
                            payload=payload.payload,
                            payload_sha256="0" * 64,
                        )
                    )
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_failed_generation_does_not_remove_the_accepted_user_source():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                owner = await scope(connection)
                source, run_id = await message(connection, owner)
                delivery = await MemoryDeliveryRepository(connection).enqueue(source)
                await connection.execute(
                    update(runs).where(runs.c.id == run_id).values(status="failed")
                )
            async with db.connect() as connection:
                assert (
                    await MemoryDeliveryRepository(connection).get(
                        str(delivery["operation_id"]),
                        bank_id=owner.relationship.bank_id,
                    )
                )["status"] == "queued"
                assert (
                    await connection.scalar(
                        select(func.count())
                        .select_from(messages)
                        .where(
                            messages.c.run_id == run_id,
                            messages.c.role == "assistant",
                        )
                    )
                    == 0
                )
        finally:
            await db.dispose()

    asyncio.run(scenario())


def test_ordinary_persona_versions_keep_one_relationship_and_delivery_order():
    async def scenario():
        db = engine()
        try:
            async with db.begin() as connection:
                first = await scope(connection)
                original, _ = await message(connection, first)
                one = await MemoryDeliveryRepository(connection).enqueue(original)
                second = await scope(
                    connection,
                    workspace_id=first.relationship.workspace_id,
                    subject_id=first.relationship.subject_id,
                    root=first.definition,
                )
                changed, _ = await message(connection, second)
                two = await MemoryDeliveryRepository(connection).enqueue(changed)
                assert first.definition["id"] != second.definition["id"]
                assert one["bank_id"] == two["bank_id"]
                assert [one["relationship_sequence"], two["relationship_sequence"]] == [
                    1,
                    2,
                ]
                assert json.loads(bytes(one["payload"]))["items"][0]["metadata"][
                    "definition_version_id"
                ] == str(first.definition["id"])
        finally:
            await db.dispose()

    asyncio.run(scenario())
