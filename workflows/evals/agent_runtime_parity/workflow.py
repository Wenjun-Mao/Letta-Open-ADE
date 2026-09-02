from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from workflows.evals.agent_runtime_v3_acceptance.cleanup import (
    CleanupScope,
    ScopedPostgresCleanup,
)

from .artifacts import ArtifactWriter
from .clients import LegacyV2Client, NativeV3Client, PublicApiError
from .config import ParityConfig, validate_config, validate_run_id
from .provenance import (
    build_parity_spec,
    build_provenance,
    capture_legacy_inputs,
    capture_source_identity,
    evaluate_comparability,
    native_definition_snapshot,
    safe_native_health,
)
from .scoring import ConversationFixture, load_fixture, score_common_contract


@dataclass(frozen=True)
class LegacyCleanupTarget:
    round_index: int
    agent_id: str


def new_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y%m%dt%H%M%Sz")
    return f"parity-{timestamp}-{uuid4().hex[:8]}"


async def run_parity(
    config: ParityConfig,
    *,
    run_id: str | None = None,
) -> dict[str, Any]:
    validate_config(config)
    resolved_run_id = validate_run_id(run_id or new_run_id())
    fixture = load_fixture(config.fixture_path)
    writer = ArtifactWriter(config.output_dir, resolved_run_id)
    parity_spec = build_parity_spec(
        config=config, fixture=fixture, run_id=resolved_run_id
    )
    parity_spec_artifact = writer.write_json("parity-spec", parity_spec)
    source_identity = capture_source_identity()
    legacy = LegacyV2Client(config.legacy_api_base_url, config.legacy_api_key)
    native = NativeV3Client(config.native_api_base_url, config.native_api_key)
    legacy_cleanup_targets: list[LegacyCleanupTarget] = []
    legacy_creation_indeterminate = False
    native_definition_keys = tuple(
        _native_definition_key(resolved_run_id, index)
        for index in range(1, config.rounds + 1)
    )
    native_subject_keys = tuple(
        _native_subject_key(resolved_run_id, index)
        for index in range(1, config.rounds + 1)
    )
    legacy_inputs: dict[str, Any] | None = None
    native_health: dict[str, Any] | None = None
    preflight_error: dict[str, Any] | None = None
    round_results: list[dict[str, Any]] = []
    normalized_turns: list[dict[str, Any]] = []
    cleanup: dict[str, Any] = {}
    try:
        try:
            legacy_inputs, health = await asyncio.gather(
                capture_legacy_inputs(legacy, config), native.worker_health()
            )
            native_health = safe_native_health(health)
        except Exception as exc:
            preflight_error = _safe_error(exc)
        if preflight_error is None:
            for round_index in range(1, config.rounds + 1):
                (
                    legacy_result,
                    legacy_created,
                    legacy_indeterminate,
                ) = await _run_legacy_round(
                    api=legacy,
                    config=config,
                    fixture=fixture,
                    run_id=resolved_run_id,
                    round_index=round_index,
                    legacy_inputs=legacy_inputs,
                )
                if legacy_created:
                    legacy_cleanup_targets.append(legacy_created)
                legacy_creation_indeterminate = (
                    legacy_creation_indeterminate or legacy_indeterminate
                )
                native_result = await _run_native_round(
                    api=native,
                    config=config,
                    fixture=fixture,
                    run_id=resolved_run_id,
                    round_index=round_index,
                    definition_key=native_definition_keys[round_index - 1],
                    subject_key=native_subject_keys[round_index - 1],
                )
                round_results.append(
                    {
                        "round": round_index,
                        "pass": bool(legacy_result["score"]["pass"])
                        and bool(native_result["score"]["pass"]),
                        "legacy": legacy_result,
                        "native": native_result,
                        "native_definition": native_result.get("definition"),
                    }
                )
                normalized_turns.extend(legacy_result["turns"])
                normalized_turns.extend(native_result["turns"])
    finally:
        cleanup = await _cleanup_all(
            legacy=legacy,
            legacy_targets=legacy_cleanup_targets,
            legacy_creation_indeterminate=legacy_creation_indeterminate,
            database_url=config.database_url,
            output_dir=config.output_dir,
            run_id=resolved_run_id,
            native_definition_keys=native_definition_keys,
            native_subject_keys=native_subject_keys,
        )
        await legacy.aclose()
        await native.aclose()

    turns_artifact = writer.write_jsonl("normalized-turns", normalized_turns)
    native_rounds = [
        {
            "round": item["round"],
            "native_definition": item.get("native_definition"),
        }
        for item in round_results
    ]
    provenance = build_provenance(
        run_id=resolved_run_id,
        parity_spec_sha256=parity_spec_artifact.sha256,
        source_identity=source_identity,
        legacy_inputs=legacy_inputs,
        native_health=native_health,
        native_rounds=native_rounds,
        cleanup=cleanup,
    )
    provenance["normalized_turns_sha256"] = turns_artifact.sha256
    provenance_artifact = writer.write_json("provenance", provenance)
    comparability = evaluate_comparability(
        parity_spec_sha256=parity_spec_artifact.sha256,
        parity_spec=parity_spec,
        legacy_inputs=legacy_inputs,
        native_health=native_health,
        native_rounds=native_rounds,
        source_identity=source_identity,
    )
    comparison = _build_comparison(
        run_id=resolved_run_id,
        parity_spec_sha256=parity_spec_artifact.sha256,
        provenance_sha256=provenance_artifact.sha256,
        normalized_turns_sha256=turns_artifact.sha256,
        preflight_error=preflight_error,
        comparability=comparability,
        expected_rounds=config.rounds,
        rounds=round_results,
        cleanup=cleanup,
    )
    comparison_artifact = writer.write_json("comparison", comparison)
    summary = _build_summary(
        run_id=resolved_run_id,
        config=config,
        fixture=fixture,
        parity_spec_sha256=parity_spec_artifact.sha256,
        provenance_sha256=provenance_artifact.sha256,
        normalized_turns_sha256=turns_artifact.sha256,
        comparison_sha256=comparison_artifact.sha256,
        preflight_error=preflight_error,
        comparability=comparability,
        rounds=round_results,
        cleanup=cleanup,
        passed=bool(comparison["pass"]),
    )
    summary_artifact = writer.write_json("summary", summary)
    return {
        **summary,
        "artifact_paths": {
            "parity_spec": str(parity_spec_artifact.path),
            "provenance": str(provenance_artifact.path),
            "normalized_turns": str(turns_artifact.path),
            "comparison": str(comparison_artifact.path),
            "summary": str(summary_artifact.path),
        },
    }


