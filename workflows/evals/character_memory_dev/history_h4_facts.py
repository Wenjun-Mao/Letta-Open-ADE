"""Source-linked H4 fact transitions and operator causation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import insert, update

from ade_api.features.agent_runtime.persistence.metadata import (
    memory_actions,
    memory_entities,
    memory_facts,
    memory_revision_predecessors,
    memory_revision_sources,
    memory_revisions,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def selected_transitions(fact: dict, included: set[str], *, full: bool) -> list[dict]:
    return [
        transition
        for transition in fact["transitions"]
        if (transition["source"] is None and full)
        or (
            transition["source"] is not None
            and transition["source"].split(":", 1)[0] in included
        )
    ]


def fixture_fact_created_at(
    first_transition: dict, setup_by_id: dict[str, dict], fact_index: int
) -> datetime:
    """Keep paired fact read order tied to the same source chronology."""
    source = first_transition.get("source")
    if source is None:
        raise ValueError("H4 fact must have a source-linked first transition")
    exchange_id = source.split(":", 1)[0]
    return datetime.fromisoformat(setup_by_id[exchange_id]["assistant_at"]) + timedelta(
        microseconds=fact_index
    )


async def seed_fact_chains(
    connection,
    *,
    case: dict,
    setup: list[dict],
    included: set[str],
    full: bool,
    workspace_id: str,
    subject_id: str,
    subject_entity_id: str,
    exchange_ids: dict[str, str],
    message_ids: dict[str, str],
    token: str,
    generation: int,
) -> tuple[
    dict[str, str], list[tuple[str, str, str, str, str, str | None, str | None]], int
]:
    fact_ids: dict[str, str] = {}
    indexed: list[tuple[str, str, str, str, str, str | None, str | None]] = []
    entity_ids: dict[str, str] = {"subject": str(subject_entity_id)}
    setup_by_id = {exchange["id"]: exchange for exchange in setup}
    for fact_index, fact in enumerate(case["facts"]):
        transitions = selected_transitions(fact, included, full=full)
        if not transitions:
            continue
        entity_key = fact["entity_id"]
        if entity_key not in entity_ids:
            entity_ids[entity_key] = str(uuid4())
            await connection.execute(
                insert(memory_entities).values(
                    id=entity_ids[entity_key],
                    workspace_id=workspace_id,
                    subject_id=subject_id,
                    kind=fact["entity_kind"],
                    label=str(transitions[0]["value"] or entity_key),
                )
            )
        fact_id = str(uuid4())
        fact_ids[fact["id"]] = fact_id
        current = transitions[-1]
        current_value = (
            None
            if current["status"] == "forgotten"
            else next(
                (
                    item["value"]
                    for item in reversed(transitions)
                    if item["value"] is not None
                ),
                None,
            )
        )
        await connection.execute(
            insert(memory_facts).values(
                id=fact_id,
                workspace_id=workspace_id,
                subject_id=subject_id,
                entity_id=entity_ids[entity_key],
                normalized_key=f"{fact['fact_type']}|{entity_key}|{fact.get('qualifier') or ''}",
                fact_type=fact["fact_type"],
                qualifier=fact.get("qualifier"),
                value=current_value,
                status=current["status"],
                assertion_schema_version=2,
                version=len(transitions),
                created_at=fixture_fact_created_at(
                    transitions[0], setup_by_id, fact_index
                ),
            )
        )
        predecessor = None
        last_revision_id = None
        for ordinal, transition in enumerate(transitions, 1):
            revision_id = str(uuid4())
            source = transition["source"]
            action_id = None
            if source is None:
                action_id = str(uuid4())
                await connection.execute(
                    insert(memory_actions).values(
                        id=action_id,
                        workspace_id=workspace_id,
                        subject_id=subject_id,
                        idempotency_key=f"h4-forget-{token}-{fact['id']}",
                        request_sha256=_digest(f"h4-forget-{token}-{fact['id']}"),
                        expected_memory_generation=generation,
                        resulting_memory_generation=generation + 1,
                        targets=[fact_id],
                        revision_ids=[revision_id],
                        outcome="committed",
                        actor_label="H4 fixture operator",
                    )
                )
                generation += 1
            exchange_id = source.split(":", 1)[0] if source else None
            created_at = (
                datetime.fromisoformat(
                    next(item for item in setup if item["id"] == exchange_id)[
                        "assistant_at"
                    ]
                )
                + timedelta(microseconds=ordinal)
                if exchange_id
                else datetime.fromisoformat(setup[-1]["assistant_at"])
                + timedelta(seconds=1)
            )
            await connection.execute(
                insert(memory_revisions).values(
                    id=revision_id,
                    fact_id=fact_id,
                    workspace_id=workspace_id,
                    subject_id=subject_id,
                    operation=transition["operation"],
                    fact_version=ordinal,
                    value=transition["value"],
                    run_id=exchange_ids[exchange_id] if exchange_id else None,
                    action_id=action_id,
                    reason=transition["reason"],
                    created_at=created_at,
                )
            )
            if source:
                quote = transition["source_quote"]
                content = next(item for item in setup if item["id"] == exchange_id)[
                    "user"
                ]
                start = content.index(quote)
                await connection.execute(
                    insert(memory_revision_sources).values(
                        id=str(uuid4()),
                        revision_id=revision_id,
                        message_id=message_ids[source],
                        start_char=start,
                        end_char=start + len(quote),
                        quote=quote,
                        message_sha256=_digest(content),
                        authority_role="user_assertion",
                    )
                )
            if predecessor:
                await connection.execute(
                    insert(memory_revision_predecessors).values(
                        revision_id=revision_id,
                        predecessor_revision_id=predecessor,
                    )
                )
            predecessor = last_revision_id = revision_id
        await connection.execute(
            update(memory_facts)
            .where(memory_facts.c.id == fact_id)
            .values(current_revision_id=last_revision_id)
        )
        if current["status"] != "forgotten":
            indexed.append(
                (
                    fact_id,
                    str(last_revision_id),
                    current["status"],
                    fact["fact_type"],
                    str(current_value),
                    fact.get("qualifier"),
                    fact["id"],
                )
            )
    return fact_ids, indexed, generation
