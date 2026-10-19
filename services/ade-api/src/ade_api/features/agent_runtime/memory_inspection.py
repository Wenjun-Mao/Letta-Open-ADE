"""Concrete scoped inspection; remote failures never masquerade as empty Memory."""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import UUID

from pydantic import ValidationError

from ade_api.integrations.hindsight import HindsightClient, HindsightError

from .errors import RuntimeNotFound, RuntimeNotReady
from .inspection_contracts import LearnedMemoryResponse
from .memory_banks import MemoryBankAccess, MemoryBankError
from .memory_progress import native_progress
from .persistence.memory_deliveries import verified_delivery
from .persistence.memory_inspection import MemoryInspectionRepository


def relationship_view(row):
    return {
        key: str(row[key]) if key.endswith("_id") else row[key]
        for key in ("subject_id", "character_root_id", "state", "last_error_code")
    }


def delivery_view(row, first=None):
    value = {
        key: row[key]
        for key in (
            "operation_id",
            "document_id",
            "message_id",
            "conversation_id",
            "role",
            "message_sequence",
            "relationship_sequence",
            "status",
            "attempt_count",
            "check_count",
            "retry_requested",
            "last_error_code",
            "native_status",
            "accepted_at",
            "retained_at",
            "last_checked_at",
            "created_at",
            "updated_at",
        )
    }
    for key in ("operation_id", "message_id", "conversation_id"):
        value[key] = str(value[key])
    value["native_progress"] = native_progress(row["native_progress"])
    value["queue_age_seconds"] = (
        max(0, (datetime.now(timezone.utc) - row["created_at"]).total_seconds())
        if row["status"] != "retained"
        else 0
    )
    value["blocked_by_operation_id"] = (
        str(first["operation_id"])
        if first and first["relationship_sequence"] < row["relationship_sequence"]
        else None
    )
    return value


def operation_view(row):
    identity = row.get("operation_id") or row.get("id")
    try:
        identity = str(UUID(identity))
    except (ValueError, TypeError, AttributeError) as exc:
        raise HindsightError("hindsight_operation_invalid") from exc
    snapshot = native_progress(row)
    if "status" not in snapshot:
        raise HindsightError("hindsight_operation_invalid")
    kind = row.get("operation_type") or row.get("task_type")
    return {
        "operation_id": identity,
        "operation_type": kind
        if kind in {"retain", "batch_retain", "consolidation", "consolidate"}
        else None,
        "status": snapshot["status"],
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "native_progress": snapshot,
    }


class MemoryInspectionService:
    def __init__(self, *, database, settings, client=None):
        self.database = database
        self.settings = settings
        self._client = client
        self._owns_client = client is None

    async def aclose(self):
        if self._owns_client and self._client is not None:
            await self._client.aclose()

    @property
    def client(self):
        if self._client is None:
            try:
                self._client = HindsightClient(
                    base_url=self.settings.hindsight_base_url,
                    api_key=self.settings.hindsight_api_key,
                    timeout_seconds=self.settings.hindsight_timeout_seconds,
                )
            except ValueError as exc:
                raise RuntimeNotReady("Memory inspection is not configured") from exc
        return self._client

    @asynccontextmanager
    async def remote(self, row):
        try:
            await MemoryBankAccess(
                engine=self.database.engine,
                client=self.client,
                workspace_id=self.database.workspace_id,
            ).ensure_ready(
                row["bank_id"],
                deadline=time.monotonic() + self.settings.hindsight_timeout_seconds,
            )
            yield self.client
        except (HindsightError, MemoryBankError, TimeoutError, ValidationError) as exc:
            raise RuntimeNotReady(
                "Memory inspection is unavailable; saved conversation and delivery state remain separate"
            ) from exc

    async def relationship(self, subject_id, character_root_id):
        await self.database.ensure_ready()
        async with (
            self.database.translated_errors(),
            self.database.engine.connect() as connection,
        ):
            return await MemoryInspectionRepository(connection).relationship(
                workspace_id=self.database.workspace_id,
                subject_id=subject_id,
                character_root_id=character_root_id,
            )

    async def deliveries(self, subject_id, character_root_id, *, limit, offset):
        row = await self.relationship(subject_id, character_root_id)
        async with self.database.engine.connect() as connection:
            counts, first, items = await MemoryInspectionRepository(connection).list(
                row["bank_id"], limit=limit, offset=offset
            )
        return {
            "relationship": relationship_view(row),
            "total": sum(counts.values()),
            "limit": limit,
            "offset": offset,
            "counts": counts,
            "blocked_operation_id": str(first["operation_id"]) if first else None,
            "items": [delivery_view(item, first) for item in items],
        }

    async def memories(self, subject_id, character_root_id, *, limit, offset):
        row = await self.relationship(subject_id, character_root_id)
        async with self.remote(row) as client:
            result = await client.memories(row["bank_id"], limit=limit, offset=offset)
            items = [
                LearnedMemoryResponse.model_validate(item).model_dump()
                for item in result["items"]
            ]
        return {
            "relationship": relationship_view(
                {**row, "state": "ready", "last_error_code": None}
            ),
            "total": result["total"],
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    async def source(self, subject_id, character_root_id, document_id):
        row = await self.relationship(subject_id, character_root_id)
        async with (
            self.database.translated_errors(),
            self.database.engine.connect() as connection,
        ):
            source = await MemoryInspectionRepository(connection).source(
                row["bank_id"], document_id
            )
        payload = verified_delivery(source).verify()["items"][0]
        async with self.remote(row) as client:
            document = await client.document(row["bank_id"], document_id)
            parameters = document.get("retain_params")
            if (
                document.get("original_text") != payload["content"]
                or not isinstance(parameters, dict)
                or parameters.get("context") != payload["context"]
            ):
                raise HindsightError("hindsight_document_changed")
        return {
            "relationship": relationship_view(row),
            "delivery": delivery_view(source),
            "content": source["content"],
            "occurred_at": source["occurred_at"],
            "definition_version_id": payload["metadata"]["definition_version_id"],
            "native_original_text": document.get("original_text"),
            "native_context": payload["context"],
        }

    async def retry_delivery(
        self, subject_id, character_root_id, operation_id, request
    ):
        row = await self.relationship(subject_id, character_root_id)
        async with (
            self.database.translated_errors(),
            self.database.engine.begin() as connection,
        ):
            delivery = await MemoryInspectionRepository(connection).retry(
                row["bank_id"],
                operation_id,
                expected_check_count=request.expected_check_count,
            )
        return delivery_view(delivery)

    async def operations(self, subject_id, character_root_id, *, limit, offset):
        row = await self.relationship(subject_id, character_root_id)
        async with self.remote(row) as client:
            result = await client.operations(row["bank_id"], limit=limit, offset=offset)
            items = [operation_view(item) for item in result["operations"]]
        return {
            "relationship": relationship_view(row),
            "total": result["total"],
            "limit": limit,
            "offset": offset,
            "items": items,
        }

    async def operation(self, subject_id, character_root_id, operation_id):
        row = await self.relationship(subject_id, character_root_id)
        async with self.remote(row) as client:
            result = await client.operation(
                row["bank_id"], operation_id, include_payload=False
            )
            if result["status"] == "not_found":
                raise RuntimeNotFound("Operation does not exist in this relationship")
            return operation_view(result)
