from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class FixtureError(ValueError):
    pass


@dataclass(frozen=True)
class ExpectedFact:
    key: str
    label: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class ConversationFixture:
    key: str
    description: str
    turns: tuple[str, ...]
    expected_facts: tuple[ExpectedFact, ...]
    forbidden_reply_substrings: tuple[str, ...]
    sha256: str


def load_fixture(path: Path) -> ConversationFixture:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FixtureError(f"Fixture is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise FixtureError("Fixture must be a JSON object")
    turns = _string_tuple(payload.get("turns"))
    expected_facts = tuple(
        _expected_fact(item) for item in _list(payload.get("expected_facts"))
    )
    forbidden = _string_tuple(payload.get("forbidden_reply_substrings"))
    if not turns or not expected_facts or not forbidden:
        raise FixtureError(
            "Fixture must provide turns, expected_facts, and forbidden substrings"
        )
    return ConversationFixture(
        key=_required_string(payload, "key"),
        description=str(payload.get("description") or "").strip(),
        turns=turns,
        expected_facts=expected_facts,
        forbidden_reply_substrings=forbidden,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def fixture_payload(fixture: ConversationFixture) -> dict[str, Any]:
    return {
        "key": fixture.key,
        "description": fixture.description,
        "turns": list(fixture.turns),
        "expected_facts": [
            {"key": item.key, "label": item.label, "aliases": list(item.aliases)}
            for item in fixture.expected_facts
        ],
        "forbidden_reply_substrings": list(fixture.forbidden_reply_substrings),
        "sha256": fixture.sha256,
    }


def score_common_contract(
    *,
    fixture: ConversationFixture,
    turn_records: list[dict[str, Any]],
    observed_memory_values: list[str],
    timeout_seconds: float,
    retry_count: int,
) -> dict[str, Any]:
    replies = [
        reply
        for record in turn_records
        for reply in record.get("assistant_replies", [])
        if isinstance(reply, str) and reply.strip()
    ]
    forbidden_hits = [
        {
            "turn_index": record.get("turn_index"),
            "hits": _forbidden_hits(
                record.get("assistant_replies", []), fixture.forbidden_reply_substrings
            ),
        }
        for record in turn_records
    ]
    forbidden_hits = [item for item in forbidden_hits if item["hits"]]
    memory_text = "\n".join(
        value for value in observed_memory_values if value
    ).casefold()
    facts = [
        {
            "key": fact.key,
            "label": fact.label,
            "matched_aliases": [
                alias for alias in fact.aliases if alias.casefold() in memory_text
            ],
        }
        for fact in fixture.expected_facts
    ]
    missing_facts = [item["key"] for item in facts if not item["matched_aliases"]]
    all_turns_succeeded = len(turn_records) == len(fixture.turns) and all(
        str(record.get("terminal_status") or "") == "succeeded"
        for record in turn_records
    )
    controls_exact = len(turn_records) == len(fixture.turns) and all(
        float(record.get("timeout_seconds", -1)) == timeout_seconds
        and int(record.get("retry_count", -1)) == retry_count
        and int(record.get("transport_attempt_count", 0)) == 1
        and (retry_count != 0 or record.get("attempt_count") in {None, 1})
        for record in turn_records
    )
    checks = {
        "no_forbidden_disclosure": not forbidden_hits,
        "expected_facts_captured": not missing_facts,
        "all_turns_succeeded": all_turns_succeeded,
        "timeout_retry_controls_exact": controls_exact,
    }
    return {
        "pass": all(checks.values()),
        "checks": checks,
        "assistant_reply_count": len(replies),
        "forbidden_hits": forbidden_hits,
        "expected_facts": facts,
        "missing_expected_facts": missing_facts,
        "turn_count": len(turn_records),
        "expected_turn_count": len(fixture.turns),
    }


def _forbidden_hits(replies: object, forbidden: tuple[str, ...]) -> list[str]:
    if not isinstance(replies, list):
        return []
    joined = "\n".join(str(value) for value in replies).casefold()
    return [needle for needle in forbidden if needle.casefold() in joined]


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_tuple(value: object) -> tuple[str, ...]:
    return tuple(str(item).strip() for item in _list(value) if str(item).strip())


def _expected_fact(value: object) -> ExpectedFact:
    if not isinstance(value, dict):
        raise FixtureError("expected_facts entries must be JSON objects")
    aliases = _string_tuple(value.get("aliases"))
    if not aliases:
        raise FixtureError("expected facts must define aliases")
    return ExpectedFact(
        key=_required_string(value, "key"),
        label=str(value.get("label") or value.get("key") or "").strip(),
        aliases=aliases,
    )


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise FixtureError(f"Fixture field '{key}' is required")
    return value