async def _run_legacy_round(
    *,
    api: LegacyV2Client,
    config: ParityConfig,
    fixture: ConversationFixture,
    run_id: str,
    round_index: int,
    legacy_inputs: dict[str, Any],
) -> tuple[dict[str, Any], LegacyCleanupTarget | None, bool]:
    started = time.monotonic()
    agent_id = ""
    creation_indeterminate = False
    turns: list[dict[str, Any]] = []
    error: dict[str, Any] | None = None
    try:
        created = await api.create_agent(
            {
                "scenario": "chat",
                "name": f"{run_id}-legacy-r{round_index:02d}",
                "model": config.legacy_model,
                "prompt_key": config.prompt_key,
                "persona_key": config.persona_key,
                "embedding": config.legacy_embedding,
                "model_identity_sha256": legacy_inputs["model"]["identity_sha256"],
                "embedding_identity_sha256": legacy_inputs["embedding"][
                    "identity_sha256"
                ],
                "prompt_content_sha256": legacy_inputs["prompt"]["content_sha256"],
                "persona_content_sha256": legacy_inputs["persona"]["content_sha256"],
            }
        )
        agent_id = _required_id(created, "id")
        _assert_legacy_identity(created, config, legacy_inputs)
        for turn_index, content in enumerate(fixture.turns, start=1):
            turn_started = time.monotonic()
            response = await api.send_message(
                agent_id=agent_id,
                message=content,
                timeout_seconds=config.timeout_seconds,
                retry_count=config.retry_count,
            )
            turns.append(
                _normalize_legacy_turn(
                    round_index=round_index,
                    turn_index=turn_index,
                    user_content=content,
                    response=response,
                    timeout_seconds=config.timeout_seconds,
                    retry_count=config.retry_count,
                    elapsed_seconds=time.monotonic() - turn_started,
                )
            )
        state = await api.persistent_state(agent_id)
        memory_values = _legacy_human_memory_values(state)
    except Exception as exc:
        error = _safe_error(exc)
        if not agent_id:
            creation_indeterminate = True
        memory_values = []
    score = score_common_contract(
        fixture=fixture,
        turn_records=turns,
        observed_memory_values=memory_values,
        timeout_seconds=config.timeout_seconds,
        retry_count=config.retry_count,
    )
    return (
        {
            "engine": "letta-v2",
            "round": round_index,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "score": score,
            "turns": turns,
            "resources": {"agent_id": agent_id or None},
            "memory_observation": {
                "representation": "legacy_human_block",
                "values": memory_values,
            },
            "error": error,
        },
        LegacyCleanupTarget(round_index, agent_id) if agent_id else None,
        creation_indeterminate,
    )


