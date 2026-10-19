from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .artifacts import ArtifactWriter, build_summary, print_summary, row_id
from .config import (
    ConfigError,
    EvalConfig,
    apply_cli_overrides,
    load_config,
    project_path,
)


class ApiRequestError(RuntimeError):
    pass


class TransientApiError(ApiRequestError):
    pass


def fetch_comment_personas(
    client: httpx.Client, config: EvalConfig
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"scenario": "comment"}
    if config.persona_search:
        params["search"] = config.persona_search
    payload = _request_json(
        client,
        "GET",
        "/api/v2/prompt-center/personas",
        retry_count=config.api_retry_count,
        params=params,
    )
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        raise ApiRequestError("Persona API response did not include an items list")

    personas = [
        item
        for item in items
        if isinstance(item, dict)
        and str(item.get("key", "") or "").startswith("comment_")
        and not bool(item.get("archived", False))
    ]
    if config.persona_keys:
        wanted = set(config.persona_keys)
        personas = [
            item for item in personas if str(item.get("key", "") or "") in wanted
        ]
        missing = sorted(wanted - {str(item.get("key", "") or "") for item in personas})
        if missing:
            raise ConfigError(
                f"Requested persona keys were not returned by the API: {', '.join(missing)}"
            )
    if config.limit:
        personas = personas[: config.limit]
    if not personas:
        raise ConfigError("No active comment personas matched the config")
    return personas


def validate_comment_options(client: httpx.Client, config: EvalConfig) -> None:
    payload = _request_json(
        client,
        "GET",
        "/api/v2/model-catalog/options",
        retry_count=config.api_retry_count,
        params={"scenario": "comment"},
    )
    models = payload.get("models", []) if isinstance(payload, dict) else []
    prompts = payload.get("prompts", []) if isinstance(payload, dict) else []
    model_keys = {
        str(item.get("key") or item.get("model_key") or "").strip()
        for item in models
        if isinstance(item, dict)
    }
    prompt_keys = {
        str(item.get("key") or "").strip() for item in prompts if isinstance(item, dict)
    }
    if config.model_key not in model_keys:
        raise ConfigError(
            f"model_key '{config.model_key}' is not available from /api/v2/model-catalog/options?scenario=comment. "
            f"Available examples: {', '.join(sorted(model_keys)[:10])}"
        )
    if config.prompt_key not in prompt_keys:
        raise ConfigError(
            f"prompt_key '{config.prompt_key}' is not available from /api/v2/model-catalog/options?scenario=comment. "
            f"Available prompts: {', '.join(sorted(prompt_keys))}"
        )


def run_evaluation(
    config: EvalConfig, *, now: datetime | None = None
) -> dict[str, Any]:
    run_timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    run_id = f"comment-persona-eval-{run_timestamp}-{uuid4().hex[:8]}"
    csv_path = config.output_dir / f"comment_persona_eval_{run_timestamp}.csv"
    jsonl_path = config.output_dir / f"comment_persona_eval_{run_timestamp}.jsonl"
    config.output_dir.mkdir(parents=True, exist_ok=True)

    news_text = config.news_path.read_text(encoding="utf-8").strip()
    if not news_text:
        raise ConfigError(f"news_path is empty: {config.news_path}")

    timeout = max(config.timeout_seconds + 30, 60)
    rows: list[dict[str, Any]] = []
    api_key = config.api_key
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    with httpx.Client(
        base_url=config.api_base_url, timeout=timeout, headers=headers
    ) as client:
        validate_comment_options(client, config)
        personas = fetch_comment_personas(client, config)
        total_attempts = len(personas) * config.rounds
        attempt_number = 0
        print(
            f"[INFO] Running {total_attempts} attempts across {len(personas)} personas x {config.rounds} rounds."
        )
        print(f"[INFO] Streaming CSV to {csv_path}")
        print(f"[INFO] Streaming JSONL to {jsonl_path}")
        with ArtifactWriter(
            csv_path=csv_path, jsonl_path=jsonl_path
        ) as artifact_writer:
            for round_number in range(1, config.rounds + 1):
                for persona in personas:
                    attempt_number += 1
                    persona_key = str(persona.get("key", "") or "")
                    print(
                        f"[{attempt_number}/{total_attempts}] round={round_number} persona={persona_key}",
                        flush=True,
                    )
                    row, raw_record = run_attempt(
                        client,
                        config=config,
                        run_id=run_id,
                        round_number=round_number,
                        persona=persona,
                        news_text=news_text,
                    )
                    rows.append(row)
                    artifact_writer.write_attempt(row, raw_record)
                    print(
                        f"[{attempt_number}/{total_attempts}] status={row['status']} "
                        f"elapsed={row['elapsed_seconds']}s",
                        flush=True,
                    )
                    if row["status"] == "error" and config.stop_on_error:
                        return build_summary(run_id, csv_path, jsonl_path, rows)
    return build_summary(run_id, csv_path, jsonl_path, rows)


