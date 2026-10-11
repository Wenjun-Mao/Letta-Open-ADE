"""HTTP recall against the source-pinned Hindsight 0.10.3 contract."""

from __future__ import annotations

import time
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from .hindsight_eval_capture import EvaluationCapture
from .hindsight_eval_contracts import (
    ATTRIBUTION_METADATA_KEYS,
    EvaluationError,
    EvaluationInput,
    RecalledMemory,
)
from .hindsight_eval_trace import qualify_reranking


def service_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise EvaluationError("invalid_service_url")
    return value.rstrip("/")


def recall_request(inputs: EvaluationInput) -> dict:
    # The pinned server's IncludeOptions accepts null to disable each supplement.
    # Entities attached to each result remain available without global entity views.
    return {
        "query": inputs.query,
        "query_timestamp": inputs.query_timestamp,
        "types": inputs.recall_types,
        "budget": inputs.recall_budget,
        "max_tokens": inputs.recall_max_tokens,
        "tags": inputs.scope.tags,
        "tags_match": "any_strict",
        "prefer_observations": False,
        "trace": True,
        "include": {"entities": None, "chunks": None, "source_facts": None},
    }


class HindsightRecall:
    def __init__(self, client: httpx.AsyncClient, *, base_url: str, api_key: str):
        self.client = client
        self.base_url = service_url(base_url)
        if not api_key.strip():
            raise EvaluationError("hindsight_credentials_missing")
        self.api_key = api_key

    async def recall(
        self, inputs: EvaluationInput, *, capture: EvaluationCapture
    ) -> tuple[list[RecalledMemory], dict]:
        payload = recall_request(inputs)
        path = f"/v1/default/banks/{inputs.scope.bank_id}/memories/recall"
        started = time.monotonic()
        capture.write(
            "hindsight.recall-request.json", {"request_path": path, "request": payload}
        )
        try:
            # No automatic retry or failure-to-empty fallback.
            response = await self.client.post(
                self.base_url + path,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=inputs.recall_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            capture.write(
                "hindsight.recall-failure.json",
                {
                    "error_type": type(exc).__name__,
                    "http_status": exc.response.status_code
                    if isinstance(exc, httpx.HTTPStatusError)
                    else None,
                    "latency_seconds": time.monotonic() - started,
                },
            )
            raise EvaluationError("recall_unavailable") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise EvaluationError("recall_response_invalid") from exc
        latency = time.monotonic() - started
        # Capture successful-HTTP diagnostics before schema/scope admission.
        # Keep original tag/type values to diagnose rejection without re-recall.
        raw_results = body.get("results") if isinstance(body, dict) else None
        projected = []
        if isinstance(raw_results, list):
            for result in raw_results:
                if not isinstance(result, dict):
                    projected.append(result)
                    continue
                item = {
                    key: value
                    for key, value in result.items()
                    if key in RecalledMemory.model_fields
                    or key in {"scores", "chunk_id"}
                }
                if isinstance(item.get("metadata"), dict):
                    item["metadata"] = {
                        key: value
                        for key, value in item["metadata"].items()
                        if key in ATTRIBUTION_METADATA_KEYS
                    }
                projected.append(item)
        trace = body.get("trace") if isinstance(body, dict) else None
        capture.write(
            "hindsight.recall.json",
            {
                "http_status": response.status_code,
                "request_path": path,
                "request": payload,
                "latency_seconds": latency,
                "result_projection": projected
                if isinstance(raw_results, list)
                else None,
                "results_shape": type(raw_results).__name__,
            },
        )
        if isinstance(trace, dict):
            capture.write("hindsight.recall-trace.json", trace)
        try:
            if not isinstance(body, dict) or not isinstance(body.get("results"), list):
                raise EvaluationError("recall_response_invalid")
            memories = [RecalledMemory.model_validate(item) for item in body["results"]]
        except (ValueError, ValidationError) as exc:
            raise EvaluationError("recall_response_invalid") from exc
        for memory in memories:
            memory.check_scope(inputs.scope)
        if not isinstance(trace, dict):
            raise EvaluationError("recall_trace_missing")
        result_ids = [item.get("id") for item in raw_results if isinstance(item, dict)] if isinstance(raw_results, list) else []
        qualify_reranking(trace, result_ids)
        return memories, {
            "status": "ok_nonempty" if memories else "ok_empty",
            "request_path": path,
            "request": payload,
            "latency_seconds": latency,
            "result_count": len(memories),
        }