async def _run_native_round(
    *,
    api: NativeV3Client,
    config: ParityConfig,
    fixture: ConversationFixture,
    run_id: str,
    round_index: int,
    definition_key: str,
    subject_key: str,
) -> dict[str, Any]:
    started = time.monotonic()
    turns: list[dict[str, Any]] = []
    definition: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    final_values: list[str] = []
    lifecycle = {"archived": False, "restored": False}
    try:
        session = await api.create_agent_studio_session(
            idempotency_key=f"{run_id}-r{round_index:02d}-session",
            definition_key=definition_key,
            name=f"Parity native round {round_index}",
            subject_external_key=subject_key,
            subject_display_name=f"Parity subject {round_index}",
            title=f"Parity round {round_index}",
            model_key=config.native_conversation_model,
            reviewer_model_key=config.native_reviewer_model,
            embedding_model_key=config.native_embedding_model,
            prompt_key=config.prompt_key,
            persona_key=config.persona_key,
        )
        if session.get("idempotent_replay") is not False:
            raise ValueError("native Agent Studio session was not freshly created")
        created_definition = _required_mapping(session, "agent_definition")
        definition = native_definition_snapshot(
            created_definition,
            expected_prompt_key=config.prompt_key,
            expected_persona_key=config.persona_key,
        )
        if definition["definition_key"] != definition_key:
            raise ValueError("native definition escaped the run-scoped definition key")
        created_subject = _required_mapping(session, "memory_subject")
        subject_id = _required_id(created_subject, "id")
        if created_subject.get("external_key") != subject_key:
            raise ValueError("native subject escaped the run-scoped external key")
        created_conversation = _required_mapping(session, "conversation")
        conversation_id = _required_id(created_conversation, "id")
        if (
            created_conversation.get("agent_definition_id") != definition["id"]
            or created_conversation.get("memory_subject_id") != subject_id
        ):
            raise ValueError(
                "native conversation escaped its definition/subject binding"
            )
        for turn_index, content in enumerate(fixture.turns, start=1):
            turn_started = time.monotonic()
            accepted = await api.accept_turn(
                conversation_id=conversation_id,
                content=content,
                idempotency_key=_idempotency_key(run_id, round_index, turn_index),
                timeout_seconds=config.timeout_seconds,
                retry_count=config.retry_count,
            )
            run, events = await api.await_terminal(
                accepted,
                timeout_seconds=config.timeout_seconds + 30,
            )
            state, memories = await asyncio.gather(
                api.conversation_state(conversation_id),
                api.subject_memories(subject_id),
            )
            values = _native_active_memory_values(memories)
            final_values = values
            turns.append(
                _normalize_native_turn(
                    round_index=round_index,
                    turn_index=turn_index,
                    user_content=content,
                    run=run,
                    events=events,
                    state=state,
                    memory_values=values,
                    elapsed_seconds=time.monotonic() - turn_started,
                )
            )
        archived = await api.archive_agent_studio_session(conversation_id)
        lifecycle["archived"] = bool(
            _required_mapping(archived, "conversation").get("archived_at")
        )
        restored = await api.restore_agent_studio_session(conversation_id)
        lifecycle["restored"] = (
            _required_mapping(restored, "conversation").get("archived_at") is None
        )
    except Exception as exc:
        error = _safe_error(exc)
    score = score_common_contract(
        fixture=fixture,
        turn_records=turns,
        observed_memory_values=final_values,
        timeout_seconds=config.timeout_seconds,
        retry_count=config.retry_count,
    )
    score["checks"]["agent_studio_session_lifecycle"] = all(lifecycle.values())
    score["pass"] = all(score["checks"].values())
    return {
        "engine": "ade-native-v3",
        "round": round_index,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "score": score,
        "turns": turns,
        "definition": definition,
        "product_api": "/api/v3/agent-studio/sessions",
        "session_lifecycle": lifecycle,
        "memory_observation": {
            "representation": "typed_active_facts",
            "values": final_values,
        },
        "error": error,
    }


