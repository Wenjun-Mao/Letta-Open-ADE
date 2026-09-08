from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .artifacts import ArtifactWriter, build_summary, print_summary, write_summary
from .client import AdeApiClient
from .config import (
    ChatMemoryEvalConfig,
    ade_api_timeout_seconds,
    effective_judge_model_key,
    router_v1_base_url,
)
from .fixtures import ConversationFixture, load_fixture
from .judge import judge_round
from .provenance import (
    assert_created_session_identity,
    capture_evaluation_provenance,
    expected_agent_identities,
    write_provenance,
)
from .scoring import (
    DEFAULT_FORBIDDEN_REPLY_SUBSTRINGS,
    assistant_replies,
    deterministic_round_score,
    memory_tool_calls,
    tool_calls,
)


def run_evaluation(
    config: ChatMemoryEvalConfig,
    *,
    run_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    run_timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    run_id = _resolve_run_id(run_id, run_timestamp)
    csv_path = config.output_dir / f"chat_memory_eval_{run_timestamp}.csv"
    jsonl_path = config.output_dir / f"chat_memory_eval_{run_timestamp}.jsonl"
    summary_path = config.output_dir / f"chat_memory_eval_{run_timestamp}_summary.json"
    provenance_path = (
        config.output_dir / f"chat_memory_eval_{run_timestamp}_provenance.json"
    )
    config.output_dir.mkdir(parents=True, exist_ok=True)

    fixture = load_fixture(config.fixtures_dir, config.fixture_key)
    rows: list[dict[str, Any]] = []
    with AdeApiClient(
        base_url=config.api_base_url,
        timeout_seconds=ade_api_timeout_seconds(config),
        api_key=os.getenv("ADE_API_ADMIN_KEY", ""),
    ) as api:
        options = api.options()
        validate_chat_options(options, config)
        provenance = capture_evaluation_provenance(
            run_id=run_id,
            api=api,
            options=options,
            config=config,
            fixture=fixture,
        )
        write_provenance(provenance_path, provenance)
        print(
            f"[INFO] Running {config.rounds} chat-memory rounds with "
            f"{len(fixture.turns)} turns each."
        )
        print(f"[INFO] Streaming CSV to {csv_path}")
        with ArtifactWriter(csv_path=csv_path, jsonl_path=jsonl_path) as writer:
            for round_index in range(1, config.rounds + 1):
                print(f"[{round_index}/{config.rounds}] starting")
                row, raw = run_round(
                    api=api,
                    config=config,
                    fixture=fixture,
                    run_id=run_id,
                    round_index=round_index,
                    provenance=provenance,
                )
                rows.append(row)
                writer.write_round(row, raw)
                print(
                    f"[{round_index}/{config.rounds}] status={row['status']} "
                    f"pass={row['pass']} elapsed={row['elapsed_seconds']}s"
                )
                if config.stop_on_error and row["status"] == "error":
                    break

    summary = build_summary(
        run_id=run_id,
        csv_path=csv_path,
        jsonl_path=jsonl_path,
        summary_path=summary_path,
        rows=rows,
    )
    summary["config"] = _config_payload(config)
    summary["fixture"] = _fixture_payload(fixture)
    summary["provenance"] = provenance
    summary["provenance_path"] = str(provenance_path)
    write_summary(summary_path, summary)
    print_summary(summary)
    return summary


def validate_chat_options(
    payload: dict[str, Any], config: ChatMemoryEvalConfig
) -> None:
    selections = (
        ("model", config.model, _option_keys(payload.get("models"))),
        ("prompt_key", config.prompt_key, _option_keys(payload.get("prompts"))),
        ("persona_key", config.persona_key, _option_keys(payload.get("personas"))),
        ("embedding", config.embedding, _option_keys(payload.get("embeddings"))),
    )
    for label, selected, available in selections:
        if selected and selected not in available:
            raise ValueError(
                f"{label} '{selected}' is unavailable from the chat options endpoint"
            )


def run_round(
    *,
    api: AdeApiClient,
    config: ChatMemoryEvalConfig,
    fixture: ConversationFixture,
    run_id: str,
    round_index: int,
    provenance: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.time()
    session_id = ""
    purged = False
    row: dict[str, Any]
    raw: dict[str, Any]
    try:
        created = api.create_evaluation_session(
            _create_session_payload(config, run_id, round_index)
        )
        conversation = created.get("conversation")
        if not isinstance(conversation, dict):
            raise RuntimeError("Evaluation session did not return a conversation")
        session_id = str(created.get("session_id") or conversation.get("id") or "")
        if not session_id:
            raise RuntimeError("Evaluation session did not return a session id")
        assert_created_session_identity(created, provenance)

        initial_state = api.evaluation_state(session_id)
        initial_memory = _memory_text_from_state(initial_state)
        turn_records, assistant_texts, final_state = _run_turns(
            api=api,
            session_id=session_id,
            config=config,
            fixture=fixture,
            run_id=run_id,
            round_index=round_index,
            initial_memory=initial_memory,
        )
        final_memory = _memory_text_from_state(final_state)
        score = deterministic_round_score(
            assistant_texts=assistant_texts,
            initial_human_memory=initial_memory,
            final_human_memory=final_memory,
            expected_facts=fixture.expected_facts,
            forbidden_reply_substrings=_forbidden_substrings(fixture),
        )
        judge_payload = _run_judge_if_enabled(
            config=config,
            fixture=fixture,
            turn_records=turn_records,
            final_human_memory=final_memory,
        )
        row = _round_row(
            run_id=run_id,
            round_index=round_index,
            config=config,
            fixture=fixture,
            status="ok",
            passed=bool(score["pass"]),
            elapsed_seconds=time.time() - started,
            session_id=session_id,
            score=score,
            judge_payload=judge_payload,
            turn_records=turn_records,
            error="",
            provenance=provenance,
        )
        raw = {
            **row,
            "turns": turn_records,
            "initial_human_memory": initial_memory,
            "final_human_memory": final_memory,
            "deterministic_score": score,
            "judge": judge_payload,
            "evaluation_state": final_state,
        }
    except Exception as exc:
        score = deterministic_round_score(
            assistant_texts=[],
            initial_human_memory="",
            final_human_memory="",
            expected_facts=fixture.expected_facts,
            forbidden_reply_substrings=_forbidden_substrings(fixture),
        )
        row = _error_row(
            run_id=run_id,
            round_index=round_index,
            config=config,
            fixture=fixture,
            elapsed_seconds=time.time() - started,
            session_id=session_id,
            error=str(exc),
            provenance=provenance,
            score=score,
        )
        raw = {
            **row,
            "turns": [],
            "initial_human_memory": "",
            "final_human_memory": "",
            "deterministic_score": score,
            "judge": {"ok": False, "skipped": True},
            "evaluation_state": {},
        }
    finally:
        if session_id and not config.keep_agents:
            try:
                api.purge_evaluation_session(session_id)
                purged = True
            except Exception as exc:
                print(f"[WARN] Failed to purge evaluation session {session_id}: {exc}")
            row["purged"] = purged
            raw["purged"] = purged
    return row, raw


def _run_turns(
    *,
    api: AdeApiClient,
    session_id: str,
    config: ChatMemoryEvalConfig,
    fixture: ConversationFixture,
    run_id: str,
    round_index: int,
    initial_memory: str,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    replies: list[str] = []
    before_memory = initial_memory
    final_state: dict[str, Any] = {}
    for turn_index, user_input in enumerate(fixture.turns, 1):
        started = time.time()
        result = api.run_turn(
            conversation_id=session_id,
            message=user_input,
            idempotency_key=f"{run_id}-round-{round_index}-turn-{turn_index}",
            timeout_seconds=config.timeout_seconds,
            retry_count=config.retry_count,
        )
        final_state = result["state"]
        run = result["run"]
        events = result["events"]
        sequence = _sequence_from_result(final_state, events, str(run.get("id") or ""))
        turn_replies = assistant_replies(sequence)
        replies.extend(turn_replies)
        after_memory = _memory_text_from_state(final_state)
        records.append(
            {
                "turn_index": turn_index,
                "user_input": user_input,
                "assistant_replies": turn_replies,
                "elapsed_seconds": round(time.time() - started, 3),
                "memory_changed_this_turn": before_memory != after_memory,
                "human_memory_before_turn": before_memory,
                "human_memory_after_turn": after_memory,
                "tool_calls": tool_calls(sequence),
                "memory_tool_calls": memory_tool_calls(sequence),
                "sequence": sequence,
                "run": run,
                "events": events,
            }
        )
        before_memory = after_memory
    return records, replies, final_state


def _sequence_from_result(
    state: dict[str, Any], events: object, run_id: str
) -> list[dict[str, Any]]:
    sequence: list[dict[str, Any]] = []
    messages = (state.get("conversation") or {}).get("messages", [])
    for message in reversed(messages if isinstance(messages, list) else []):
        if (
            isinstance(message, dict)
            and message.get("role") == "assistant"
            and str(message.get("run_id") or "") == run_id
        ):
            sequence.append(
                {"type": "assistant", "content": message.get("content", "")}
            )
            break
    for event in events if isinstance(events, list) else []:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("type") or "")
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if event_type == "tool.call.requested":
            sequence.append(
                {
                    "type": "tool_call",
                    "name": str(payload.get("name") or ""),
                    "arguments": json.dumps(
                        payload.get("arguments") or {}, ensure_ascii=False
                    ),
                }
            )
        elif event_type == "memory.committed":
            sequence.append(
                {
                    "type": "tool_call",
                    "name": "memory.commit",
                    "arguments": json.dumps(payload, ensure_ascii=False),
                }
            )
    return sequence


def _memory_text_from_state(state: dict[str, Any]) -> str:
    facts = (state.get("memories") or {}).get("facts", [])
    if not isinstance(facts, list):
        return ""
    rows = []
    for fact in facts:
        if not isinstance(fact, dict) or fact.get("status") != "active":
            continue
        value = str(fact.get("value") or "").strip()
        if not value:
            continue
        label = str(
            fact.get("qualifier") or fact.get("fact_type") or fact.get("key") or ""
        )
        rows.append(f"{label}: {value}" if label else value)
    return "\n".join(rows)


def _run_judge_if_enabled(
    *,
    config: ChatMemoryEvalConfig,
    fixture: ConversationFixture,
    turn_records: list[dict[str, Any]],
    final_human_memory: str,
) -> dict[str, Any]:
    if not config.judge_enabled:
        return {"ok": False, "skipped": True}
    return judge_round(
        router_v1_base_url=router_v1_base_url(config),
        router_api_key=config.model_router_api_key,
        model_key=effective_judge_model_key(config),
        fixture=_fixture_payload(fixture),
        turn_records=turn_records,
        final_human_memory=final_human_memory,
        timeout_seconds=config.judge_timeout_seconds,
    )


def _create_session_payload(
    config: ChatMemoryEvalConfig, run_id: str, round_index: int
) -> dict[str, Any]:
    return {
        "idempotency_key": f"{run_id}-round-{round_index}-session",
        "title": f"Chat memory evaluation round {round_index}",
        "model_key": config.model,
        "reviewer_model_key": config.model,
        "embedding_model_key": config.embedding,
        "prompt_key": config.prompt_key,
        "persona_key": config.persona_key,
        "tool_names": ["search_memory"],
        "subject_external_key": f"evaluation:{run_id}:round:{round_index}",
        "subject_display_name": f"Evaluation subject {round_index}",
    }


def _round_row(**values: Any) -> dict[str, Any]:
    score = values["score"]
    judge = values["judge_payload"]
    turns = values["turn_records"]
    identities = expected_agent_identities(values["provenance"])
    return {
        "run_id": values["run_id"],
        "round": values["round_index"],
        "status": values["status"],
        "pass": values["passed"],
        "elapsed_seconds": round(float(values["elapsed_seconds"]), 3),
        "model": values["config"].model,
        "prompt_key": values["config"].prompt_key,
        "persona_key": values["config"].persona_key,
        "embedding": values["config"].embedding,
        "fixture_key": values["fixture"].key,
        "configuration_sha256": values["provenance"]["configuration_sha256"],
        "provenance_sha256": values["provenance"]["provenance_sha256"],
        "model_identity_sha256": identities["model_identity_sha256"],
        "embedding_identity_sha256": identities["embedding_identity_sha256"],
        "prompt_content_sha256": identities["prompt_content_sha256"],
        "persona_content_sha256": identities["persona_content_sha256"],
        "turn_count": len(turns),
        "assistant_reply_count": sum(len(item["assistant_replies"]) for item in turns),
        "forbidden_hit_count": int(score["forbidden_hit_count"]),
        "human_memory_changed": bool(score["human_memory_changed"]),
        "expected_facts_passed": bool(score["expected_facts_passed"]),
        "missing_expected_facts": ",".join(score["missing_expected_facts"]),
        "memory_tool_call_count": sum(len(item["memory_tool_calls"]) for item in turns),
        "total_tool_call_count": sum(len(item["tool_calls"]) for item in turns),
        "judge_enabled": values["config"].judge_enabled,
        "judge_ok": bool(judge.get("ok", False)),
        "judge_pass": judge.get("pass", ""),
        "judge_score": judge.get("score", ""),
        "session_id": values["session_id"],
        "purged": False,
        "error": values["error"],
    }


def _error_row(**values: Any) -> dict[str, Any]:
    return _round_row(
        **values,
        status="error",
        passed=False,
        judge_payload={"ok": False},
        turn_records=[],
    )


def _option_keys(items: object) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {
        str(item.get("key") or "").strip() for item in items if isinstance(item, dict)
    }


def _forbidden_substrings(fixture: ConversationFixture) -> tuple[str, ...]:
    return fixture.forbidden_reply_substrings or DEFAULT_FORBIDDEN_REPLY_SUBSTRINGS


def _fixture_payload(fixture: ConversationFixture) -> dict[str, Any]:
    return {
        "key": fixture.key,
        "description": fixture.description,
        "turns": list(fixture.turns),
        "expected_facts": [asdict(item) for item in fixture.expected_facts],
        "forbidden_reply_substrings": list(_forbidden_substrings(fixture)),
    }


def _config_payload(config: ChatMemoryEvalConfig) -> dict[str, Any]:
    payload = asdict(config)
    for key, value in list(payload.items()):
        if isinstance(value, Path):
            payload[key] = str(value)
    if payload.get("model_router_api_key"):
        payload["model_router_api_key"] = "***"
    return payload


def _resolve_run_id(run_id: str | None, run_timestamp: str) -> str:
    provided = str(run_id or "").strip()
    return provided or f"chat-memory-eval-{run_timestamp}-{uuid4().hex[:8]}"
