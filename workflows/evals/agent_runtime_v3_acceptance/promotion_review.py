from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_runtime_eval_contracts import (
    EventObservation,
    FactObservation,
    ToolObservation,
    TurnObservation,
    load_cases,
    score_case,
    study_cases_path,
)
from model_catalog_contracts.deployment_manifest import DeploymentManifest

from .policy import fingerprint_policy_hashes, production_policy_hashes
from .qualification import requires_versioned_summary


REQUIRED_ROLES = frozenset({"conversation", "reviewer", "retriever"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")


class PromotionReviewError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitState:
    revision: str
    dirty: bool


@dataclass(frozen=True)
class PromotionReview:
    proposal_sha256: str
    source_revision: str
    deployment_ids: tuple[str, ...]
    applied: bool


def review_promotion(
    *,
    proposal_path: Path,
    manifest_path: Path,
    project_root: Path,
    apply: bool,
    git_state: GitState | None = None,
) -> PromotionReview:
    proposal = _load_json(proposal_path, "promotion proposal")
    _verify_content_digest(
        proposal,
        field="proposal_sha256",
        label="promotion proposal",
        newline=False,
    )
    _require_equal(proposal.get("schema_version"), 1, "proposal schema_version")
    _require_equal(
        proposal.get("kind"),
        "agent-runtime-v3-promotion-proposal",
        "proposal kind",
    )
    _require_equal(proposal.get("apply_status"), "proposal-only", "apply status")
    _require_equal(proposal.get("source_dirty"), False, "proposal source_dirty")
    source_revision = _required_revision(proposal.get("source_revision"))
    source_fingerprint = _required_digest(
        proposal.get("source_fingerprint"), "proposal source_fingerprint"
    )
    state = git_state or _read_git_state(project_root)
    if state.revision != source_revision or state.dirty:
        raise PromotionReviewError(
            "promotion requires the exact clean source revision that produced the evidence"
        )

    policy_hashes = _digest_mapping(proposal.get("policy_hashes"), "policy hashes")
    if policy_hashes != production_policy_hashes(project_root):
        raise PromotionReviewError("promotion policy hashes are stale")
    qualification_config = _mapping(
        proposal.get("qualification_config"), "qualification config"
    )
    expected_qualification_keys = {
        "conversation_model_key",
        "reviewer_model_key",
        "embedding_model_key",
        "rounds",
        "timeout_seconds",
        "retry_count",
        "case_keys",
    }
    if set(qualification_config) != expected_qualification_keys:
        raise PromotionReviewError("promotion qualification config is incomplete")
    if qualification_config.get("case_keys") != []:
        raise PromotionReviewError(
            "promotion cannot use a case-filtered diagnostic selection"
        )
    if (
        qualification_config.get("rounds") != 3
        or float(qualification_config.get("timeout_seconds") or 0) != 180.0
        or qualification_config.get("retry_count") != 0
    ):
        raise PromotionReviewError(
            "production qualification requires three rounds at 180s with zero retries"
        )

    run_dir = proposal_path.parent
    preflight = _load_json(run_dir / "preflight.json", "worker preflight")
    preflight_sha256 = _validate_worker_preflight(
        preflight,
        run_id=str(proposal.get("run_id") or ""),
        source_revision=source_revision,
        source_fingerprint=source_fingerprint,
    )
    _require_equal(
        preflight_sha256,
        proposal.get("preflight_sha256"),
        "worker preflight digest",
    )
    provenance = _load_json(run_dir / "provenance.json", "provenance")
    provenance_sha256 = _verify_content_digest(
        provenance,
        field="provenance_sha256",
        label="provenance",
        newline=True,
    )
    _require_equal(
        provenance_sha256,
        proposal.get("provenance_sha256"),
        "provenance digest",
    )
    for key, expected in (
        ("run_id", proposal.get("run_id")),
        ("source_revision", source_revision),
        ("source_dirty", False),
        ("source_fingerprint", source_fingerprint),
        ("policy_hashes", policy_hashes),
        ("preflight_sha256", preflight_sha256),
    ):
        _require_equal(provenance.get(key), expected, f"provenance {key}")
    effective = _mapping(provenance.get("effective_config"), "effective config")
    for key, expected in qualification_config.items():
        _require_equal(effective.get(key), expected, f"effective config {key}")

    canonical_case_keys = _string_list(
        proposal.get("canonical_case_keys"), "canonical case keys"
    )
    canonical_cases = tuple(load_cases(study_cases_path()))
    expected_case_keys = [case.key for case in canonical_cases]
    _require_equal(
        canonical_case_keys,
        expected_case_keys,
        "canonical production case matrix",
    )
    cases_by_key = {case.key: case for case in canonical_cases}
    _require_equal(
        provenance.get("canonical_case_keys"),
        canonical_case_keys,
        "provenance canonical matrix",
    )
    _require_equal(
        provenance.get("canonical_case_keys_sha256"),
        _sha256("\n".join(canonical_case_keys).encode("utf-8")),
        "provenance canonical matrix digest",
    )
    round_digests = _string_list(
        proposal.get("round_artifact_sha256s"), "round artifact digests"
    )
    if len(round_digests) != 3 or any(
        not _SHA256_RE.fullmatch(value) for value in round_digests
    ):
        raise PromotionReviewError("promotion requires exactly three round digests")
    rounds = _load_rounds(run_dir, round_digests)
    expected_fingerprints = _digest_mapping(
        proposal.get("deployment_fingerprints"), "deployment fingerprints"
    )
    for index, round_payload in enumerate(rounds, start=1):
        _validate_round(
            round_payload,
            index=index,
            canonical_case_keys=canonical_case_keys,
            cases_by_key=cases_by_key,
            deployment_fingerprints=expected_fingerprints,
        )
    provenance_rounds = provenance.get("primary_rounds")
    if not isinstance(provenance_rounds, list):
        raise PromotionReviewError("provenance primary_rounds must be a list")
    _require_equal(
        [item.get("artifact_sha256") for item in provenance_rounds],
        round_digests,
        "provenance round digests",
    )

    bindings = _deployment_bindings(proposal.get("deployment_bindings"))
    if set(bindings) != REQUIRED_ROLES:
        raise PromotionReviewError("proposal must bind every required deployment role")
    config_keys = {
        "conversation": "conversation_model_key",
        "reviewer": "reviewer_model_key",
        "retriever": "embedding_model_key",
    }
    for role, binding in bindings.items():
        _require_equal(
            qualification_config.get(config_keys[role]),
            binding["route_alias"],
            f"{role} configured route alias",
        )
        _require_equal(
            binding["fingerprint_sha256"],
            expected_fingerprints.get(role),
            f"{role} binding fingerprint",
        )
        if not all(_round_contains_binding(item, role, binding) for item in rounds):
            raise PromotionReviewError(
                f"round evidence does not contain the exact {role} deployment binding"
            )

    manifest_payload = _load_json(manifest_path, "deployment manifest")
    manifest = DeploymentManifest.from_payload(manifest_payload)
    entries = {item.deployment_id: item for item in manifest.deployments}
    for role, binding in bindings.items():
        entry = entries.get(binding["deployment_id"])
        if entry is None or role not in entry.roles:
            raise PromotionReviewError(
                f"manifest does not bind deployment role {role} to {binding['deployment_id']}"
            )
        if (
            entry.fingerprint.sha256 != binding["fingerprint_sha256"]
            or binding["route_alias"] not in entry.route_aliases
        ):
            raise PromotionReviewError(
                f"manifest fingerprint or alias changed for deployment role {role}"
            )
        if fingerprint_policy_hashes(entry.fingerprint) != policy_hashes:
            raise PromotionReviewError(
                f"manifest {role} fingerprint is not bound to the evaluated policies"
            )

    updated = _qualified_manifest(manifest_payload, bindings)
    DeploymentManifest.from_payload(updated)
    if apply:
        _atomic_write_json(manifest_path, updated)
    return PromotionReview(
        proposal_sha256=str(proposal["proposal_sha256"]),
        source_revision=source_revision,
        deployment_ids=tuple(
            sorted({binding["deployment_id"] for binding in bindings.values()})
        ),
        applied=apply,
    )


def _validate_worker_preflight(
    payload: dict[str, Any],
    *,
    run_id: str,
    source_revision: str,
    source_fingerprint: str,
) -> str:
    digest = _verify_content_digest(
        payload,
        field="preflight_sha256",
        label="worker preflight",
        newline=True,
    )
    for key, expected in (
        ("schema_version", 1),
        ("kind", "agent-runtime-v3-worker-preflight"),
        ("run_id", run_id),
        ("passed", True),
    ):
        _require_equal(payload.get(key), expected, f"worker preflight {key}")
    health = _mapping(payload.get("health"), "worker preflight health")
    source_identity = _mapping(
        payload.get("source_identity"), "worker preflight source identity"
    )
    for key, expected in (
        ("revision", source_revision),
        ("dirty", False),
        ("fingerprint", source_fingerprint),
    ):
        _require_equal(
            source_identity.get(key), expected, f"worker preflight source {key}"
        )
    for key, expected in (
        ("http_status", 200),
        ("status", "ready"),
        ("database_ready", True),
        ("worker_ready", True),
        ("source_revision", source_revision),
        ("source_dirty", False),
        ("source_fingerprint", source_fingerprint),
    ):
        _require_equal(health.get(key), expected, f"worker preflight health {key}")
    for field in ("compatible_worker_count", "matching_build_worker_count"):
        count = health.get(field)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise PromotionReviewError(
                f"worker preflight health {field} must be a positive integer"
            )
    if not _SHA256_RE.fullmatch(str(health.get("compatibility_fingerprint") or "")):
        raise PromotionReviewError(
            "worker preflight health compatibility_fingerprint is invalid"
        )
    return digest


def _load_rounds(run_dir: Path, expected_digests: list[str]) -> list[dict[str, Any]]:
    by_digest: dict[str, dict[str, Any]] = {}
    paths = sorted(run_dir.glob("round-[0-9][0-9][0-9]/round.json"))
    if len(paths) != 3:
        raise PromotionReviewError(
            "run directory must contain exactly three primary rounds"
        )
    for path in paths:
        payload = _load_json(path, f"round artifact {path.name}")
        digest = _verify_content_digest(
            payload,
            field="artifact_sha256",
            label=f"round artifact {path}",
            newline=True,
        )
        events_path = path.parent / "events.jsonl"
        if not events_path.is_file():
            raise PromotionReviewError(f"round events are missing: {events_path}")
        _require_equal(
            _sha256(events_path.read_bytes()),
            payload.get("events_sha256"),
            f"events digest for {path.parent.name}",
        )
        payload["_raw_events"] = _load_json_lines(events_path)
        by_digest[digest] = payload
    if set(by_digest) != set(expected_digests):
        raise PromotionReviewError("round artifact digests do not match the proposal")
    return [by_digest[digest] for digest in expected_digests]


def _validate_round(
    payload: dict[str, Any],
    *,
    index: int,
    canonical_case_keys: list[str],
    cases_by_key: dict[str, Any],
    deployment_fingerprints: dict[str, str],
) -> None:
    for key, expected in (
        ("index", index),
        ("kind", "primary"),
        ("execution_mode", "live-api"),
        ("complete_matrix", True),
        ("passed", True),
        ("case_keys", canonical_case_keys),
        ("deployment_fingerprints", deployment_fingerprints),
    ):
        _require_equal(payload.get(key), expected, f"round {index} {key}")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != len(canonical_case_keys):
        raise PromotionReviewError(f"round {index} case evidence is incomplete")
    _require_equal(
        [item.get("case_key") for item in cases if isinstance(item, dict)],
        canonical_case_keys,
        f"round {index} case evidence order",
    )
    if any(
        not isinstance(case, dict)
        or not isinstance(case.get("score"), dict)
        or case["score"].get("pass") is not True
        or not isinstance(case.get("infrastructure"), dict)
        or case["infrastructure"].get("failures") != []
        for case in cases
    ):
        raise PromotionReviewError(f"round {index} includes failed case evidence")
    observed_run_ids: set[str] = set()
    normalized_tools_by_run: dict[str, list[tuple[str, bool]]] = {}
    summary_requirements_by_case: dict[str, tuple[set[str], int]] = {}
    for case_payload in cases:
        case_key = str(case_payload["case_key"])
        case_run_ids, case_tools_by_run = _validate_and_rescore_case(
            case_payload, cases_by_key[case_key], index
        )
        observed_run_ids.update(case_run_ids)
        normalized_tools_by_run.update(case_tools_by_run)
        if requires_versioned_summary(cases_by_key[case_key]):
            summary_requirements_by_case[case_key] = (
                case_run_ids,
                _required_summary_boundary(cases_by_key[case_key]),
            )
    _validate_raw_events(
        payload.get("_raw_events"),
        observed_run_ids=observed_run_ids,
        normalized_tools_by_run=normalized_tools_by_run,
        summary_requirements_by_case=summary_requirements_by_case,
        conversation_fingerprint=deployment_fingerprints["conversation"],
        index=index,
    )


def _validate_and_rescore_case(
    payload: dict[str, Any], case: Any, round_index: int
) -> tuple[set[str], dict[str, list[tuple[str, bool]]]]:
    raw_facts = payload.get("facts")
    raw_turns = payload.get("turns")
    if not isinstance(raw_facts, list) or not isinstance(raw_turns, list):
        raise PromotionReviewError(
            f"round {round_index} case {case.key} lacks normalized observations"
        )
    facts_by_subject: dict[str, list[FactObservation]] = {
        subject_key: [] for subject_key in case.subject_keys
    }
    for raw_fact in raw_facts:
        fact = _mapping(raw_fact, f"{case.key} fact observation")
        subject_key = str(fact.get("subject_key") or "")
        if subject_key not in facts_by_subject:
            raise PromotionReviewError(f"{case.key} fact has an unknown subject")
        observation = _mapping(fact.get("observation"), f"{case.key} fact")
        value = str(observation.get("value") or "")
        if not value:
            raise PromotionReviewError(f"{case.key} fact value is empty")
        facts_by_subject[subject_key].append(
            FactObservation(key=str(observation.get("key") or ""), value=value)
        )

    expected_conversations = [turn.conversation_key for turn in case.turns]
    actual_conversations: list[str] = []
    results_by_conversation: dict[str, list[TurnObservation]] = {
        conversation_key: [] for conversation_key in case.conversations
    }
    run_ids: set[str] = set()
    normalized_tools_by_run: dict[str, list[tuple[str, bool]]] = {}
    for raw_turn in raw_turns:
        turn = _mapping(raw_turn, f"{case.key} turn observation")
        _require_equal(turn.get("case_key"), case.key, f"{case.key} turn case key")
        conversation_key = str(turn.get("conversation_key") or "")
        if conversation_key not in results_by_conversation:
            raise PromotionReviewError(f"{case.key} turn has an unknown conversation")
        actual_conversations.append(conversation_key)
        run_id = str(turn.get("run_id") or "")
        if not run_id or run_id in run_ids:
            raise PromotionReviewError(
                f"{case.key} turn run id is missing or duplicated"
            )
        run_ids.add(run_id)
        if turn.get("attempt_count") != 1:
            raise PromotionReviewError(
                f"{case.key} did not preserve zero-retry attempt ownership"
            )
        observation = _mapping(turn.get("observation"), f"{case.key} turn")
        events = tuple(
            EventObservation(type=_required_text(item, "type", f"{case.key} event"))
            for item in _mapping_list(observation.get("events"), f"{case.key} events")
        )
        tools = tuple(
            ToolObservation(
                name=_required_text(item, "name", f"{case.key} tool"),
                succeeded=_required_bool(item, "succeeded", f"{case.key} tool"),
            )
            for item in _mapping_list(observation.get("tools"), f"{case.key} tools")
        )
        normalized_tools_by_run[run_id] = [
            (tool.name, tool.succeeded) for tool in tools
        ]
        usage = _mapping(observation.get("usage"), f"{case.key} usage")
        if any(
            not isinstance(value, int) or isinstance(value, bool)
            for value in usage.values()
        ):
            raise PromotionReviewError(f"{case.key} usage must contain integers")
        results_by_conversation[conversation_key].append(
            TurnObservation(
                status=_required_text(observation, "status", f"{case.key} turn"),
                assistant_text=_optional_string(observation.get("assistant_text")),
                candidate_assistant_text=_optional_string(
                    observation.get("candidate_assistant_text")
                ),
                events=events,
                tools=tools,
                usage={str(key): int(value) for key, value in usage.items()},
                elapsed_seconds=float(observation.get("elapsed_seconds") or 0),
            )
        )
    _require_equal(
        actual_conversations,
        expected_conversations,
        f"{case.key} turn conversation sequence",
    )
    rescored = score_case(
        case=case,
        facts_by_subject=facts_by_subject,
        results_by_conversation=results_by_conversation,
    )
    _require_equal(payload.get("score"), rescored, f"{case.key} deterministic score")
    setup_run_ids = _string_list(
        payload.get("setup_run_ids"), f"{case.key} setup run ids"
    )
    if len(setup_run_ids) != len(set(setup_run_ids)) or run_ids.intersection(
        setup_run_ids
    ):
        raise PromotionReviewError(f"{case.key} setup run ids are duplicated")
    scoreable_run_ids = set(run_ids)
    setup_run_id_set = set(setup_run_ids)
    known_run_ids = scoreable_run_ids | setup_run_id_set
    expected_tool_records = [
        {"run_id": run_id, "name": name, "succeeded": succeeded}
        for run_id, tools in normalized_tools_by_run.items()
        for name, succeeded in tools
    ]
    actual_tool_records = [
        {
            "run_id": _required_text(item, "run_id", f"{case.key} recorded tool"),
            "name": _required_text(item, "name", f"{case.key} recorded tool"),
            "succeeded": _required_bool(item, "succeeded", f"{case.key} recorded tool"),
        }
        for item in _mapping_list(payload.get("tools"), f"{case.key} recorded tools")
    ]
    unknown_tool_run_ids = {
        record["run_id"]
        for record in actual_tool_records
        if record["run_id"] not in known_run_ids
    }
    if unknown_tool_run_ids:
        raise PromotionReviewError(
            f"{case.key} recorded tool references an unknown run"
        )
    _require_equal(
        [
            record
            for record in actual_tool_records
            if record["run_id"] in scoreable_run_ids
        ],
        expected_tool_records,
        f"{case.key} normalized tool records",
    )
    run_ids.update(setup_run_ids)
    for run_id in setup_run_ids:
        normalized_tools_by_run[run_id] = [
            (record["name"], record["succeeded"])
            for record in actual_tool_records
            if record["run_id"] == run_id
        ]
    return run_ids, normalized_tools_by_run


def _validate_raw_events(
    value: object,
    *,
    observed_run_ids: set[str],
    normalized_tools_by_run: dict[str, list[tuple[str, bool]]],
    summary_requirements_by_case: dict[str, tuple[set[str], int]],
    conversation_fingerprint: str,
    index: int,
) -> None:
    if not isinstance(value, list):
        raise PromotionReviewError(f"round {index} raw events are missing")
    events_by_run: dict[str, list[int]] = {}
    events_by_id: dict[str, dict[str, Any]] = {}
    raw_tools_by_run: dict[str, list[tuple[str, bool]]] = {}
    summary_boundaries_by_run: dict[str, list[int]] = {}
    for raw_event in value:
        event = _mapping(raw_event, f"round {index} raw event")
        run_id = str(event.get("run_id") or "")
        if run_id not in observed_run_ids:
            raise PromotionReviewError(f"round {index} raw event has an unknown run")
        sequence = event.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            raise PromotionReviewError(f"round {index} raw event sequence is invalid")
        attempt = event.get("attempt")
        if attempt not in {None, 1} or event.get("event_type") == "retry.scheduled":
            raise PromotionReviewError(
                f"round {index} raw events violate zero-retry ownership"
            )
        event_id = _required_text(event, "event_id", f"round {index} raw event")
        if event_id in events_by_id:
            raise PromotionReviewError(f"round {index} raw event id is duplicated")
        _require_equal(
            event.get("correlation_id"),
            run_id,
            f"round {index} raw event correlation",
        )
        causation_id = event.get("causation_id")
        if causation_id is None and event.get("event_type") in {
            "model.response.completed",
            "model.request.failed",
            "model.request.cancelled",
            "tool.call.requested",
            "tool.call.completed",
            "summary.committed",
        }:
            raise PromotionReviewError(
                f"round {index} raw event is missing required causation"
            )
        if causation_id is not None:
            cause = events_by_id.get(str(causation_id))
            if cause is None or cause.get("run_id") != run_id:
                raise PromotionReviewError(
                    f"round {index} raw event causation is not a prior same-run event"
                )
            _validate_event_causation(event, cause, index=index)
        events_by_run.setdefault(run_id, []).append(sequence)
        event_type = event.get("event_type")
        payload = _mapping(event.get("payload"), f"round {index} raw event payload")
        if event_type in {"model.request.failed", "model.request.cancelled"}:
            raise PromotionReviewError(
                f"round {index} includes a provider request failure"
            )
        if event_type == "tool.call.completed":
            raw_tools_by_run.setdefault(run_id, []).append(
                (
                    _required_text(payload, "name", "raw completed tool"),
                    _required_bool(payload, "succeeded", "raw completed tool"),
                )
            )
        if event_type == "summary.committed":
            boundary = _validate_summary_event(
                payload,
                run_id=run_id,
                conversation_fingerprint=conversation_fingerprint,
            )
            summary_boundaries_by_run.setdefault(run_id, []).append(boundary)
        events_by_id[event_id] = event
    _require_equal(
        set(events_by_run), observed_run_ids, f"round {index} raw event run coverage"
    )
    for run_id, sequences in events_by_run.items():
        _require_equal(
            sequences,
            list(range(1, len(sequences) + 1)),
            f"round {index} raw event sequence for {run_id}",
        )
        _require_equal(
            raw_tools_by_run.get(run_id, []),
            normalized_tools_by_run.get(run_id, []),
            f"round {index} raw tool evidence for {run_id}",
        )
    for case_key, (
        case_run_ids,
        required_boundary,
    ) in summary_requirements_by_case.items():
        observed_boundaries = [
            boundary
            for run_id in case_run_ids
            for boundary in summary_boundaries_by_run.get(run_id, [])
        ]
        if not observed_boundaries or max(observed_boundaries) < required_boundary:
            raise PromotionReviewError(
                f"{case_key} lacks a complete versioned summary commitment event"
            )


def _validate_summary_event(
    payload: dict[str, Any], *, run_id: str, conversation_fingerprint: str
) -> int:
    _required_text(payload, "summary_id", "summary commitment")
    _required_text(payload, "model_key", "summary commitment")
    _require_equal(payload.get("run_id"), run_id, "summary commitment run id")
    _require_equal(
        payload.get("model_fingerprint"),
        conversation_fingerprint,
        "summary commitment model fingerprint",
    )
    version = payload.get("version")
    boundary = payload.get("through_sequence")
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version < 1
        or not isinstance(boundary, int)
        or isinstance(boundary, bool)
        or boundary < 1
    ):
        raise PromotionReviewError("summary commitment version or boundary is invalid")
    for field in (
        "content_sha256",
        "prompt_sha256",
        "input_sha256",
        "policy_sha256",
    ):
        if not _SHA256_RE.fullmatch(str(payload.get(field) or "")):
            raise PromotionReviewError(f"summary commitment {field} is invalid")
    source_message_ids = _string_list(
        payload.get("source_message_ids"), "summary source message ids"
    )
    if not source_message_ids or len(source_message_ids) != len(
        set(source_message_ids)
    ):
        raise PromotionReviewError(
            "summary commitment source messages are missing or duplicated"
        )
    return boundary


def _validate_event_causation(
    event: dict[str, Any], cause: dict[str, Any], *, index: int
) -> None:
    event_type = str(event.get("event_type") or "")
    cause_type = str(cause.get("event_type") or "")
    payload = _mapping(event.get("payload"), "caused event payload")
    cause_payload = _mapping(cause.get("payload"), "causing event payload")
    if event_type == "model.response.completed":
        if cause_type != "model.request.started" or any(
            payload.get(field) != cause_payload.get(field)
            for field in ("role", "request_number")
        ):
            raise PromotionReviewError(
                f"round {index} model response has invalid request causation"
            )
    elif event_type in {"model.request.failed", "model.request.cancelled"}:
        if cause_type != "model.request.started" or any(
            payload.get(field) != cause_payload.get(field)
            for field in ("stage", "operation", "request_id", "request_number")
        ):
            raise PromotionReviewError(
                f"round {index} provider failure has invalid request causation"
            )
    elif event_type == "tool.call.requested":
        if (
            cause_type != "model.response.completed"
            or cause_payload.get("role") != "conversation"
            or payload.get("request_number") != cause_payload.get("request_number")
        ):
            raise PromotionReviewError(
                f"round {index} tool request has invalid model causation"
            )
    elif event_type == "tool.call.completed":
        if cause_type != "tool.call.requested" or any(
            payload.get(field) != cause_payload.get(field)
            for field in ("call_id", "name", "request_number")
        ):
            raise PromotionReviewError(
                f"round {index} tool result has invalid request causation"
            )
    elif event_type == "summary.committed" and (
        cause_type != "model.response.completed"
        or cause_payload.get("role") != "compaction"
    ):
        raise PromotionReviewError(
            f"round {index} summary has invalid compaction causation"
        )


def _required_summary_boundary(case: Any) -> int:
    return max(
        int(getattr(prelude, "summary_through_sequence", 0))
        for prelude in tuple(getattr(case, "prelude_messages", ()))
    )


def _round_contains_binding(
    round_payload: dict[str, Any], role: str, binding: dict[str, str]
) -> bool:
    snapshots = round_payload.get("deployment_snapshots")
    return isinstance(snapshots, list) and any(
        isinstance(snapshot, dict)
        and snapshot.get("role") == role
        and snapshot.get("deployment_id") == binding["deployment_id"]
        and snapshot.get("route_alias") == binding["route_alias"]
        and snapshot.get("fingerprint") == binding["fingerprint_sha256"]
        for snapshot in snapshots
    )


def _qualified_manifest(
    payload: dict[str, Any], bindings: dict[str, dict[str, str]]
) -> dict[str, Any]:
    updated = deepcopy(payload)
    roles_by_deployment: dict[str, set[str]] = {}
    for role, binding in bindings.items():
        roles_by_deployment.setdefault(binding["deployment_id"], set()).add(role)
    for deployment in updated.get("deployments", []):
        if not isinstance(deployment, dict):
            continue
        roles = roles_by_deployment.get(str(deployment.get("id") or ""))
        if not roles:
            continue
        qualification = _mapping(deployment.get("qualification"), "qualification")
        results = qualification.get("role_results")
        if not isinstance(results, list):
            raise PromotionReviewError("manifest role_results must be a list")
        for result in results:
            if isinstance(result, dict) and result.get("role") in roles:
                result["observed_rounds"] = 3
                result["consecutive_passing_rounds"] = 3
                result["qualified"] = True
        qualification["qualified"] = all(
            isinstance(result, dict) and result.get("qualified") is True
            for result in results
        )
        deployment["lifecycle"] = (
            "qualified" if qualification["qualified"] else "candidate"
        )
    return updated


def _deployment_bindings(value: object) -> dict[str, dict[str, str]]:
    raw = _mapping(value, "deployment bindings")
    bindings: dict[str, dict[str, str]] = {}
    for role, item in raw.items():
        binding = _mapping(item, f"{role} deployment binding")
        normalized = {
            "deployment_id": str(binding.get("deployment_id") or "").strip(),
            "route_alias": str(binding.get("route_alias") or "").strip(),
            "fingerprint_sha256": str(binding.get("fingerprint_sha256") or "").strip(),
        }
        if any(not item for item in normalized.values()) or not _SHA256_RE.fullmatch(
            normalized["fingerprint_sha256"]
        ):
            raise PromotionReviewError(f"invalid {role} deployment binding")
        bindings[str(role)] = normalized
    return bindings


def _read_git_state(project_root: Path) -> GitState:
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=project_root,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PromotionReviewError(
            "promotion requires an identifiable Git source"
        ) from exc
    return GitState(revision=revision, dirty=dirty)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionReviewError(f"could not read {label}: {path}") from exc
    return _mapping(value, label)


def _load_json_lines(path: Path) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            values.append(_mapping(json.loads(line), f"{path.name} line {index}"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PromotionReviewError(f"could not read raw events: {path}") from exc
    return values


def _verify_content_digest(
    payload: dict[str, Any], *, field: str, label: str, newline: bool
) -> str:
    digest = str(payload.get(field) or "")
    if not _SHA256_RE.fullmatch(digest):
        raise PromotionReviewError(f"{label} has no valid {field}")
    material = {key: value for key, value in payload.items() if key != field}
    encoded = _canonical_bytes(material, newline=newline)
    if _sha256(encoded) != digest:
        raise PromotionReviewError(f"{label} content digest does not match")
    return digest


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PromotionReviewError(f"{label} must be an object")
    return value


def _mapping_list(value: object, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise PromotionReviewError(f"{label} must be a list")
    return [_mapping(item, label) for item in value]


def _required_text(value: dict[str, Any], field: str, label: str) -> str:
    normalized = str(value.get(field) or "").strip()
    if not normalized:
        raise PromotionReviewError(f"{label} {field} is required")
    return normalized


def _required_bool(value: dict[str, Any], field: str, label: str) -> bool:
    item = value.get(field)
    if not isinstance(item, bool):
        raise PromotionReviewError(f"{label} {field} must be a boolean")
    return item


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PromotionReviewError("assistant text must be a string or null")
    return value


def _digest_mapping(value: object, label: str) -> dict[str, str]:
    raw = _mapping(value, label)
    result = {str(key): str(item) for key, item in raw.items()}
    if any(not _SHA256_RE.fullmatch(item) for item in result.values()):
        raise PromotionReviewError(f"{label} must contain SHA-256 digests")
    return result


def _string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise PromotionReviewError(f"{label} must be a string list")
    return value


def _required_revision(value: object) -> str:
    revision = str(value or "").strip().casefold()
    if not _REVISION_RE.fullmatch(revision):
        raise PromotionReviewError("proposal source_revision is invalid")
    return revision


def _required_digest(value: object, label: str) -> str:
    digest = str(value or "").strip().casefold()
    if not _SHA256_RE.fullmatch(digest):
        raise PromotionReviewError(f"{label} is invalid")
    return digest


def _require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise PromotionReviewError(f"{label} does not match reviewed evidence")


def _canonical_bytes(payload: dict[str, Any], *, newline: bool) -> bytes:
    suffix = "\n" if newline else ""
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        + suffix
    ).encode("utf-8")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