async def _cleanup_all(
    *,
    legacy: LegacyV2Client,
    legacy_targets: list[LegacyCleanupTarget],
    legacy_creation_indeterminate: bool,
    database_url: str,
    output_dir: Any,
    run_id: str,
    native_definition_keys: tuple[str, ...],
    native_subject_keys: tuple[str, ...],
) -> dict[str, Any]:
    legacy_outcomes: list[dict[str, Any]] = []
    for target in legacy_targets:
        outcome = {
            "round": target.round_index,
            "agent_id": target.agent_id,
            "archived": False,
            "purged": False,
            "error": None,
        }
        try:
            await legacy.archive_agent(target.agent_id)
            outcome["archived"] = True
            await legacy.purge_agent(target.agent_id)
            outcome["purged"] = True
        except Exception as exc:
            outcome["error"] = _safe_error(exc)
        legacy_outcomes.append(outcome)
    legacy_completed = not legacy_creation_indeterminate and all(
        item["archived"] and item["purged"] for item in legacy_outcomes
    )
    native_cleanup: dict[str, Any]
    try:
        manifest = ScopedPostgresCleanup(
            database_url=database_url,
            output_dir=output_dir,
        ).cleanup(
            CleanupScope(
                run_id=run_id,
                definition_keys=native_definition_keys,
                subject_external_keys=native_subject_keys,
            )
        )
        native_cleanup = {
            "completed": manifest.payload.get("status") == "completed",
            "recovery_manifest": str(manifest.path),
            "manifest_sha256": _file_sha256(manifest.path),
            "error": None,
        }
    except Exception as exc:
        native_cleanup = {
            "completed": False,
            "recovery_manifest": None,
            "manifest_sha256": None,
            "error": _safe_error(exc),
        }
    return {
        "legacy": {
            "required": True,
            "completed": legacy_completed,
            "creation_indeterminate": legacy_creation_indeterminate,
            "outcomes": legacy_outcomes,
        },
        "native": {"required": True, **native_cleanup},
        "completed": legacy_completed and bool(native_cleanup["completed"]),
    }


def _normalize_legacy_turn(
    *,
    round_index: int,
    turn_index: int,
    user_content: str,
    response: dict[str, Any],
    timeout_seconds: float,
    retry_count: int,
    elapsed_seconds: float,
) -> dict[str, Any]:
    sequence = response.get("sequence")
    items = sequence if isinstance(sequence, list) else []
    replies = [
        str(item.get("content") or "").strip()
        for item in items
        if isinstance(item, dict)
        and str(item.get("type") or "").casefold() == "assistant"
        and str(item.get("content") or "").strip()
    ]
    tools = [
        str(item.get("name") or "")
        for item in items
        if isinstance(item, dict)
        and str(item.get("type") or "").casefold() == "tool_call"
        and str(item.get("name") or "").strip()
    ]
    return {
        "schema_version": 1,
        "engine": "letta-v2",
        "round": round_index,
        "turn_index": turn_index,
        "user_content": user_content,
        "assistant_replies": replies,
        "terminal_status": "succeeded",
        "timeout_seconds": timeout_seconds,
        "retry_count": retry_count,
        "attempt_count": None,
        "transport_attempt_count": 1,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "tool_outcomes": [{"name": name, "status": "observed"} for name in tools],
        "memory_outcome": _legacy_memory_outcome(response),
    }


