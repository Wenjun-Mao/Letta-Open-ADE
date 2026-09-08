from __future__ import annotations

import time
from typing import Any

import httpx


TERMINAL_RUN_STATUSES = frozenset({"succeeded", "failed", "cancelled"})


class ApiRequestError(RuntimeError):
    pass


class AdeApiClient:
    """Small synchronous client for the evaluation-session lifecycle."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        api_key: str = "",
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._api_key = api_key.strip()

    def __enter__(self) -> AdeApiClient:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        self._client = httpx.Client(
            base_url=self._base_url, timeout=self._timeout_seconds, headers=headers
        )
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._client.close()

    def options(self) -> dict[str, Any]:
        return self._request_json(
            "GET",
            "/api/v2/model-catalog/options",
            params={"scenario": "chat", "refresh": "true"},
        )

    def template(self, kind: str, key: str) -> dict[str, Any]:
        if kind not in {"prompt", "persona"}:
            raise ValueError(f"Unsupported template kind: {kind}")
        collection = "prompts" if kind == "prompt" else "personas"
        return self._request_json(
            "GET",
            f"/api/v2/prompt-center/{collection}/{key}",
            params={"scenario": "chat"},
        )

    def create_evaluation_session(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/api/v3/evaluation-sessions", json=payload)

    def run_turn(
        self,
        *,
        conversation_id: str,
        message: str,
        idempotency_key: str,
        timeout_seconds: float,
        retry_count: int,
    ) -> dict[str, Any]:
        accepted = self._request_json(
            "POST",
            f"/api/v3/conversations/{conversation_id}/turns",
            json={
                "content": message,
                "idempotency_key": idempotency_key,
                "timeout_seconds": timeout_seconds,
                "retry_count": retry_count,
            },
        )
        run_id = _required_text(accepted, "run_id")
        run = self._wait_for_run(
            run_id,
            deadline_seconds=timeout_seconds * (retry_count + 1) + 30,
        )
        if run.get("status") != "succeeded":
            raise ApiRequestError(
                f"Agent runtime run {run_id} ended with status={run.get('status')} "
                f"code={run.get('error_code') or 'unknown'}"
            )
        return {
            "accepted": accepted,
            "run": run,
            "events": self._request_json(
                "GET", f"/api/v3/runs/{run_id}/event-log", params={"limit": "500"}
            ).get("items", []),
            "state": self.evaluation_state(conversation_id),
        }

    def evaluation_state(self, conversation_id: str) -> dict[str, Any]:
        return self._request_json(
            "GET",
            f"/api/v3/evaluation-sessions/{conversation_id}/state",
            params={"message_limit": "200"},
        )

    def purge_evaluation_session(self, conversation_id: str) -> dict[str, Any]:
        return self._request_json(
            "DELETE", f"/api/v3/evaluation-sessions/{conversation_id}"
        )

    def _wait_for_run(self, run_id: str, *, deadline_seconds: float) -> dict[str, Any]:
        deadline = time.monotonic() + deadline_seconds
        while time.monotonic() < deadline:
            run = self._request_json("GET", f"/api/v3/runs/{run_id}")
            if run.get("status") in TERMINAL_RUN_STATUSES:
                return run
            time.sleep(0.2)
        raise ApiRequestError(f"Agent runtime run {run_id} exceeded client deadline")

    def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._client.request(method, path, **kwargs)
        if response.status_code >= 400:
            raise ApiRequestError(
                f"{method} {path} failed with {response.status_code}: {response.text}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise ApiRequestError(f"{method} {path} returned a non-object JSON payload")
        return payload


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ApiRequestError(f"ADE API response is missing {key}")
    return value
