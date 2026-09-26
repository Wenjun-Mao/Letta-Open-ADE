"""Source-relative lifecycle envelopes for historical exchanges."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection

from ..errors import RuntimeValidationError
from .metadata import (
    memory_facts,
    memory_revision_predecessors,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
)

# Probe limits are frozen with the H1 fixture. Exceeding lineage limits omits the
# entire exchange, so a compact packet cannot erase a material transition.
MAX_LINKS_PER_EXCHANGE = 8
MAX_REVISIONS_PER_FACT = 32
MAX_EDGES_PER_FACT = 48


def source_message(row: dict[str, Any], prefix: str) -> dict[str, Any]:
    return {
        "id": str(row[f"{prefix}_id"]),
        "role": prefix,
        "content": row[f"{prefix}_content"],
        "content_sha256": row[f"{prefix}_sha256"],
        "created_at": row[f"{prefix}_created_at"],
        "sequence": int(row[f"{prefix}_sequence"]),
    }


def _linked_path(
    origin_id: str,
    current_id: str,
    revisions: list[dict[str, Any]],
    edges: list[tuple[str, str]],
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]] | None:
    by_id = {str(revision["id"]): revision for revision in revisions}
    if origin_id not in by_id or current_id not in by_id:
        return None
    successors: dict[str, set[str]] = defaultdict(set)
    predecessors: dict[str, set[str]] = defaultdict(set)
    for newer, older in edges:
        if newer not in by_id or older not in by_id:
            return None
        successors[older].add(newer)
        predecessors[newer].add(older)

    def closure(start: str, adjacency: dict[str, set[str]]) -> set[str]:
        found, pending = set(), [start]
        while pending:
            node = pending.pop()
            if node not in found:
                found.add(node)
                pending.extend(adjacency[node] - found)
        return found

    relevant = closure(origin_id, successors) & closure(current_id, predecessors)
    if current_id not in relevant:
        return None
    path_revisions = sorted(
        (by_id[node] for node in relevant),
        key=lambda revision: (int(revision["fact_version"]), str(revision["id"])),
    )
    path_edges = sorted(
        (newer, older)
        for newer, older in edges
        if newer in relevant and older in relevant
    )
    return path_revisions, path_edges


async def _fact_lineage(
    connection: AsyncConnection,
    fact_id: str,
    *,
    workspace_id: str,
    subject_id: str,
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]] | None:
    rows = (
        (
            await connection.execute(
                select(
                    memory_revisions.c.id,
                    memory_revisions.c.fact_version,
                    memory_revisions.c.operation,
                    memory_revisions.c.reason,
                    memory_revisions.c.created_at,
                )
                .where(
                    memory_revisions.c.fact_id == fact_id,
                    memory_revisions.c.workspace_id == workspace_id,
                    memory_revisions.c.subject_id == subject_id,
                )
                .order_by(memory_revisions.c.fact_version, memory_revisions.c.id)
                .limit(MAX_REVISIONS_PER_FACT + 1)
            )
        )
        .mappings()
        .all()
    )
    if len(rows) > MAX_REVISIONS_PER_FACT:
        return None
    revisions = [dict(row) for row in rows]
    ids = [revision["id"] for revision in revisions]
    if not ids:
        return None
    edge_rows = (
        await connection.execute(
            select(
                memory_revision_predecessors.c.revision_id,
                memory_revision_predecessors.c.predecessor_revision_id,
            )
            .where(memory_revision_predecessors.c.revision_id.in_(ids))
            .order_by(
                memory_revision_predecessors.c.revision_id,
                memory_revision_predecessors.c.predecessor_revision_id,
            )
            .limit(MAX_EDGES_PER_FACT + 1)
        )
    ).all()
    if len(edge_rows) > MAX_EDGES_PER_FACT:
        return None
    return revisions, [(str(newer), str(older)) for newer, older in edge_rows]


async def read_history_annotations(
    connection: AsyncConnection,
    exchange: dict[str, Any],
    *,
    workspace_id: str,
    subject_id: str,
    purpose: str,
) -> dict[str, Any] | None:
    source_ids = [message["id"] for message in exchange["messages"]]
    rows = (
        (
            await connection.execute(
                select(
                    memory_revision_sources.c.message_id,
                    memory_revision_sources.c.start_char,
                    memory_revision_sources.c.end_char,
                    memory_revision_sources.c.quote,
                    memory_revision_sources.c.message_sha256,
                    memory_revision_sources.c.authority_role,
                    memory_revision_sources.c.revision_id,
                    memory_facts.c.id.label("fact_id"),
                    memory_facts.c.workspace_id.label("fact_workspace_id"),
                    memory_facts.c.subject_id.label("fact_subject_id"),
                    memory_facts.c.fact_type,
                    memory_facts.c.qualifier,
                    memory_facts.c.value,
                    memory_facts.c.status,
                    memory_facts.c.current_revision_id,
                    memory_revisions.c.workspace_id.label("revision_workspace_id"),
                    memory_revisions.c.subject_id.label("revision_subject_id"),
                    memory_subjects.c.purpose.label("subject_purpose"),
                )
                .select_from(memory_revision_sources)
                .join(
                    memory_revisions,
                    memory_revisions.c.id == memory_revision_sources.c.revision_id,
                )
                .join(memory_facts, memory_facts.c.id == memory_revisions.c.fact_id)
                .join(
                    memory_subjects, memory_subjects.c.id == memory_facts.c.subject_id
                )
                .where(memory_revision_sources.c.message_id.in_(source_ids))
                .order_by(
                    memory_revision_sources.c.message_id,
                    memory_revision_sources.c.start_char,
                    memory_revision_sources.c.id,
                )
                .limit(MAX_LINKS_PER_EXCHANGE + 1)
            )
        )
        .mappings()
        .all()
    )
    if len(rows) > MAX_LINKS_PER_EXCHANGE:
        return None
    by_message = {message["id"]: message for message in exchange["messages"]}
    fact_cache: dict[
        str, tuple[list[dict[str, Any]], list[tuple[str, str]]] | None
    ] = {}
    links = []
    facts: dict[str, dict[str, Any]] = {}
    revision_records: dict[str, dict[str, Any]] = {}
    predecessor_edges: set[tuple[str, str]] = set()
    for row in rows:
        link = dict(row)
        if (
            str(link["fact_workspace_id"]) != workspace_id
            or str(link["revision_workspace_id"]) != workspace_id
            or str(link["fact_subject_id"]) != subject_id
            or str(link["revision_subject_id"]) != subject_id
            or link["subject_purpose"] != purpose
        ):
            raise RuntimeValidationError("historical source crosses memory boundary")
        message = by_message[str(link["message_id"])]
        content = message["content"]
        if (
            link["message_sha256"] != message["content_sha256"]
            or hashlib.sha256(content.encode()).hexdigest() != message["content_sha256"]
            or content[link["start_char"] : link["end_char"]] != link["quote"]
            or (link["authority_role"] == "assistant_referent")
            != (message["role"] == "assistant")
        ):
            raise RuntimeValidationError(
                "historical source span failed integrity check"
            )
        fact_id = str(link["fact_id"])
        if fact_id not in fact_cache:
            fact_cache[fact_id] = await _fact_lineage(
                connection, fact_id, workspace_id=workspace_id, subject_id=subject_id
            )
        lineage = fact_cache[fact_id]
        if lineage is None or link["current_revision_id"] is None:
            return None
        path = _linked_path(
            str(link["revision_id"]), str(link["current_revision_id"]), *lineage
        )
        if path is None:
            return None
        revisions, edges = path
        for revision in revisions:
            revision_records[str(revision["id"])] = {
                "id": str(revision["id"]),
                "fact_id": fact_id,
                "fact_version": int(revision["fact_version"]),
                "operation": revision["operation"],
                "reason": revision["reason"],
                "status_after": link["status"]
                if str(revision["id"]) == str(link["current_revision_id"])
                else None,
                "created_at": revision["created_at"],
            }
        predecessor_edges.update(edges)
        facts[fact_id] = {
            "id": fact_id,
            "current_revision_id": str(link["current_revision_id"]),
            "fact_type": link["fact_type"],
            "qualifier": link["qualifier"],
            "status": link["status"],
            "value": link["value"] if link["status"] == "active" else None,
        }
        links.append(
            {
                "message_id": str(link["message_id"]),
                "span": [int(link["start_char"]), int(link["end_char"])],
                "quote": link["quote"],
                "authority_role": link["authority_role"],
                "origin_revision_id": str(link["revision_id"]),
                "fact_id": fact_id,
            }
        )
    return {
        "links": links,
        "facts": sorted(facts.values(), key=lambda fact: fact["id"]),
        "revisions": sorted(
            revision_records.values(),
            key=lambda revision: (
                revision["fact_id"],
                revision["fact_version"],
                revision["id"],
            ),
        ),
        "predecessor_edges": sorted(predecessor_edges),
    }