def _normalize_native_turn(
    *,
    round_index: int,
    turn_index: int,
    user_content: str,
    run: dict[str, Any],
    events: tuple[Any, ...],
    state: dict[str, Any],
    memory_values: list[str],
    elapsed_seconds: float,
) -> dict[str, Any]:
    run_id = _required_id(run, "id")
    normalized_events = [
        {"sequence": event.sequence, "type": event.event_type, "attempt": event.attempt}
        for event in events
    ]
    tool_outcomes = [
        {"name": event["type"], "status": "observed"}
        for event in normalized_events
        if "tool" in event["type"].casefold()
    ]
    return {
        "schema_version": 1,
        "engine": "ade-native-v3",
        "round": round_index,
        "turn_index": turn_index,
        "user_content": user_content,
        "assistant_replies": _native_assistant_replies(state, run_id),
        "terminal_status": str(run.get("status") or "unknown"),
        "timeout_seconds": float(run.get("timeout_seconds") or -1),
        "retry_count": int(
            run.get("retry_count") if run.get("retry_count") is not None else -1
        ),
        "attempt_count": int(run.get("attempt_count") or 0),
        "transport_attempt_count": 1,
        "elapsed_seconds": round(elapsed_seconds, 3),
        "run_id": run_id,
        "run_events": normalized_events,
        "tool_outcomes": tool_outcomes,
        "memory_outcome": {
            "representation": "typed_active_facts",
            "active_values": memory_values,
        },
    }


def _build_comparison(
    *,
    run_id: str,
    parity_spec_sha256: str,
    provenance_sha256: str,
    normalized_turns_sha256: str,
    preflight_error: dict[str, Any] | None,
    comparability: dict[str, Any],
    expected_rounds: int,
    rounds: list[dict[str, Any]],
    cleanup: dict[str, Any],
) -> dict[str, Any]:
    paired_rounds_pass = len(rounds) == expected_rounds and all(
        item["pass"] for item in rounds
    )
    checks = {
        "preflight_completed": preflight_error is None,
        "inputs_comparable": bool(comparability["pass"]),
        "all_paired_rounds_pass": paired_rounds_pass,
        "cleanup_complete": bool(cleanup["completed"]),
        "zero_retry_policy": all(
            item["legacy"]["score"]["checks"]["timeout_retry_controls_exact"]
            and item["native"]["score"]["checks"]["timeout_retry_controls_exact"]
            for item in rounds
        ),
    }
    return {
        "schema_version": 1,
        "kind": "agent-runtime-parity-comparison",
        "run_id": run_id,
        "pass": all(checks.values()),
        "checks": checks,
        "artifact_inputs": {
            "parity_spec_sha256": parity_spec_sha256,
            "provenance_sha256": provenance_sha256,
            "normalized_turns_sha256": normalized_turns_sha256,
        },
        "preflight_error": preflight_error,
        "comparability": comparability,
        "cleanup": cleanup,
        "rounds": [
            {
                "round": item["round"],
                "pass": item["pass"],
                "legacy_score": item["legacy"]["score"],
                "native_score": item["native"]["score"],
            }
            for item in rounds
        ],
        "semantic_differences_permitted": [
            "legacy human memory block versus native typed facts",
            "assistant prose is not compared",
        ],
    }


