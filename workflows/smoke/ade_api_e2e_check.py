"""Lean end-to-end smoke check for the current ADE stack.

The check intentionally creates data only through the evaluation-session API.
That API owns the isolated definition, subject, and conversation graph, and its
idempotent purge endpoint is the only cleanup path used here.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from typing import Any

import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from workflows.smoke.config_defaults import (
    DEFAULT_ADE_API_BASE_URL,
    DEFAULT_EMBEDDING_MODEL_KEY,
    DEFAULT_PROMPT_KEY,
    DEFAULT_TEST_MODEL_KEY,
    ade_api_headers,
)


ADE_API_BASE_URL = os.getenv("ADE_API_BASE_URL", DEFAULT_ADE_API_BASE_URL).rstrip("/")
ADE_API_CLIENT_TIMEOUT_SECONDS = float(
    os.getenv("ADE_API_CLIENT_TIMEOUT_SECONDS", "180")
)
SMOKE_TURN_TIMEOUT_SECONDS = float(
    os.getenv("ADE_CURRENT_STACK_SMOKE_TURN_TIMEOUT_SECONDS", "180")
)
TERMINAL_RUN_STATUSES = frozenset({"succeeded", "failed", "cancelled"})


class SmokeCheckError(RuntimeError):
    pass


def _as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _require_object(response: httpx.Response, *, step: str) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise SmokeCheckError(f"{step} returned a non-object JSON payload")
    return payload


def _option_key(
    payload: dict[str, Any],
    *,
    collection: str,
    fallback: str = "",
    require_router_key: bool = False,
) -> str:
    defaults = payload.get("defaults", {})
    default_key = (
        str(defaults.get(_default_name(collection), "") or "").strip()
        if isinstance(defaults, dict)
        else ""
    )
    items = payload.get(collection, [])
    if not isinstance(items, list):
        raise SmokeCheckError(f"options.{collection} must be a list")

    available = [
        str(item.get("key", "") or "").strip()
        for item in items
        if isinstance(item, dict)
        and bool(item.get("available", True))
        and str(item.get("key", "") or "").strip()
    ]
    key = default_key if default_key in available else ""
    if not key and fallback in available:
        key = fallback
    if not key and available:
        key = available[0]
    if not key:
        raise SmokeCheckError(f"options has no available {collection}")
    if require_router_key:
        _require_canonical_router_key(key, collection=collection)
    return key


def _default_name(collection: str) -> str:
    return {
        "models": "model",
        "embeddings": "embedding",
        "prompts": "prompt_key",
        "personas": "persona_key",
        "schemas": "schema_key",
    }.get(collection, collection.rstrip("s"))


def _require_canonical_router_key(value: str, *, collection: str) -> None:
    if "::" not in value or value.startswith(("openai-proxy/", "letta/")):
        raise SmokeCheckError(
            f"{collection} must use a canonical Model Router key, got {value!r}"
        )


def _load_options(http: httpx.Client, scenario: str) -> dict[str, Any]:
    return _require_object(
        http.get(
            "/api/v2/model-catalog/options",
            params={"scenario": scenario, "refresh": "true"},
        ),
        step=f"{scenario} model options",
    )


def _require_removed_routes(http: httpx.Client) -> dict[str, int]:
    # These paths belonged to the retired Letta/Tool Center and generic-runtime
    # surfaces. A 404 proves the old capability cannot be used accidentally.
    paths = (
        "/api/v2/agent-studio/agents",
        "/api/v2/tool-center/runtime-tools",
        "/api/v2/tool-center/invocations",
        "/api/v3/agent-definitions",
        "/api/v3/memory-subjects",
        "/api/v3/conversations",
    )
    statuses: dict[str, int] = {}
    for path in paths:
        response = http.get(path)
        statuses[path] = response.status_code
        if response.status_code != 404:
            raise SmokeCheckError(
                f"retired route {path} must return 404, got {response.status_code}"
            )
    return statuses


def _wait_for_run(http: httpx.Client, run_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + SMOKE_TURN_TIMEOUT_SECONDS + 30
    while time.monotonic() < deadline:
        run = _require_object(http.get(f"/api/v3/runs/{run_id}"), step="runtime run")
        status = str(run.get("status", "") or "")
        if status in TERMINAL_RUN_STATUSES:
            if status != "succeeded":
                raise SmokeCheckError(
                    "evaluation-session turn failed: "
                    f"status={status} code={run.get('error_code') or 'unknown'}"
                )
            return run
        time.sleep(0.25)
    raise SmokeCheckError(f"runtime run {run_id} exceeded the smoke deadline")


def _safe_purge_evaluation_session(
    conversation_id: str | None,
) -> dict[str, Any] | None:
    if not conversation_id:
        return None
    try:
        with httpx.Client(
            base_url=ADE_API_BASE_URL,
            timeout=30.0,
            headers=ade_api_headers(),
        ) as http:
            response = http.delete(f"/api/v3/evaluation-sessions/{conversation_id}")
            if response.status_code >= 400:
                return {"ok": False, "status": response.status_code}
            payload = response.json()
            return payload if isinstance(payload, dict) else {"ok": False}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc)}


def main() -> None:
    summary: dict[str, Any] = {
        "name": "ade_api_e2e_check",
        "ok": False,
        "steps": {},
        "detail": "",
    }
    conversation_id: str | None = None
    purged = False

    try:
        with httpx.Client(
            base_url=ADE_API_BASE_URL,
            timeout=ADE_API_CLIENT_TIMEOUT_SECONDS,
            headers=ade_api_headers(),
        ) as http:
            health = _require_object(http.get("/api/v2/health"), step="API health")
            summary["steps"]["health"] = {"ok": True, "status": health.get("status")}

            worker_health = _require_object(
                http.get("/api/v3/worker-health"), step="runtime worker health"
            )
            if not bool(worker_health.get("worker_ready")):
                raise SmokeCheckError("runtime worker is not ready")
            summary["steps"]["runtime_worker"] = {
                "ok": True,
                "compatible_worker_count": worker_health.get("compatible_worker_count"),
            }

            chat_options = _load_options(http, "chat")
            comment_options = _load_options(http, "comment")
            label_options = _load_options(http, "label")
            chat_model_key = _option_key(
                chat_options,
                collection="models",
                fallback=DEFAULT_TEST_MODEL_KEY,
                require_router_key=True,
            )
            embedding_model_key = _option_key(
                chat_options,
                collection="embeddings",
                fallback=DEFAULT_EMBEDDING_MODEL_KEY,
                require_router_key=True,
            )
            chat_prompt_key = _option_key(
                chat_options, collection="prompts", fallback=DEFAULT_PROMPT_KEY
            )
            chat_persona_key = _option_key(chat_options, collection="personas")
            comment_model_key = _option_key(
                comment_options,
                collection="models",
                fallback=DEFAULT_TEST_MODEL_KEY,
                require_router_key=True,
            )
            comment_prompt_key = _option_key(comment_options, collection="prompts")
            comment_persona_key = _option_key(comment_options, collection="personas")
            label_model_key = _option_key(
                label_options,
                collection="models",
                fallback=DEFAULT_TEST_MODEL_KEY,
                require_router_key=True,
            )
            label_prompt_key = _option_key(label_options, collection="prompts")
            label_schema_key = _option_key(label_options, collection="schemas")
            summary["steps"]["model_options"] = {
                "ok": True,
                "chat_model_key": chat_model_key,
                "comment_model_key": comment_model_key,
                "label_model_key": label_model_key,
                "embedding_model_key": embedding_model_key,
            }

            prompt_catalog = _require_object(
                http.get("/api/v2/prompt-center/catalog", params={"scenario": "chat"}),
                step="Prompt Center catalog",
            )
            if not prompt_catalog.get("prompts") or not prompt_catalog.get("personas"):
                raise SmokeCheckError(
                    "Prompt Center chat catalog is unexpectedly empty"
                )
            schema_catalog = _require_object(
                http.get("/api/v2/schema-center/label-schemas"),
                step="Schema Center catalog",
            )
            if not schema_catalog.get("items"):
                raise SmokeCheckError("Schema Center catalog is unexpectedly empty")
            agent_studio_options = _require_object(
                http.get("/api/v3/agent-studio/options"), step="Agent Studio options"
            )
            if agent_studio_options.get("runtime") != "ade_native":
                raise SmokeCheckError(
                    "Agent Studio did not report the native ADE runtime"
                )
            summary["steps"]["product_catalogs"] = {
                "ok": True,
                "chat_prompt_key": chat_prompt_key,
                "chat_persona_key": chat_persona_key,
                "label_schema_key": label_schema_key,
            }

            comment = _require_object(
                http.post(
                    "/api/v2/comment-lab/generations",
                    json={
                        "scenario": "comment",
                        "input": "请用一句话概括这条读者反馈：这项服务很容易上手。",
                        "prompt_key": comment_prompt_key,
                        "persona_key": comment_persona_key,
                        "model_key": comment_model_key,
                        "max_tokens": 96,
                        "timeout_seconds": SMOKE_TURN_TIMEOUT_SECONDS,
                        "retry_count": 0,
                    },
                ),
                step="Comment Lab generation",
            )
            if not str(comment.get("content", "") or "").strip():
                raise SmokeCheckError("Comment Lab returned empty content")
            summary["steps"]["comment_lab"] = {
                "ok": True,
                "model_key": comment.get("model_key"),
            }

            label = _require_object(
                http.post(
                    "/api/v2/label-lab/generations",
                    json={
                        "scenario": "label",
                        "input": "张伟在多伦多与同事讨论了新的天气预报服务。",
                        "prompt_key": label_prompt_key,
                        "schema_key": label_schema_key,
                        "model_key": label_model_key,
                        "max_tokens": 128,
                        "timeout_seconds": SMOKE_TURN_TIMEOUT_SECONDS,
                        "repair_retry_count": 0,
                    },
                ),
                step="Label Lab generation",
            )
            if not isinstance(label.get("result"), dict):
                raise SmokeCheckError("Label Lab did not return a structured result")
            summary["steps"]["label_lab"] = {
                "ok": True,
                "model_key": label.get("model_key"),
            }

            session = _require_object(
                http.post(
                    "/api/v3/evaluation-sessions",
                    json={
                        "idempotency_key": f"current-stack-smoke-{uuid.uuid4()}",
                        "title": "Current stack smoke",
                        "model_key": chat_model_key,
                        "reviewer_model_key": chat_model_key,
                        "embedding_model_key": embedding_model_key,
                        "prompt_key": chat_prompt_key,
                        "persona_key": chat_persona_key,
                        "tool_names": ["search_memory"],
                    },
                ),
                step="evaluation-session creation",
            )
            conversation = session.get("conversation", {})
            conversation_id = str(conversation.get("id", "") or "")
            if not conversation_id:
                raise SmokeCheckError(
                    "evaluation session did not return a conversation id"
                )
            if conversation.get("purpose") != "evaluation":
                raise SmokeCheckError(
                    "evaluation session did not retain evaluation purpose"
                )

            accepted = _require_object(
                http.post(
                    f"/api/v3/conversations/{conversation_id}/turns",
                    json={
                        "content": "你好，请简短确认当前运行正常。",
                        "idempotency_key": f"current-stack-turn-{uuid.uuid4()}",
                        "timeout_seconds": SMOKE_TURN_TIMEOUT_SECONDS,
                        "retry_count": 0,
                    },
                ),
                step="evaluation-session turn",
            )
            run_id = str(accepted.get("run_id", "") or "")
            if not run_id:
                raise SmokeCheckError("evaluation turn did not return a run id")
            run = _wait_for_run(http, run_id)
            events = _require_object(
                http.get(f"/api/v3/runs/{run_id}/event-log", params={"limit": 200}),
                step="runtime event log",
            )
            if not events.get("items"):
                raise SmokeCheckError("runtime event log is unexpectedly empty")
            state = _require_object(
                http.get(f"/api/v3/evaluation-sessions/{conversation_id}/state"),
                step="evaluation-session state",
            )
            if state.get("conversation", {}).get("id") != conversation_id:
                raise SmokeCheckError(
                    "evaluation-session state returned another conversation"
                )
            summary["steps"]["evaluation_session"] = {
                "ok": True,
                "run_id": run_id,
                "attempt_count": run.get("attempt_count"),
                "event_count": len(events.get("items", [])),
            }

            first_purge = _require_object(
                http.delete(f"/api/v3/evaluation-sessions/{conversation_id}"),
                step="evaluation-session purge",
            )
            second_purge = _require_object(
                http.delete(f"/api/v3/evaluation-sessions/{conversation_id}"),
                step="idempotent evaluation-session purge",
            )
            if bool(first_purge.get("already_purged")) or not bool(
                second_purge.get("already_purged")
            ):
                raise SmokeCheckError("evaluation-session purge is not idempotent")
            purged = True
            summary["steps"]["evaluation_cleanup"] = {"ok": True}

            summary["steps"]["retired_routes"] = {
                "ok": True,
                "statuses": _require_removed_routes(http),
            }

        summary["ok"] = True
        summary["detail"] = "current ADE stack smoke passed"
    except Exception as exc:
        summary["detail"] = str(exc)
        raise
    finally:
        if conversation_id and not purged:
            summary["steps"]["evaluation_cleanup"] = _safe_purge_evaluation_session(
                conversation_id
            )
        print(_as_json(summary))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[FAIL] ade_api_e2e_check: {exc}")
        raise
