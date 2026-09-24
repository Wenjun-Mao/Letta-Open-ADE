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
    """Verify every locally reserved request has one successful raw capture."""

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


def mutation_state_matches(cell_id: str, facts: list[dict[str, Any]]) -> bool:
    def matching(fact_type: str, status: str, *terms: str) -> list[dict[str, Any]]:
        return [
            fact
            for fact in facts
            if fact["fact_type"] == fact_type
            and fact["status"] == status
            and any(
                term.casefold() in str(fact.get("value") or "").casefold()
                for term in terms
            )
        ]

    coffee_active = matching("person.preference", "active", "咖啡", "coffee")
    coffee_forgotten = matching("person.preference", "forgotten", "咖啡", "coffee")
    flower_active = matching("person.preference", "active", "花茶", "flower tea")
    relation_active = matching("relationship.person", "active", "小王", "Xiao Wang")
    relation_inactive = matching("relationship.person", "inactive", "小王", "Xiao Wang")
    relation_forgotten = matching(
        "relationship.person", "forgotten", "小王", "Xiao Wang"
    )
    match cell_id:
        case "mutation-preference-add":
            return bool(coffee_active) and not matching(
                "person.preference", "active", "茉莉", "jasmine"
            )
        case "mutation-scoped-addition":
            return (
                bool(coffee_active and flower_active)
                and coffee_active[0]["id"] != flower_active[0]["id"]
            )
        case "mutation-natural-correction":
            roxy = matching("pet.name", "active", "Roxy")
            return (
                bool(roxy)
                and not matching("pet.name", "active", "Rocky")
                and any(
                    any(
                        str(revision.get("reason") or "") == "correct"
                        for revision in fact.get("revisions", [])
                    )
                    for fact in roxy
                )
            )
        case "mutation-end":
            return bool(relation_inactive) and not relation_active
        case "mutation-endorsement":
            husky = matching("pet.breed", "active", "哈士奇", "Husky")
            return any(
                {"user_endorsement", "assistant_referent"}
                <= {
                    source["authority_role"]
                    for revision in fact.get("revisions", [])
                    for source in revision.get("evidence", [])
                }
                for fact in husky
            )
        case "mutation-no-save":
            return (
                bool(coffee_forgotten)
                and not coffee_active
                and bool(
                    matching("person.current_location", "active", "多伦多", "Toronto")
                )
            )
        case "mutation-explicit-removal":
            return bool(matching("person.preference", "forgotten", "奶茶", "milk tea"))
        case "mutation-fresh-restatement":
            return bool(relation_active and relation_forgotten) and all(
                current["id"] != old["id"]
                for current in relation_active
                for old in relation_forgotten
            )
        case _:
            raise ValueError(f"Unknown required mutation: {cell_id}")


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
        if not roles.intersection({"user_assertion", "user_endorsement"}):
            return False, "assistant_only_provenance"
    return True, "verified"
