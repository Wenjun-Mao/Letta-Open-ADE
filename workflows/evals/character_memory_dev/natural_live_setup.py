"""Source-linked, synthetic PostgreSQL setup for frozen live comparison cells."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import insert, select

from ade_api.features.agent_runtime.embeddings import (
    EmbeddingClient,
    NATURAL_RETRIEVAL_POLICY_VERSION,
    embedding_space_key,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_embeddings,
    memory_facts,
    memory_revisions,
)

from .natural_state_packet_support import seed_state_packet


@dataclass(frozen=True)
class SeededCell:
    history_message_ids: tuple[str, ...]
    fact_ids: tuple[str, ...]
    scripted_setup: tuple[str, ...]


def _fact(
    fact_type: str,
    value: str,
    assertion: str,
    *,
    qualifier: str | None = None,
    status: str = "active",
    transitions: list[dict] | None = None,
) -> dict:
    return {
        "fact_type": fact_type,
        "qualifier": qualifier,
        "value": value,
        "status": status,
        "assertion": assertion,
        "transitions": transitions or [],
        "index_prior": False,
    }


def _relationship(branch: dict, *, status: str) -> dict:
    turns = {label: content for label, _, content in branch["turns"]}
    transitions = []
    if status in {"inactive", "forgotten"}:
        transitions.append(
            {"operation": "end", "reason": "ended", "source": turns["u2"]}
        )
    if status == "forgotten":
        transitions.append(
            {"operation": "forget", "reason": "forgotten", "source": turns["u3"]}
        )
    first = turns.get("u1") or turns.get("u0")
    return _fact(
        "relationship.person",
        "小王",
        first,
        qualifier="partner",
        status=status,
        transitions=transitions,
    )


def facts_for_cell(cell: dict, branch: dict) -> list[dict]:
    turns = {label: content for label, _, content in branch["turns"]}
    cell_id = cell["id"]
    facts: list[dict] = []
    if cell_id in {"mutation-scoped-addition", "mutation-no-save"}:
        facts.append(
            _fact(
                "person.preference",
                "早上喜欢喝咖啡",
                turns.get("u0") or turns["u1"],
                qualifier="drink",
            )
        )
    elif cell_id == "mutation-explicit-removal":
        facts.append(
            _fact("person.preference", "喜欢奶茶", turns["u1"], qualifier="drink")
        )
    elif cell_id == "mutation-natural-correction":
        facts.append(_fact("pet.name", "Rocky", turns["u1"]))
    elif cell_id in {"mutation-end", "response-ended-recall"}:
        facts.append(
            _relationship(
                branch, status="active" if cell_id == "mutation-end" else "inactive"
            )
        )
    elif cell_id in {"mutation-fresh-restatement", "summary-end-forget"}:
        facts.append(_relationship(branch, status="forgotten"))
    elif cell_id in {"response-breakup", "summary-after-change"}:
        facts.append(_relationship(branch, status="inactive"))
    elif cell_id == "response-residence-visit":
        facts.append(_fact("person.current_location", "多伦多", turns["u1"]))
    count = int(cell.get("record_count", 0))
    for index in range(count):
        value = (
            f"M{index}" if cell_id.startswith("pressure-") else f"unrelated-{index:03d}"
        ) + " x" * 15
        facts.append(
            _fact(
                "person.preference",
                value,
                f"For unrelated topic {index:03d}, I prefer {value}.",
                qualifier="other",
                status="inactive" if index % 3 == 0 else "active",
                transitions=(
                    [
                        {
                            "operation": "end",
                            "reason": "ended",
                            "source": f"I no longer prefer {value} for unrelated topic {index:03d}.",
                        }
                    ]
                    if index % 3 == 0
                    else []
                ),
            )
        )
    return facts


def history_for_cell(
    cell: dict, branch: dict
) -> tuple[list[tuple[str, str]], tuple[str, ...]]:
    cutoff = next(
        index for index, turn in enumerate(branch["turns"]) if turn[0] == cell["cutoff"]
    )
    previous = branch["turns"][:cutoff]
    pairs: list[tuple[str, str]] = []
    scripted: list[str] = []
    pending_user: str | None = None
    for label, role, content in previous:
        if role == "operator":
            continue
        if role == "user":
            if pending_user is not None:
                pairs.append((pending_user, "收到。"))
                scripted.append("acknowledgement for an unpaired fixture user turn")
            pending_user = content
        elif pending_user is None:
            pairs.append(("你好。", content))
            scripted.append(f"neutral lead-in for assistant referent {label}")
        else:
            pairs.append((pending_user, content))
            pending_user = None
        if cell["id"].startswith("summary-") and label in {"a1", "u1"}:
            # Native compaction requires more than 64 prior messages. These
            # neutral exchanges are identical in all three variant setups.
            if cell["id"] == "summary-after-change" and label == "a1":
                pairs.extend(_neutral_pairs(31))
                scripted.append("31 neutral complete exchanges after a1")
            if cell["id"] == "summary-end-forget" and label == "u1":
                if pending_user is not None:
                    pairs.append((pending_user, "收到。"))
                    pending_user = None
                pairs.extend(_neutral_pairs(31))
                scripted.append("31 neutral complete exchanges after u1")
    if pending_user is not None:
        pairs.append((pending_user, "收到。"))
        scripted.append("acknowledgement for the final prior user turn")
    return pairs, tuple(scripted)


def _neutral_pairs(count: int) -> list[tuple[str, str]]:
    return [
        (
            f"Neutral synthetic topic {index:02d}?",
            f"Neutral synthetic reply {index:02d}.",
        )
        for index in range(count)
    ]


async def seed_live_cell(
    engine,
    session: dict,
    *,
    cell: dict,
    branch: dict,
    token: str,
    transport,
    embedding_model: str,
    summary_content: str = "",
    summary_through_sequence: int = 2,
) -> SeededCell:
    history, scripted = history_for_cell(cell, branch)
    facts = facts_for_cell(cell, branch)
    if not history and not facts and not summary_content:
        return SeededCell((), (), scripted)
    deployment = next(
        snapshot
        for snapshot in session["agent_definition"]["deployments"]
        if snapshot["role"] == "retriever"
    )
    seeded = await seed_state_packet(
        engine,
        session,
        token=token,
        history=history,
        facts=facts,
        summary_content=summary_content,
        summary_through_sequence=summary_through_sequence,
        summary_model_key="deepseek::deepseek-flash",
        summary_model_fingerprint=next(
            snapshot["fingerprint"]
            for snapshot in session["agent_definition"]["deployments"]
            if snapshot["role"] == "conversation"
        ),
    )
    fact_ids = tuple(seeded["fact_ids"])
    if fact_ids:
        async with engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        select(memory_facts).where(memory_facts.c.id.in_(fact_ids))
                    )
                )
                .mappings()
                .all()
            )
        by_id = {str(row["id"]): row for row in rows}
        ordered = [by_id[fact_id] for fact_id in fact_ids]
        documents = [
            f"lifecycle_status: {row['status']}\n"
            f"fact_type: {row['fact_type']}\n"
            f"qualifier: {row['qualifier'] or ''}\n"
            f"value: {row['value']}"
            for row in ordered
        ]
        vectors = await EmbeddingClient(transport).embed(
            model_key=embedding_model, inputs=documents, timeout_seconds=180
        )
        expected_dimensions = deployment["fingerprint_payload"]["sampling_settings"][
            "dimensions"
        ]
        if any(len(vector) != expected_dimensions for vector in vectors):
            raise RuntimeError("synthetic setup embedding dimensions differ")
        space_key = embedding_space_key(deployment)
        async with engine.begin() as connection:
            for row, vector in zip(ordered, vectors, strict=True):
                revision_id = row["current_revision_id"]
                if row["status"] == "forgotten":
                    revision_id = await connection.scalar(
                        select(memory_revisions.c.id).where(
                            memory_revisions.c.fact_id == row["id"],
                            memory_revisions.c.fact_version == 1,
                        )
                    )
                await connection.execute(
                    insert(memory_embeddings).values(
                        id=str(uuid4()),
                        workspace_id=row["workspace_id"],
                        subject_id=row["subject_id"],
                        fact_id=row["id"],
                        revision_id=revision_id,
                        model_fingerprint=space_key,
                        dimensions=expected_dimensions,
                        normalized=True,
                        retrieval_policy_version=NATURAL_RETRIEVAL_POLICY_VERSION,
                        embedding=vector,
                    )
                )
    return SeededCell(
        history_message_ids=tuple(seeded["history_message_ids"]),
        fact_ids=fact_ids,
        scripted_setup=scripted,
    )
