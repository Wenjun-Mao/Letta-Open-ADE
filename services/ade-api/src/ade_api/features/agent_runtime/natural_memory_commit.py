"""Atomic storage of a validated mixed natural-memory review."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncConnection

from .natural_memory_policy import PreparedNaturalOperation, PreparedNaturalReview
from .persistence.base import OptimisticLockError
from .persistence.memory import MemoryRepository


async def commit_natural_memory_review(
    connection: AsyncConnection,
    *,
    workspace_id: str,
    subject_id: str,
    run_id: str,
    review: PreparedNaturalReview,
    operation_embeddings: tuple[list[float] | None, ...],
    embedding_fingerprint: str,
    embedding_dimensions: int,
    retrieval_policy_version: str,
    expected_memory_generation: int,
) -> list[dict[str, Any]]:
    if len(review.operations) != len(operation_embeddings):
        raise ValueError("natural memory operations and embeddings must align")
    if not review.operations:
        return []
    repository = MemoryRepository(connection)
    subject = await repository.lock_subject(subject_id)
    if int(subject["memory_generation"]) != expected_memory_generation:
        raise OptimisticLockError("subject memory changed before natural review commit")
    used_entity_ids = {operation.entity_id for operation in review.operations}
    for entity in review.new_entities:
        if entity.id in used_entity_ids:
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
        fact, revision = await _write_operation(
            repository,
            workspace_id=workspace_id,
            subject_id=subject_id,
            run_id=run_id,
            operation=operation,
        )
        if embedding is not None:
            if not embedding_dimensions or len(embedding) != embedding_dimensions:
                raise ValueError("natural memory embedding dimensions changed")
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
                "operation": operation.proposal.operation,
                "reason": operation.revision_reason,
                "status": operation.next_status,
                "fact_version": int(revision["fact_version"]),
                "source_message_ids": sorted(
                    {source.message_id for source in operation.sources}
                ),
            }
        )
    await repository.advance_memory_generation(
        subject_id, expected_generation=expected_memory_generation
    )
    return committed


async def _write_operation(
    repository: MemoryRepository,
    *,
    workspace_id: str,
    subject_id: str,
    run_id: str,
    operation: PreparedNaturalOperation,
) -> tuple[dict[str, Any], dict[str, Any]]:
    existing = operation.existing_fact
    revision_id = str(uuid4())
    if existing is None:
        fact_id = str(uuid4())
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
                "assertion_schema_version": 2,
                "current_revision_id": None,
            },
            {
                "id": revision_id,
                "fact_id": fact_id,
                "workspace_id": workspace_id,
                "subject_id": subject_id,
                "operation": "add",
                "reason": None,
                "fact_version": 1,
                "value": operation.value,
                "run_id": run_id,
            },
            evidence=[_source_payload(source) for source in operation.sources],
        )
    version = int(existing["version"])
    revision = await repository.create_revision(
        {
            "id": revision_id,
            "fact_id": existing["id"],
            "workspace_id": workspace_id,
            "subject_id": subject_id,
            "operation": operation.proposal.operation,
            "reason": operation.revision_reason,
            "fact_version": version + 1,
            "value": operation.value,
            "run_id": run_id,
        },
        expected_fact_version=version,
        next_fact_status=operation.next_status,
        updated_at=datetime.now(UTC),
        predecessor_revision_ids=(str(existing["current_revision_id"]),),
        evidence=[_source_payload(source) for source in operation.sources],
    )
    updated = dict(existing)
    updated.update(
        {
            "value": operation.value,
            "status": operation.next_status,
            "version": version + 1,
            "current_revision_id": revision["id"],
        }
    )
    return updated, revision


def _source_payload(source) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "message_id": source.message_id,
        "start_char": source.start_char,
        "end_char": source.end_char,
        "quote": source.quote,
        "message_sha256": source.message_sha256,
        "authority_role": source.authority_role,
    }
