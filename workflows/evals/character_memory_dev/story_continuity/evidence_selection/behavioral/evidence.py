"""Validate captured evidence independently of permission to continue execution."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from .contracts import ARMS, ROUTE, digest, load_prepared, review_request
from .receipts import read, require_private

STAGES = tuple(
    f"{arm}.{stage}" for arm, _ in ARMS for stage in ("generation", "reviewer")
)


def response_object(raw: dict) -> dict:
    value = json.loads(base64.b64decode(raw["body_base64"], validate=True))
    if not isinstance(value, dict):
        raise ValueError("Response must be an object")
    return value


def visible(raw: dict) -> str:
    response = response_object(raw)
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("Expected one choice")
    choice = choices[0]
    message = choice.get("message", {})
    if choice.get("finish_reason") != "stop":
        raise ValueError("Non-stop/truncated output")
    if (
        message.get("role") != "assistant"
        or message.get("tool_calls")
        or message.get("function_call")
        or message.get("refusal")
    ):
        raise ValueError("Tool/refusal/non-assistant output")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Empty/nontext visible output")
    return content


def classify(raw: dict, stage: str) -> dict:
    if not 200 <= raw["status"] < 300:
        return {"disposition": "infrastructure_stop", "reason": "HTTP failure"}
    try:
        content = visible(raw)
        if stage == "reviewer":
            if not isinstance(json.loads(content), dict):
                raise ValueError("Reviewer JSON must be an object")
            return {
                "disposition": "captured",
                "validation": "pending_runtime_schema_binding_audit",
            }
        return {"disposition": "captured", "visible_reply_sha256": digest(content)}
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return {"disposition": "complete_unusable", "reason": str(exc)}


def status(directory: Path) -> dict:
    rows = {}
    for key in STAGES:
        outcome = directory / f"{key}.outcome.json"
        intent = directory / f"{key}.intent.json"
        rows[key] = (
            read(outcome)["classification"]
            if outcome.exists()
            else {"disposition": "uncertain_consumed" if intent.exists() else "unrun"}
        )
    return rows


def validate_receipts(directory: Path, packets: list) -> str | None:
    """Validate one prefix, returning its terminal state without authorizing a send.

    A bound intent without an outcome is an uncertain consumed attempt. Its raw
    file may be absent or incomplete and is not interpreted as an outcome. Later
    artifacts remain invalid. Complete outcomes and their raw originals must
    match exactly, including the final transport/HTTP stop outcome.
    """
    frontier = False
    terminal = None
    freeze = read(directory / "freeze.json")
    for packet in packets:
        generation = None
        for stage in ("generation", "reviewer"):
            key = f"{packet['arm']}.{stage}"
            intent_path, outcome_path, raw_path = (
                directory / f"{key}.{suffix}.json"
                for suffix in ("intent", "outcome", "raw")
            )
            present = intent_path.exists() or outcome_path.exists() or raw_path.exists()
            if not present:
                frontier = True
                continue
            if frontier or terminal:
                raise ValueError("Non-prefix or post-stop receipts")
            outcome = read(outcome_path) if outcome_path.exists() else None
            if outcome and outcome["classification"]["disposition"] == "skipped":
                if (
                    stage != "reviewer"
                    or intent_path.exists()
                    or raw_path.exists()
                    or not generation
                    or generation["classification"]["disposition"]
                    != "complete_unusable"
                ):
                    raise ValueError("Invalid skipped reviewer receipt")
                continue
            if not intent_path.exists():
                raise ValueError("Outcome/raw capture without dispatch intent")
            intent = read(intent_path)
            if stage == "reviewer" and (
                not generation
                or generation["classification"]["disposition"] != "captured"
            ):
                raise ValueError("Reviewer intent without usable generation")
            request = (
                packet["generation"]
                if stage == "generation"
                else review_request(packet, visible(generation["raw"]))
            )
            if intent["request"] != request or intent["request_sha256"] != digest(
                request
            ):
                raise ValueError("Captured request/source/reply drift")
            if (
                intent["source"] != freeze["source"]
                or intent["route"] != ROUTE
                or intent["stage"] != key
                or intent["deadline_seconds"] != 180
                or intent["attempt"] != 1
            ):
                raise ValueError("Captured intent binding drift")
            if outcome is None:
                terminal = "uncertain_consumed"
                continue
            if outcome["intent_sha256"] != digest(intent):
                raise ValueError("Captured intent/outcome drift")
            disposition = outcome["classification"]["disposition"]
            if disposition == "transport_stop":
                if (
                    raw_path.exists()
                    or "raw" in outcome
                    or not outcome["classification"].get("error_type")
                ):
                    raise ValueError("Invalid transport stop receipt")
                terminal = "transport_stop"
            else:
                if not raw_path.exists() or read(raw_path) != outcome.get("raw"):
                    raise ValueError("Original raw capture drift")
                if classify(outcome["raw"], stage) != outcome["classification"]:
                    raise ValueError("Captured classification drift")
                if disposition == "infrastructure_stop":
                    terminal = "infrastructure_stop"
            if stage == "generation":
                generation = outcome
    stop_path = directory / "stop.json"
    if stop_path.exists():
        stop = read(stop_path)
        reasons = {
            "catalog_preflight_failure",
            "source_preflight_failure",
            "source_drift",
            "actual_reviewer_capacity",
        }
        if terminal or stop.get("reason") not in reasons:
            raise ValueError("Invalid or duplicate terminal stop receipt")
        if stop["stage"] in STAGES:
            if stop["reason"] == "catalog_preflight_failure":
                raise ValueError("Catalog stop bound to chat stage")
            for key in STAGES[STAGES.index(stop["stage"]) :]:
                if any(
                    (directory / f"{key}.{suffix}.json").exists()
                    for suffix in ("intent", "outcome", "raw")
                ):
                    raise ValueError("Post-preflight-stop receipts")
        elif (
            stop["reason"] != "catalog_preflight_failure"
            or not (directory / f"{stop['stage']}.outcome.json").exists()
            or read(directory / f"{stop['stage']}.outcome.json").get("disposition")
            != "preflight_stop"
        ):
            raise ValueError("Invalid preflight stop binding")
        terminal = terminal or "preflight_stop"
    return terminal


def audit(directory: Path, validator) -> dict:
    directory = require_private(directory)
    prepared = load_prepared()
    terminal = validate_receipts(directory, prepared["packets"])
    results = {}
    for arm, _ in ARMS:
        generation_path = directory / f"{arm}.generation.outcome.json"
        reviewer_path = directory / f"{arm}.reviewer.outcome.json"
        if (
            not reviewer_path.exists()
            or read(reviewer_path)["classification"]["disposition"] != "captured"
        ):
            results[arm] = "unrun_or_unusable"
            continue
        reply = visible(read(generation_path)["raw"])
        payload = json.loads(visible(read(reviewer_path)["raw"]))
        try:
            validator(arm, reply, payload)
            results[arm] = (
                "schema_source_binding_valid_not_factual_judgment_or_persistence"
            )
        except Exception as exc:
            if getattr(exc, "detail_code", None) == "natural_memory_reply_conflict":
                results[arm] = "source_bound_conflict_observation_not_independent_truth"
            else:
                results[arm] = {
                    "invalid": type(exc).__name__,
                    "detail_code": getattr(exc, "detail_code", None),
                }
    return {
        "assessments": results,
        "stages": status(directory),
        "execution_state": terminal
        or (
            "complete"
            if all((directory / f"{key}.outcome.json").exists() for key in STAGES)
            else "captured_prefix"
        ),
        "stop": read(directory / "stop.json")
        if (directory / "stop.json").exists()
        else None,
    }
