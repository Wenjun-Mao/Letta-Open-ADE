from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncConnection

from .contracts import MemoryOperation
from .memory_policy import PreparedMemoryOperation, PreparedMemoryReview
from .persistence.memory import MemoryRepository


async def commit_memory_review(
    connection: AsyncConnection,
    *,
    workspace_id: str,
    subject_id: str,
    run_id: str,
    review: PreparedMemoryReview,
    operation_embeddings: tuple[list[float] | None, ...],
    embedding_fingerprint: str,
    embedding_dimensions: int,
    retrieval_policy_version: str,
) -> list[dict[str, Any]]:
    if len(review.operations) != len(operation_embeddings):
        raise ValueError("memory operations and embeddings must stay aligned")
    repository = MemoryRepository(connection)
    for entity in review.new_entities:
        await repository.create_entity(
            {
                "id": entity.id,
                "workspace_id": workspace_id,
                "subject_id": subject_id,
                "kind": entity.kind,
                "label": entity.label,
            }
        )

    committed: list[dict[str, Any]] = []
    for operation, embedding in zip(
        review.operations, operation_embeddings, strict=True
    ):
        if operation.proposal.operation is MemoryOperation.ADD:
            fact, revision = await _create_fact(
                repository,
                workspace_id=workspace_id,
                subject_id=subject_id,
                run_id=run_id,
                operation=operation,
            )
        elif operation.proposal.operation in {
            MemoryOperation.CORRECT,
            MemoryOperation.FORGET,
        }:
            fact, revision = await _revise_fact(
                repository,
                workspace_id=workspace_id,
                subject_id=subject_id,
                run_id=run_id,
                operation=operation,
            )
        else:  # pragma: no cover - MemoryOperation is closed by Pydantic.
            raise AssertionError("unsupported memory operation")
        if embedding is not None:
            if not embedding_dimensions or len(embedding) != embedding_dimensions:
                raise ValueError("memory embedding dimensions changed during commit")
            await repository.create_embedding(
                {
                    "id": str(uuid4()),
                    "workspace_id": workspace_id,
                    "subject_id": subject_id,
                    "fact_id": fact["id"],
                    "revision_id": revision["id"],
                    "model_fingerprint": embedding_fingerprint,
                    "dimensions": embedding_dimensions,
                    "normalized": True,
                    "retrieval_policy_version": retrieval_policy_version,
                    "embedding": embedding,
                }
            )
        committed.append(
            {
                "revision_id": str(revision["id"]),
                "fact_id": str(fact["id"]),
                "operation": operation.proposal.operation.value,
                "fact_version": int(revision["fact_version"]),
                "source_message_ids": [operation.evidence.message_id],
            }
        )
    return committed


async def _create_fact(
    repository: MemoryRepository,
    *,
    workspace_id: str,
    subject_id: str,
    run_id: str,
    operation: PreparedMemoryOperation,
    predecessor_revision_ids: tuple[str, ...] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    fact_id = str(uuid4())
    revision_id = str(uuid4())
    return await repository.create_initial_revision(
        {
            "id": fact_id,
            "workspace_id": workspace_id,
            "subject_id": subject_id,
            "entity_id": operation.entity_id,
            "normalized_key": operation.normalized_key,
            "fact_type": operation.fact_type,
            "qualifier": operation.qualifier,
            "value": operation.value,
            "status": "active",
            "version": 1,
            "current_revision_id": None,
        },
        {
            "id": revision_id,
            "fact_id": fact_id,
            "workspace_id": workspace_id,
            "subject_id": subject_id,
            "operation": operation.proposal.operation.value,
            "fact_version": 1,
            "value": operation.value,
            "run_id": run_id,
        },
        evidence=[_evidence_payload(operation)],
        predecessor_revision_ids=predecessor_revision_ids,
    )


async def _revise_fact(
    repository: MemoryRepository,
    *,
    workspace_id: str,
    subject_id: str,
    run_id: str,
    operation: PreparedMemoryOperation,
) -> tuple[dict[str, Any], dict[str, Any]]:
    fact = operation.existing_fact
    if fact is None:
        raise ValueError("revising memory requires an existing fact")
    next_version = int(fact["version"]) + 1
    revision = await repository.create_revision(
        {
            "id": str(uuid4()),
            "fact_id": fact["id"],
            "workspace_id": workspace_id,
            "subject_id": subject_id,
            "operation": operation.proposal.operation.value,
            "fact_version": next_version,
            "value": operation.value,
            "run_id": run_id,
        },
        expected_fact_version=int(fact["version"]),
        next_fact_status=(
            "forgotten"
            if operation.proposal.operation is MemoryOperation.FORGET
            else "active"
        ),
        updated_at=datetime.now(UTC),
        predecessor_revision_ids=(str(fact["current_revision_id"]),),
        evidence=[_evidence_payload(operation)],
    )
    next_fact = dict(fact)
    next_fact.update(
        {
            "value": operation.value,
            "status": (
                "forgotten"
                if operation.proposal.operation is MemoryOperation.FORGET
                else "active"
            ),
            "version": next_version,
            "current_revision_id": revision["id"],
        }
    )
    return next_fact, revision


def _evidence_payload(operation: PreparedMemoryOperation) -> dict[str, Any]:
    evidence = operation.evidence
    return {
        "id": str(uuid4()),
        "message_id": evidence.message_id,
        "start_char": evidence.start_char,
        "end_char": evidence.end_char,
        "quote": evidence.quote,
        "message_sha256": evidence.message_sha256,
    }