def _build_summary(
    *,
    run_id: str,
    config: ParityConfig,
    fixture: ConversationFixture,
    parity_spec_sha256: str,
    provenance_sha256: str,
    normalized_turns_sha256: str,
    comparison_sha256: str,
    preflight_error: dict[str, Any] | None,
    comparability: dict[str, Any],
    rounds: list[dict[str, Any]],
    cleanup: dict[str, Any],
    passed: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "agent-runtime-parity-summary",
        "run_id": run_id,
        "pass": passed,
        "rounds_requested": config.rounds,
        "rounds_completed": len(rounds),
        "rounds_passed": sum(1 for item in rounds if item["pass"]),
        "fixture": {"key": fixture.key, "sha256": fixture.sha256},
        "controls": {
            "timeout_seconds": config.timeout_seconds,
            "retry_count": config.retry_count,
            "client_transport_retries": 0,
        },
        "artifact_inputs": {
            "parity_spec_sha256": parity_spec_sha256,
            "provenance_sha256": provenance_sha256,
            "normalized_turns_sha256": normalized_turns_sha256,
            "comparison_sha256": comparison_sha256,
        },
        "preflight_error": preflight_error,
        "inputs_comparable": bool(comparability["pass"]),
        "cleanup_complete": bool(cleanup["completed"]),
    }


def _assert_legacy_identity(
    created: dict[str, Any], config: ParityConfig, inputs: dict[str, Any]
) -> None:
    expected = {
        "model": config.legacy_model,
        "embedding": config.legacy_embedding,
        "prompt_key": config.prompt_key,
        "persona_key": config.persona_key,
        "model_identity_sha256": inputs["model"]["identity_sha256"],
        "embedding_identity_sha256": inputs["embedding"]["identity_sha256"],
        "prompt_content_sha256": inputs["prompt"]["content_sha256"],
        "persona_content_sha256": inputs["persona"]["content_sha256"],
    }
    for key, value in expected.items():
        if created.get(key) != value:
            raise ValueError(f"legacy agent creation returned a different {key}")


def _legacy_human_memory_values(state: dict[str, Any]) -> list[str]:
    blocks = state.get("memory_blocks")
    if not isinstance(blocks, list):
        return []
    return [
        str(block.get("value") or "")
        for block in blocks
        if isinstance(block, dict)
        and str(block.get("label") or "") == "human"
        and str(block.get("value") or "").strip()
    ]


def _legacy_memory_outcome(response: dict[str, Any]) -> dict[str, Any]:
    memory_diff = response.get("memory_diff")
    if not isinstance(memory_diff, dict):
        return {"representation": "legacy_human_block", "changed": False}
    old = memory_diff.get("old")
    new = memory_diff.get("new")
    old_human = old.get("human") if isinstance(old, dict) else ""
    new_human = new.get("human") if isinstance(new, dict) else ""
    return {
        "representation": "legacy_human_block",
        "changed": str(old_human or "").strip() != str(new_human or "").strip(),
        "after_sha256": hashlib.sha256(
            str(new_human or "").encode("utf-8")
        ).hexdigest(),
    }


def _native_active_memory_values(payload: dict[str, Any]) -> list[str]:
    facts = payload.get("facts")
    if not isinstance(facts, list):
        return []
    return [
        str(fact.get("value") or "")
        for fact in facts
        if isinstance(fact, dict)
        and fact.get("status") == "active"
        and str(fact.get("value") or "").strip()
    ]


def _native_assistant_replies(state: dict[str, Any], run_id: str) -> list[str]:
    messages = state.get("messages")
    if not isinstance(messages, list):
        return []
    return [
        str(message.get("content") or "").strip()
        for message in messages
        if isinstance(message, dict)
        and message.get("role") == "assistant"
        and message.get("run_id") == run_id
        and str(message.get("content") or "").strip()
    ]


def _native_definition_key(run_id: str, round_index: int) -> str:
    value = f"{run_id}-r{round_index:02d}-definition"
    if len(value) > 64:
        raise ValueError("run id leaves no room for the v3 definition key")
    return value


def _native_subject_key(run_id: str, round_index: int) -> str:
    return f"{run_id}-r{round_index:02d}-subject"


def _idempotency_key(run_id: str, round_index: int, turn_index: int) -> str:
    return f"{run_id}-r{round_index:02d}-t{turn_index:02d}"


def _required_id(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"public API response did not return {key}")
    return value


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"public API response did not return {key}")
    return value


def _safe_error(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, PublicApiError):
        return {
            "kind": "public_api_error",
            "engine": exc.engine,
            "status_code": exc.status_code,
            "code": exc.code,
        }
    return {"kind": type(exc).__name__, "code": "workflow_error"}


def _file_sha256(path: Any) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
