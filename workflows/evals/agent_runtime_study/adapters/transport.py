from __future__ import annotations

from typing import Any, Protocol

import httpx

from .base import ModelProtocolError, NonRetryableModelError, RetryableModelError


class ChatCompletionsTransport(Protocol):
    async def complete(
        self,
        *,
        model_key: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> dict[str, Any]: ...


class HttpxChatCompletionsTransport:
    """One-shot OpenAI-compatible transport with no internal retry layer."""

    def __init__(self, *, base_url: str, api_key: str) -> None:
        base = str(base_url or "").strip().rstrip("/")
        if base.endswith("/chat/completions"):
            self.url = base
        elif base.endswith("/v1"):
            self.url = f"{base}/chat/completions"
        else:
            self.url = f"{base}/v1/chat/completions"
        self.api_key = api_key

    async def complete(
        self,
        *,
        model_key: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: dict[str, Any] = {
            "model": model_key,
            "messages": messages,
            "stream": False,
            "max_tokens": max_output_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(self.url, headers=headers, json=payload)
        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.RemoteProtocolError,
        ) as exc:
            raise RetryableModelError(str(exc)) from exc
        if response.status_code == 429 or response.status_code >= 500:
            raise RetryableModelError(
                f"Model Router temporary failure ({response.status_code}): "
                f"{response.text[:500]}"
            )
        if response.status_code >= 400:
            raise NonRetryableModelError(
                f"Model Router request failed ({response.status_code}): "
                f"{response.text[:500]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ModelProtocolError("Model Router returned non-JSON content") from exc
        if not isinstance(payload, dict):
            raise ModelProtocolError("Model Router returned a non-object payload")
        return payload
