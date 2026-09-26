"""Independent H4 readback and exact paired base-packet comparisons."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ade_api.features.agent_runtime.history_admission import HISTORY_DATA_INSTRUCTION
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_entities,
    memory_facts,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
)

from .natural_live_results import sha256_file


_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def capture_receipts(capture_dir: Path, scope: Any) -> list[dict[str, Any]]:
    receipts = []
    for kind in ("generation", "embedding"):
        for number in range(1, int(getattr(scope, f"{kind}_used")) + 1):
            path = capture_dir / f"{scope.name}-{kind}-{number:03d}.json"
            if not path.is_file():
                receipts.append({"kind": kind, "number": number, "status": "missing"})
                continue
            capture = json.loads(path.read_text())
            receipts.append(
                {
                    "kind": kind,
                    "number": number,
                    "status": capture.get("outcome", "invalid"),
                    "sha256": sha256_file(path),
                }
            )
    return receipts


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return _UUID.sub("<fixture-id>", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    return value


def paired_base_packet(attempt: dict[str, Any]) -> dict[str, Any] | None:
    generation = attempt.get("generation", {})
    reviewer = attempt.get("reviewer_request", {})
    if "messages" not in generation or "messages" not in reviewer:
        return None
    messages = deepcopy(generation["messages"])
    system = str(messages[0]["content"])
    history_section = "\n\n" + HISTORY_DATA_INSTRUCTION
    if history_section not in system:
        raise ValueError("H-capable generation packet lacks its history boundary")
    messages[0]["content"] = system.split(history_section, 1)[0]
    reviewer_messages = deepcopy(reviewer["messages"])
    reviewer_packet = json.loads(reviewer_messages[1]["content"])
    reviewer_packet.pop("history", None)
    reviewer_packet.pop("candidate_visible_reply", None)
    return _normalize(
        {
            "generation_messages": messages,
            "generation_input_limit": generation.get("input_limit"),
            "reviewer_system": reviewer_messages[0]["content"],
            "reviewer_packet": reviewer_packet,
            "reviewer_max_tokens": reviewer.get("max_tokens"),
            "reviewer_response_format": reviewer.get("response_format"),
        }
    )


async def mutation_snapshot(engine, subject_id: str) -> dict[str, Any]:
    async with engine.connect() as connection:
        generation = await connection.scalar(
            select(memory_subjects.c.memory_generation).where(
                memory_subjects.c.id == subject_id
            )
        )
        entity_ids = set(
            (
                await connection.execute(
                    select(memory_entities.c.id).where(
                        memory_entities.c.subject_id == subject_id
                    )
                )
            ).scalars()
        )
        revision_ids = set(
            (
                await connection.execute(
                    select(memory_revisions.c.id).where(
                        memory_revisions.c.subject_id == subject_id
                    )
                )
            ).scalars()
        )
    return {
        "memory_generation": int(generation),
        "entity_ids": {str(item) for item in entity_ids},
        "revision_ids": {str(item) for item in revision_ids},
    }


async def mutation_delta(
    engine, *, subject_id: str, run_id: str, before: dict[str, Any]
) -> dict[str, Any]:
    after = await mutation_snapshot(engine, subject_id)
    async with engine.connect() as connection:
        rows = (
            (
                await connection.execute(
                    select(
                        memory_revisions.c.id,
                        memory_revisions.c.fact_id,
                        memory_revisions.c.operation,
                        memory_revisions.c.reason,
                        memory_revisions.c.value,
                        memory_facts.c.fact_type,
                        memory_facts.c.qualifier,
                        memory_facts.c.entity_id,
                    )
                    .join(memory_facts, memory_facts.c.id == memory_revisions.c.fact_id)
                    .where(memory_revisions.c.run_id == run_id)
                    .order_by(memory_revisions.c.id)
                )
            )
            .mappings()
            .all()
        )
        revisions = []
        for row in rows:
            sources = (
                (
                    await connection.execute(
                        select(
                            memory_revision_sources.c.quote,
                            memory_revision_sources.c.authority_role,
                        ).where(memory_revision_sources.c.revision_id == row["id"])
                    )
                )
                .mappings()
                .all()
            )
            revisions.append(
                {
                    **{
                        key: str(value)
                        if key in {"id", "fact_id", "entity_id"}
                        else value
                        for key, value in row.items()
                    },
                    "sources": [dict(item) for item in sources],
                }
            )
    new_revision_ids = after["revision_ids"] - before["revision_ids"]
    return {
        "generation_advance": after["memory_generation"] - before["memory_generation"],
        "entity_additions": sorted(after["entity_ids"] - before["entity_ids"]),
        "revision_count": len(new_revision_ids),
        "run_revisions": revisions,
        "other_revision_ids": sorted(
            new_revision_ids - {item["id"] for item in revisions}
        ),
    }


def compare_expected_delta(
    observed: dict[str, Any],
    expected: dict[str, Any],
    *,
    seeded_fact_ids: dict[str, str],
    subject_entity_id: str,
) -> list[str]:
    issues = []
    if observed["generation_advance"] != expected["expected_generation_advance"]:
        issues.append("memory_generation")
    if observed["revision_count"] != expected["expected_revision_count"]:
        issues.append("revision_count")
    if len(observed["entity_additions"]) != len(expected["expected_entity_additions"]):
        issues.append("entity_additions")
    if observed["other_revision_ids"]:
        issues.append("non_target_revision")
    remaining = list(observed["run_revisions"])
    for item in expected["expected_delta"]:
        kind = item["kind"]
        candidates = [
            row
            for row in remaining
            if row["operation"]
            == ("add" if kind in {"subject_add", "related_add"} else kind)
            and (
                kind in {"subject_add", "related_add"}
                or row["fact_id"] == seeded_fact_ids.get(item["fact_id"])
            )
            and (
                kind not in {"subject_add", "related_add"}
                or (
                    row["fact_type"] == item["fact_type"]
                    and row["qualifier"] == item["qualifier"]
                    and (row["entity_id"] == subject_entity_id)
                    == (kind == "subject_add")
                )
            )
            and row["reason"] == item.get("reason")
            and row["value"] == item.get("value")
            and any(
                source["quote"] == item["source_quote"]
                and source["authority_role"] == "user_assertion"
                for source in row["sources"]
            )
        ]
        if len(candidates) != 1:
            issues.append(f"write:{item['fact_id']}")
        else:
            remaining.remove(candidates[0])
    if remaining:
        issues.append("extra_target_write")
    return issues