def run_attempt(
    client: httpx.Client,
    *,
    config: EvalConfig,
    run_id: str,
    round_number: int,
    persona: dict[str, Any],
    news_text: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    persona_key = str(persona.get("key", "") or "")
    request_payload = {
        "scenario": "comment",
        "input": news_text,
        "prompt_key": config.prompt_key,
        "persona_key": persona_key,
        "model_key": config.model_key,
        "max_tokens": config.max_tokens,
        "timeout_seconds": config.timeout_seconds,
        "retry_count": config.retry_count,
        "task_shape": config.task_shape,
        "cache_prompt": config.cache_prompt,
        "enable_thinking": config.enable_thinking,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "top_k": config.top_k,
        "include_diagnostics": True,
    }
    started = time.perf_counter()
    response_payload: dict[str, Any] | None = None
    error = ""
    status = "ok"
    try:
        response_payload = _request_json(
            client,
            "POST",
            "/api/v2/comment-lab/generations",
            retry_count=config.api_retry_count,
            json=request_payload,
        )
    except Exception as exc:
        status = "error"
        error = str(exc)
    elapsed = round(time.perf_counter() - started, 3)

    row = _row_from_result(
        run_id=run_id,
        round_number=round_number,
        persona=persona,
        config=config,
        elapsed_seconds=elapsed,
        status=status,
        response_payload=response_payload,
        error=error,
    )
    raw_record = {
        "row_id": row_id(row),
        "run_id": run_id,
        "round": round_number,
        "persona": persona,
        "request": request_payload,
        "status": status,
        "elapsed_seconds": elapsed,
        "response": response_payload,
        "error": error,
    }
    return row, raw_record


def _request_json(
    client: httpx.Client, method: str, path: str, *, retry_count: int, **kwargs: Any
) -> dict[str, Any]:
    retrying = Retrying(
        stop=stop_after_attempt(1 + retry_count),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.TransportError, TransientApiError)
        ),
        reraise=True,
    )
    for attempt in retrying:
        with attempt:
            response = client.request(method, path, **kwargs)
            if response.status_code >= 500:
                raise TransientApiError(_response_error(response))
            if response.status_code >= 400:
                raise ApiRequestError(_response_error(response))
            try:
                data = response.json()
            except json.JSONDecodeError as exc:
                raise ApiRequestError(
                    f"{method} {path} did not return valid JSON"
                ) from exc
            if not isinstance(data, dict):
                raise ApiRequestError(f"{method} {path} did not return a JSON object")
            return data
    raise ApiRequestError(f"{method} {path} failed without returning a response")


def _row_from_result(
    *,
    run_id: str,
    round_number: int,
    persona: dict[str, Any],
    config: EvalConfig,
    elapsed_seconds: float,
    status: str,
    response_payload: dict[str, Any] | None,
    error: str,
) -> dict[str, Any]:
    response = response_payload or {}
    usage = (
        response.get("usage", {}) if isinstance(response.get("usage", {}), dict) else {}
    )
    raw_reply = (
        response.get("raw_reply", {})
        if isinstance(response.get("raw_reply", {}), dict)
        else {}
    )
    timings = (
        raw_reply.get("timings", {})
        if isinstance(raw_reply.get("timings", {}), dict)
        else {}
    )
    reasoning_text = _reasoning_text(raw_reply)
    content = str(response.get("content", "") or "")
    return {
        "run_id": run_id,
        "round": round_number,
        "persona_key": str(persona.get("key", "") or ""),
        "persona_label": str(persona.get("label", "") or ""),
        "persona_description": str(persona.get("description", "") or ""),
        "status": status,
        "elapsed_seconds": elapsed_seconds,
        "content": content,
        "content_length": len(content),
        "finish_reason": str(response.get("finish_reason", "") or ""),
        "content_source": str(response.get("content_source", "") or ""),
        "usage_prompt_tokens": _usage_int(usage, "prompt_tokens"),
        "usage_completion_tokens": _usage_int(usage, "completion_tokens"),
        "usage_total_tokens": _usage_int(usage, "total_tokens"),
        "error": error,
        "model_key": config.model_key,
        "prompt_key": config.prompt_key,
        "task_shape": config.task_shape,
        "cache_prompt": config.cache_prompt,
        "enable_thinking": config.enable_thinking,
        "temperature": config.temperature,
        "top_p": config.top_p,
        "top_k": config.top_k,
        "max_tokens": config.max_tokens,
        "timeout_seconds": config.timeout_seconds,
        "retry_count": config.retry_count,
        "reasoning_length": len(reasoning_text),
        "usage_reasoning_tokens": _usage_reasoning_tokens(usage),
        "timings_cache_n": _usage_int(timings, "cache_n"),
        "timings_prompt_n": _usage_int(timings, "prompt_n"),
        "timings_predicted_n": _usage_int(timings, "predicted_n"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate Comment Lab output across SQLite-backed comment personas."
    )
    parser.add_argument(
        "--config", default="workflows/evals/comment_persona_eval/config.toml"
    )
    parser.add_argument("--api-base-url", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--persona-key", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = apply_cli_overrides(load_config(project_path(args.config)), args)
        summary = run_evaluation(config)
    except Exception as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    print_summary(summary)
    return 0


def _usage_int(usage: dict[str, Any], key: str) -> int:
    try:
        return int(usage.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _usage_reasoning_tokens(usage: dict[str, Any]) -> int:
    details = usage.get("completion_tokens_details", {})
    if not isinstance(details, dict):
        return 0
    return _usage_int(details, "reasoning_tokens")


def _reasoning_text(raw_reply: dict[str, Any]) -> str:
    choices = raw_reply.get("choices", [])
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0] if isinstance(choices[0], dict) else {}
    message = first_choice.get("message", {})
    if not isinstance(message, dict):
        return ""
    return str(message.get("reasoning") or message.get("reasoning_content") or "")


def _response_error(response: httpx.Response) -> str:
    try:
        detail = response.json()
    except Exception:
        detail = response.text
    return f"{response.request.method} {response.request.url.path} returned {response.status_code}: {detail}"


if __name__ == "__main__":
    raise SystemExit(main())
