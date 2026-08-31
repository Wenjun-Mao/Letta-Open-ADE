from __future__ import annotations

from typing import Any

import httpx


class ApiRequestError(RuntimeError):
    pass


class AdeApiClient:
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

    def create_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/api/v2/agent-studio/agents", json=payload)

    def chat(
        self, *, agent_id: str, message: str, timeout_seconds: float, retry_count: int
    ) -> dict[str, Any]:
        return self._request_json(
            "POST",
            f"/api/v2/agent-studio/agents/{agent_id}/messages",
            json={
                "message": message,
                "timeout_seconds": timeout_seconds,
                "retry_count": retry_count,
            },
        )

    def persistent_state(self, agent_id: str) -> dict[str, Any]:
        return self._request_json(
            "GET",
            f"/api/v2/agent-studio/agents/{agent_id}/persistent-state",
            params={"limit": "500"},
        )

    def archive_agent(self, agent_id: str) -> dict[str, Any]:
        return self._request_json(
            "POST", f"/api/v2/agent-studio/agents/{agent_id}/archive"
        )

    def purge_agent(self, agent_id: str) -> dict[str, Any]:
        return self._request_json(
            "DELETE", f"/api/v2/agent-studio/agents/{agent_id}/purge"
        )

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
