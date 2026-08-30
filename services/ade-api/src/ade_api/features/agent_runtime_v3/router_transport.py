from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx


_TRANSIENT_ERRORS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.RemoteProtocolError,
)


class RouterRequestError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        error_code: str = "router_request_error",
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ):
        super().__init__(message)
        self.retryable = retryable
        self.error_code = _normalize_error_code(error_code)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class RouterTransport:
    base_url: str
    api_key: str = ""

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def catalog(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        return await self._request(
            "/router/model-catalog", None, timeout_seconds=timeout_seconds, method="GET"
        )

    async def chat_completion(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self._request(
            "/chat/completions", payload, timeout_seconds=timeout_seconds
        )

    async def embeddings(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self._request(
            "/embeddings", payload, timeout_seconds=timeout_seconds
        )

    async def _request(
        self,
        path: str,
        payload: dict[str, Any] | None,
        *,
        timeout_seconds: float,
        method: str = "POST",
    ) -> dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}{path}"
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                if method == "GET":
                    response = await client.get(url, headers=self._headers())
                else:
                    response = await client.post(
                        url, headers=self._headers(), json=payload
                    )
        except _TRANSIENT_ERRORS as exc:
            error_name = type(exc).__name__.removesuffix("Exception")
            raise RouterRequestError(
                "Model Router transport request failed",
                retryable=True,
                error_code=f"transport_{error_name.casefold()}",
            ) from exc
        retryable = response.status_code == 429 or response.status_code >= 500
        if response.status_code >= 400:
            retry_after: float | None = None
            try:
                retry_after = float(response.headers.get("Retry-After", ""))
            except ValueError:
                pass
            raise RouterRequestError(
                f"Model Router request failed with status {response.status_code}",
                retryable=retryable,
                error_code=f"http_{response.status_code}",
                status_code=response.status_code,
                retry_after_seconds=retry_after,
            )
        try:
            value = response.json()
        except ValueError as exc:
            raise RouterRequestError(
                "Model Router returned non-JSON content",
                retryable=False,
                error_code="invalid_json_response",
            ) from exc
        if not isinstance(value, dict):
            raise RouterRequestError(
                "Model Router returned a non-object response",
                retryable=False,
                error_code="invalid_response_shape",
            )
        return value


def _normalize_error_code(value: object) -> str:
    normalized = str(value or "").strip().casefold()
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", normalized):
        return "router_request_error"
    return normalized
