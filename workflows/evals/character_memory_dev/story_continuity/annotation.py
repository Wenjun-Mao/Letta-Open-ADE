"""Pre-outcome human annotation of actual delivered details, never model input."""

import json

from .schedule import digest


def freeze_annotation(
    *,
    run_id: str,
    reply: str,
    committed: bool,
    at_turn: int,
    observed_turns: list[int],
    quotes: list[str],
    rationale: str,
    replacement_suggestion: str | None = None,
) -> dict:
    if at_turn not in {1, 3} or not observed_turns or max(observed_turns) != at_turn:
        raise ValueError("Annotate origin/detail before any later outcome is observed")
    if not committed or not reply or not rationale.strip():
        raise ValueError("Annotation requires delivered origin and human rationale")
    if not quotes or any(not quote.strip() or quote not in reply for quote in quotes):
        raise ValueError(
            "Annotate exact actual reply quotes, not evaluator-invented details"
        )
    if len(quotes) != len(set(quotes)):
        raise ValueError("Duplicate annotation quote")
    if at_turn == 1 and not replacement_suggestion:
        raise ValueError("Predeclare the rewrite suggestion at origin annotation")
    payload = {
        "run_id": run_id,
        "reply_sha256": digest(reply.encode()),
        "at_turn": at_turn,
        "quotes": quotes,
        "rationale": rationale,
        "replacement_suggestion": replacement_suggestion,
    }
    return {
        "annotation": payload,
        "sha256": digest(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        ),
    }


def check_annotation(
    record: dict, *, expected_sha256: str, run_id: str, reply: str
) -> dict:
    payload = record["annotation"]
    actual = digest(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode())
    if (
        actual != expected_sha256
        or actual != record["sha256"]
        or payload["run_id"] != run_id
        or payload["reply_sha256"] != digest(reply.encode())
    ):
        raise ValueError("Stale/corrupt annotation or changed delivered origin")
    return payload
