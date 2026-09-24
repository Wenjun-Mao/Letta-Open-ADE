"""Checkpoint-6 outcome checks and durable, explicitly partial reporting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n"
    ).encode()
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)
    return hashlib.sha256(encoded).hexdigest()


def capture_scope(
    capture_dir: Path,
    scope: Any,
    *,
    generation_start: int = 0,
    embedding_start: int = 0,
) -> list[dict[str, Any]]:
    """Check observed captures; missing evidence makes this evaluation unscorable."""

    captures = []
    for kind, start in (
        ("generation", generation_start),
        ("embedding", embedding_start),
    ):
        used = int(getattr(scope, f"{kind}_used"))
        for number in range(start + 1, used + 1):
            path = capture_dir / f"{scope.name}-{kind}-{number:03d}.json"
            if not path.is_file():
                raise RuntimeError(f"missing {kind} provider capture")
            record = json.loads(path.read_text())
            if (
                record.get("scope") != scope.name
                or record.get("kind") != kind
                or record.get("number") != number
                or record.get("outcome") != "completed"
            ):
                raise RuntimeError(f"failed or invalid {kind} provider capture")
            captures.append(
                {"kind": kind, "number": number, "sha256": sha256_file(path)}
            )
    return captures


def mutation_state_matches(
    cell_id: str,
    facts: list[dict[str, Any]],
    *,
    run_id: str,
    terminal: dict[str, Any],
) -> bool:
    """Require the frozen result and its new, terminal-confirmed revision."""

    if terminal.get("outcome") != "committed":
        return False
    committed_ids = set(map(str, terminal.get("revision_ids", [])))
    if not committed_ids:
        return False

    def has_terms(value: Any, *terms: str) -> bool:
        text = str(value or "").casefold()
        return any(term.casefold() in text for term in terms)

    def matching(fact_type: str, status: str, *terms: str) -> list[dict[str, Any]]:
        return [
            fact
            for fact in facts
            if fact["fact_type"] == fact_type
            and fact["status"] == status
            and has_terms(fact.get("value"), *terms)
        ]

    def new_revisions(fact: dict[str, Any], *operations: str) -> list[dict[str, Any]]:
        return [
            revision
            for revision in fact.get("revisions", [])
            if str(revision.get("run_id")) == run_id
            and str(revision.get("id")) in committed_ids
            and (not operations or revision.get("operation") in operations)
        ]

    coffee_active = matching("person.preference", "active", "咖啡", "coffee")
    coffee_forgotten = matching("person.preference", "forgotten", "咖啡", "coffee")
    flower_active = matching("person.preference", "active", "花茶", "flower tea")
    relation_active = matching("relationship.person", "active", "小王", "Xiao Wang")
    relation_inactive = matching("relationship.person", "inactive", "小王", "Xiao Wang")
    relation_forgotten = matching(
        "relationship.person", "forgotten", "小王", "Xiao Wang"
    )
    milk_active = matching("person.preference", "active", "奶茶", "milk tea")

    match cell_id:
        case "mutation-preference-add":
            return any(
                has_terms(fact["value"], "早上", "morning")
                and new_revisions(fact, "add")
                for fact in coffee_active
            ) and not matching("person.preference", "active", "茉莉", "jasmine")
        case "mutation-scoped-addition":
            return any(
                has_terms(coffee["value"], "早上", "morning")
                and has_terms(flower["value"], "晚上", "evening")
                and coffee["id"] != flower["id"]
                and not new_revisions(coffee)
                and new_revisions(flower, "add")
                for coffee in coffee_active
                for flower in flower_active
            )
        case "mutation-natural-correction":
            for roxy in matching("pet.name", "active", "Roxy"):
                revisions = roxy.get("revisions", [])
                by_id = {str(revision["id"]): revision for revision in revisions}
                for current in new_revisions(roxy, "revise"):
                    if current.get("reason") != "correct":
                        continue
                    predecessors = [
                        by_id.get(str(predecessor))
                        for predecessor in current.get("predecessor_revision_ids", [])
                    ]
                    if any(
                        prior is not None
                        and has_terms(prior.get("value"), "Rocky")
                        and prior.get("operation") == "add"
                        for prior in predecessors
                    ) and any(
                        source.get("authority_role") == "user_assertion"
                        and has_terms(source.get("quote"), "打错", "typo", "wrong")
                        for source in current.get("evidence", [])
                    ):
                        return not matching("pet.name", "active", "Rocky")
            return False
        case "mutation-end":
            return not relation_active and any(
                new_revisions(fact, "end") for fact in relation_inactive
            )
        case "mutation-endorsement":
            roxy_entities = {
                str(fact["entity_id"])
                for fact in matching("pet.name", "active", "Roxy")
                if new_revisions(fact, "add")
            }
            return any(
                str(fact["entity_id"]) in roxy_entities
                and any(
                    {"user_endorsement", "assistant_referent"}
                    <= {
                        source.get("authority_role")
                        for source in revision.get("evidence", [])
                    }
                    for revision in new_revisions(fact, "add")
                )
                for fact in matching("pet.breed", "active", "哈士奇", "Husky")
            )
        case "mutation-no-save":
            return (
                not coffee_active
                and any(new_revisions(fact, "forget") for fact in coffee_forgotten)
                and any(
                    new_revisions(fact, "add")
                    for fact in matching(
                        "person.current_location", "active", "多伦多", "Toronto"
                    )
                )
            )
        case "mutation-explicit-removal":
            return not milk_active and any(
                new_revisions(fact, "forget")
                for fact in matching(
                    "person.preference", "forgotten", "奶茶", "milk tea"
                )
            )
        case "mutation-fresh-restatement":
            return bool(relation_forgotten) and any(
                new_revisions(current, "add")
                and all(current["id"] != old["id"] for old in relation_forgotten)
                for current in relation_active
            )
        case _:
            raise ValueError(f"Unknown required mutation: {cell_id}")


def require_mutation_state(
    cell_id: str,
    *,
    facts: list[dict[str, Any]],
    run_id: str,
    terminal: dict[str, Any],
) -> None:
    if not mutation_state_matches(cell_id, facts, run_id=run_id, terminal=terminal):
        raise RuntimeError("required mutation state did not match committed fixture")


def unrun_after_stop(cells: list[tuple[str, dict, str]], index: int) -> list[str]:
    return [item[0] for item in cells[index + 1 :]]


def stop_campaign_at(
    manifest: dict[str, Any],
    cells: list[tuple[str, dict, str]],
    index: int,
    error: Exception,
) -> str:
    """Record the failed cell and preserve the untouched suffix of the schedule."""

    result = manifest["cells"][-1]
    reason = f"{result['cell']}: {type(error).__name__}: {error}"
    result["status"] = "campaign_stopped"
    result["stop_reason"] = reason
    manifest["unrun"] = unrun_after_stop(cells, index)
    return reason


def verify_attempt_safety(
    *,
    run: dict[str, Any],
    evidence: dict[str, Any],
    facts: list[dict[str, Any]],
) -> tuple[bool, str]:
    terminal = evidence.get("terminal_readback", {})
    outcome = terminal.get("outcome")
    if outcome not in {"committed", "confirmed_rejection"}:
        return False, "unconfirmed_attempt"
    if int(run.get("attempt_count") or 0) != 1 or evidence.get("attempt") != 1:
        return False, "exact_attempt_violation"
    if outcome == "committed" and (
        run.get("status") != "succeeded"
        or len(terminal.get("assistant_message_ids", [])) != 1
    ):
        return False, "atomicity_violation"
    if outcome == "confirmed_rejection" and (
        terminal.get("assistant_message_ids") or terminal.get("revision_ids")
    ):
        return False, "atomicity_violation"
    new_revisions = [
        revision
        for fact in facts
        for revision in fact.get("revisions", [])
        if str(revision.get("run_id")) == str(run["id"])
    ]
    if len(new_revisions) != len(terminal.get("revision_ids", [])):
        return False, "provenance_readback_mismatch"
    for revision in new_revisions:
        roles = {source["authority_role"] for source in revision.get("evidence", [])}
        if not roles.intersection(
            {"user_assertion", "user_endorsement", "user_resolution"}
        ):
            return False, "assistant_only_provenance"
    return True, "verified"
