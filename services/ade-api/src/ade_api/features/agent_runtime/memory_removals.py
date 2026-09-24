"""Exact-target, atomic operator removal of saved subject assertions."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .contracts import MemoryRemovalRequest
from .database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
    require_default_workspace,
)
from .errors import (
    MemoryActionIdempotencyConflict,
    MemoryGenerationConflict,
    MemoryTargetConflict,
    RuntimeValidationError,
)
from .persistence.memory import MemoryRepository
from .persistence.memory_actions import MemoryActionRepository
from .persistence.base import NotFoundError


class MemoryRemovalService:
    def __init__(self, database: RuntimeDatabase) -> None:
        self.database = database

    async def remove(
        self,
        subject_id: str,
        request: MemoryRemovalRequest,
        *,
        actor_label: str,
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        if not actor_label.strip() or len(actor_label) > 200:
            raise RuntimeValidationError("operator identity label is invalid")
        targets = [
            {
                "fact_id": str(target.fact_id),
                "expected_version": target.expected_version,
            }
            for target in request.targets
        ]
        targets.sort(key=lambda target: target["fact_id"])
        request_hash = _request_hash(
            subject_id,
            request.expected_memory_generation,
            targets,
        )
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                memory = MemoryRepository(connection)
                actions = MemoryActionRepository(connection)
                # Subject-only actions never acquire a conversation lock. All
                # run writers use conversation -> subject -> sorted fact locks.
                subject = await memory.lock_subject(subject_id)
                require_default_workspace(subject)
                if subject["purpose"] != "agent_studio" or subject["archived_at"]:
                    raise RuntimeValidationError(
                        "memory removal requires an active Agent Studio subject"
                    )
                prior = await actions.find_by_key(subject_id, request.idempotency_key)
                if prior is not None:
                    if prior["request_sha256"] != request_hash:
                        raise MemoryActionIdempotencyConflict(
                            "idempotency key belongs to a different removal request"
                        )
                    return _receipt(prior, replayed=True)
                generation = int(subject["memory_generation"])
                if generation != request.expected_memory_generation:
                    raise MemoryGenerationConflict(
                        "subject memory generation changed before removal"
                    )

                facts = []
                for target in targets:
                    try:
                        fact = await memory.lock_fact(target["fact_id"])
                    except NotFoundError as exc:
                        raise MemoryTargetConflict(
                            "removal target is not an eligible exact subject version"
                        ) from exc
                    if (
                        str(fact["subject_id"]) != subject_id
                        or str(fact["workspace_id"]) != DEFAULT_WORKSPACE_ID
                        or fact["status"] not in {"active", "inactive"}
                        or int(fact["version"]) != target["expected_version"]
                        or fact["current_revision_id"] is None
                    ):
                        raise MemoryTargetConflict(
                            "removal target is not an eligible exact subject version"
                        )
                    facts.append(fact)

                action_id = str(uuid4())
                revision_ids = [str(uuid4()) for _ in facts]
                receipt = await actions.create(
                    {
                        "id": action_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "subject_id": subject_id,
                        "idempotency_key": request.idempotency_key,
                        "request_sha256": request_hash,
                        "expected_memory_generation": generation,
                        "resulting_memory_generation": generation + 1,
                        "targets": targets,
                        "revision_ids": revision_ids,
                        "outcome": "committed",
                        "actor_label": actor_label,
                    }
                )
                for fact, revision_id in zip(facts, revision_ids, strict=True):
                    await memory.create_revision(
                        {
                            "id": revision_id,
                            "fact_id": fact["id"],
                            "workspace_id": DEFAULT_WORKSPACE_ID,
                            "subject_id": subject_id,
                            "operation": "forget",
                            "reason": "forgotten",
                            "fact_version": int(fact["version"]) + 1,
                            "value": None,
                            "action_id": action_id,
                        },
                        expected_fact_version=int(fact["version"]),
                        next_fact_status="forgotten",
                        updated_at=datetime.now(UTC),
                        predecessor_revision_ids=(str(fact["current_revision_id"]),),
                    )
                await memory.advance_memory_generation(
                    subject_id, expected_generation=generation
                )
                return _receipt(receipt, replayed=False)


def _request_hash(
    subject_id: str, expected_generation: int, targets: list[dict[str, Any]]
) -> str:
    content = json.dumps(
        {
            "subject_id": subject_id,
            "expected_memory_generation": expected_generation,
            "targets": targets,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _receipt(row: dict[str, Any], *, replayed: bool) -> dict[str, Any]:
    return {
        "action_id": str(row["id"]),
        "outcome": row["outcome"],
        "revision_ids": [str(value) for value in row["revision_ids"]],
        "resulting_memory_generation": int(row["resulting_memory_generation"]),
        "idempotent_replay": replayed,
        "committed_at": row["created_at"],
    }
