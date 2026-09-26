"""Small fail-closed checks for the frozen historical probe scripts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ade_api.features.agent_runtime.fact_registry import (
    fact_type_spec,
    normalize_qualifier,
)
from ade_api.features.agent_runtime.natural_memory_review import (
    NaturalReviewDecision,
    bind_exact_quote,
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _decision_payload(
    kind: str, fact: dict[str, Any], value: str | None, reason: str | None, quote: str
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": kind,
        "evidence": {"mode": "direct", "current_quote": quote},
    }
    if kind in {"subject_add", "related_add"}:
        payload.update(
            fact_type=fact["fact_type"], qualifier=fact["qualifier"], value=value
        )
        if kind == "related_add":
            payload["entity_ref"] = fact["entity_id"]
    else:
        payload["target"] = "F1"
        if kind in {"revise", "reassert"}:
            payload["value"] = value
        if kind in {"revise", "end"}:
            payload["reason"] = reason
    return payload


def _validate_write(
    kind: str, fact: dict[str, Any], value: str | None, reason: str | None, quote: str
) -> None:
    try:
        NaturalReviewDecision.model_validate(
            {"decisions": [_decision_payload(kind, fact, value, reason, quote)]}
        )
    except ValueError as exc:
        raise ValueError(f"invalid natural write {kind}/{reason}: {exc}") from exc


def _validate_delta(
    delta: list[dict[str, Any]],
    user_text: str,
    facts: dict[str, dict[str, Any]],
    *,
    generation_advance: int,
    revision_count: int,
    entity_additions: list[str],
) -> None:
    _require(
        generation_advance == int(bool(delta)),
        "generation delta disagrees with complete write list",
    )
    _require(entity_additions == [], "this probe freezes no new entity additions")
    _require(
        revision_count == len(delta),
        "revision count disagrees with complete write list",
    )
    seen: set[str] = set()
    for item in delta:
        fact_id = item["fact_id"]
        _require(fact_id not in seen, "one fact can change only once per turn")
        seen.add(fact_id)
        kind = item["kind"]
        expected_keys = (
            {
                "kind",
                "fact_id",
                "entity_id",
                "fact_type",
                "qualifier",
                "value",
                "source_quote",
            }
            if kind in {"subject_add", "related_add"}
            else {"kind", "fact_id", "reason", "value", "source_quote"}
            if kind == "revise"
            else {"kind", "fact_id", "reason", "source_quote"}
            if kind == "end"
            else None
        )
        _require(
            expected_keys is not None and set(item) == expected_keys,
            "expected delta has an unsupported or incomplete write shape",
        )
        quote = item["source_quote"]
        bind_exact_quote(
            {"id": "current", "content": user_text}, quote, "user_assertion"
        )
        if kind in {"subject_add", "related_add"}:
            _require(fact_id not in facts, "new fact ID collides with seeded fact")
            fact = item
            spec = fact_type_spec(fact["fact_type"])
            normalize_qualifier(spec, fact["qualifier"])
            _require(
                (spec.entity_kind == "subject") == (kind == "subject_add"),
                "add operation disagrees with fact entity kind",
            )
            _require(
                item["entity_id"] == "subject"
                if kind == "subject_add"
                else item["entity_id"] != "subject",
                "add entity kind disagrees with operation",
            )
        else:
            _require(fact_id in facts, "write target is not a seeded fact")
            fact = facts[fact_id]
        _validate_write(kind, fact, item.get("value"), item.get("reason"), quote)


def validate_history_cases(contract: dict[str, Any], fixture: dict[str, Any]) -> None:
    """Reject ambiguous chronology, lifecycle recipes and missing finite cells."""
    cases = fixture["cases"]
    _require(
        [case["id"] for case in cases] == [case["id"] for case in contract["cases"]],
        "case schedule differs from frozen contract",
    )
    by_case = {case["id"]: case for case in cases}
    for case in cases:
        exchanges = {exchange["id"]: exchange for exchange in case["setup"]}
        _require(len(exchanges) == len(case["setup"]), "duplicate setup exchange ID")
        last_time: datetime | None = None
        next_sequence: dict[str, int] = {}
        for order, exchange in enumerate(case["setup"], 1):
            _require(
                exchange.get("workspace", "primary") in {"primary", "different"}
                and exchange.get("subject", "primary") in {"primary", "different"}
                and exchange.get("root", "primary") in {"primary", "different"}
                and exchange.get("purpose", "evaluation") in {"evaluation", "preview"}
                and type(exchange.get("version", 1)) is int
                and exchange.get("version", 1) > 0
                and type(exchange.get("archived", False)) is bool,
                "setup scope or version is invalid",
            )
            chat = exchange["chat"]
            expected_sequence = next_sequence.get(chat, 1)
            _require(exchange["order"] == order, "setup commit order changed")
            _require(
                exchange["user_sequence"] == expected_sequence,
                "local user sequence changed",
            )
            _require(
                exchange["assistant_sequence"] == expected_sequence + 1,
                "local assistant sequence changed",
            )
            next_sequence[chat] = expected_sequence + 2
            user_at, assistant_at = (
                datetime.fromisoformat(exchange[key])
                for key in ("user_at", "assistant_at")
            )
            _require(
                last_time is None or last_time < user_at < assistant_at,
                "source chronology changed",
            )
            last_time = assistant_at
        target = case["target"]
        _require(
            all(
                target.get(key, "primary") == "primary"
                for key in ("workspace", "subject", "root")
            )
            and target.get("purpose", "evaluation") == "evaluation",
            "target scope is outside the primary binding",
        )
        _require(target["order"] == len(exchanges) + 1, "target order changed")
        _require(
            target["user_sequence"] == next_sequence.get(target["chat"], 1),
            "target local sequence changed",
        )
        fact_by_id = {fact["id"]: fact for fact in case["facts"]}
        _require(len(fact_by_id) == len(case["facts"]), "duplicate fact ID")
        for fact in case["facts"]:
            spec = fact_type_spec(fact["fact_type"])
            _require(
                spec.entity_kind == fact["entity_kind"],
                "fact entity kind disagrees with registry",
            )
            normalize_qualifier(spec, fact["qualifier"])
            value: str | None = None
            status: str | None = None
            _require(
                fact["transitions"] and fact["transitions"][0]["operation"] == "add",
                "fact chain must start with add",
            )
            previous_order = 0
            for transition in fact["transitions"]:
                operation, source = transition["operation"], transition["source"]
                _require(
                    previous_order == 0 or operation != "add",
                    "fact chain contains a second add",
                )
                if transition["origin"] == "operator":
                    _require(
                        operation == "forget"
                        and source is None
                        and transition["reason"] == "forgotten",
                        "unsupported operator transition",
                    )
                    value, status = None, "forgotten"
                    previous_order = len(exchanges) + 1
                else:
                    _require(
                        source is not None and source.endswith(":user"),
                        "reviewer transition needs user authority",
                    )
                    exchange = exchanges[source.split(":", 1)[0]]
                    _require(
                        exchange["order"] > previous_order,
                        "fact transitions are not chronological",
                    )
                    previous_order = exchange["order"]
                    quote = transition["source_quote"]
                    bind_exact_quote(
                        {"id": source, "content": exchange["user"]},
                        quote,
                        "user_assertion",
                    )
                    kind = (
                        (
                            "subject_add"
                            if fact["entity_kind"] == "subject"
                            else "related_add"
                        )
                        if operation == "add"
                        else operation
                    )
                    _validate_write(
                        kind, fact, transition["value"], transition["reason"], quote
                    )
                    status = (
                        "inactive"
                        if operation == "end"
                        or operation == "revise"
                        and transition["value"] is None
                        else "active"
                    )
                    if operation in {"add", "revise", "reassert"}:
                        value = transition["value"]
                _require(
                    transition["status"] == status,
                    "transition status disagrees with operation",
                )
            _require(
                fact["current"] == {"status": status, "value": value},
                "current fact projection differs from transitions",
            )
        for source in case["required_evidence"]:
            exchange = exchanges.get(source.split(":", 1)[0])
            _require(exchange is not None, "required evidence is not target-time setup")
            _require(
                all(
                    exchange.get(key, "primary") == "primary"
                    for key in ("workspace", "subject", "root")
                )
                and exchange.get("purpose", "evaluation") == "evaluation",
                "required evidence crosses target scope",
            )
        _validate_delta(
            case["expected_delta"],
            target["user"],
            fact_by_id,
            generation_advance=case["expected_generation_advance"],
            revision_count=case["expected_revision_count"],
            entity_additions=case["expected_entity_additions"],
        )
        if "followup" in case:
            followup = case["followup"]
            _require(
                followup["order"] == target["order"] + 1, "follow-up order changed"
            )
            _require(
                followup["chat"] == target["chat"]
                and followup["user_sequence"] == target["user_sequence"] + 2,
                "follow-up local sequence changed",
            )
            _validate_delta(
                followup["expected_delta"],
                followup["user"],
                fact_by_id,
                generation_advance=followup["expected_generation_advance"],
                revision_count=followup["expected_revision_count"],
                entity_additions=followup["expected_entity_additions"],
            )
    controls = fixture["native_controls"]
    _require(
        [item["id"] for item in controls]
        == contract["paired_schedule"]["native_control_ids"],
        "native control schedule is incomplete",
    )
    for control in controls:
        source_case = by_case[control["setup_case"]]
        setup_ids = [exchange["id"] for exchange in source_case["setup"]]
        _require(
            control["through"] is None or control["through"] in setup_ids,
            "control setup cutoff is missing",
        )
        included_ids = (
            set(setup_ids[: setup_ids.index(control["through"]) + 1])
            if control["through"] is not None
            else set()
        )
        seeded = {}
        expected_seeded = []
        for fact in source_case["facts"]:
            value = None
            status = None
            for transition in fact["transitions"]:
                source = transition["source"]
                if source is None:
                    if len(included_ids) != len(setup_ids):
                        continue
                elif source.split(":", 1)[0] not in included_ids:
                    continue
                status = transition["status"]
                if status == "forgotten":
                    value = None
                elif transition["value"] is not None:
                    value = transition["value"]
            if status is not None:
                seeded[fact["id"]] = fact
                expected_seeded.append(
                    {"id": fact["id"], "status": status, "value": value}
                )
        _require(
            control["seeded_facts"] == expected_seeded,
            "control seed state differs from cutoff",
        )
        _validate_delta(
            control["expected_delta"],
            control["user"],
            seeded,
            generation_advance=control["expected_generation_advance"],
            revision_count=control["expected_revision_count"],
            entity_additions=control["expected_entity_additions"],
        )
    _require(
        fixture["followup_schedule"]
        == contract["paired_schedule"]["followup_case_ids_per_arm"]
        and all(
            "followup" in by_case[case_id] for case_id in fixture["followup_schedule"]
        ),
        "per-arm follow-up schedule is incomplete",
    )
