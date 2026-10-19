"""Concrete HTTP integration with the source-pinned Hindsight 0.10.3 API."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote, urlsplit
from uuid import UUID

import httpx


OPERATION_STATUSES = {
    "pending",
    "processing",
    "completed",
    "failed",
    "cancelled",
    "not_found",
}


class HindsightError(RuntimeError):
    def __init__(self, code: str, *, status_code: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def _identity(value: object, *, expected: str, code: str) -> None:
    if value != expected:
        raise HindsightError(code)


class HindsightClient:
    """Each method makes one attempt; durable retries belong to ADE's owner."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 30,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        parsed = urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not api_key.strip()
            or timeout_seconds <= 0
        ):
            raise ValueError(
                "A Hindsight service URL, credential and timeout are required"
            )
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._owns_client = client is None
        self.client = client if client is not None else httpx.AsyncClient()

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    @staticmethod
    def bank_path(bank_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", bank_id):
            raise ValueError("Invalid Hindsight bank identity")
        return f"/v1/default/banks/{bank_id}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict | None = None,
        raw_body: bytes | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        if body is not None and raw_body is not None:
            raise ValueError("Specify one request representation")
        kwargs: dict[str, Any] = {"params": params}
        if raw_body is not None:
            kwargs["content"] = raw_body
        elif body is not None:
            kwargs["json"] = body
        try:
            response = await self.client.request(
                method,
                self.base_url + path,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise HindsightError("hindsight_unavailable") from exc
        if response.is_error:
            raise HindsightError(
                "hindsight_http_error", status_code=response.status_code
            )
        try:
            result = response.json()
        except ValueError as exc:
            raise HindsightError("hindsight_response_invalid") from exc
        if not isinstance(result, dict):
            raise HindsightError("hindsight_response_invalid")
        return result

    async def create_bank(self, bank_id: str, *, name: str) -> dict:
        body = await self._request("PUT", self.bank_path(bank_id), body={"name": name})
        _identity(body.get("bank_id"), expected=bank_id, code="hindsight_bank_mismatch")
        return body

    async def bank_config(self, bank_id: str) -> dict:
        body = await self._request("GET", self.bank_path(bank_id) + "/config")
        _identity(body.get("bank_id"), expected=bank_id, code="hindsight_bank_mismatch")
        if not isinstance(body.get("config"), dict):
            raise HindsightError("hindsight_config_invalid")
        return body

    async def configure_bank(self, bank_id: str, updates: dict) -> dict:
        body = await self._request(
            "PATCH", self.bank_path(bank_id) + "/config", body={"updates": updates}
        )
        _identity(body.get("bank_id"), expected=bank_id, code="hindsight_bank_mismatch")
        if not isinstance(body.get("config"), dict):
            raise HindsightError("hindsight_config_invalid")
        return body

    async def submit(self, bank_id: str, *, operation_id: str, payload: bytes) -> dict:
        UUID(operation_id)
        try:
            request = json.loads(payload)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Invalid immutable retain payload") from exc
        if (
            not isinstance(request, dict)
            or request.get("operation_id") != operation_id
            or request.get("async") is not True
            or not isinstance(request.get("items"), list)
            or len(request["items"]) != 1
        ):
            raise ValueError("Retain payload must bind one source and async operation")
        body = await self._request(
            "POST", self.bank_path(bank_id) + "/memories", raw_body=payload
        )
        _identity(body.get("bank_id"), expected=bank_id, code="hindsight_bank_mismatch")
        _identity(
            body.get("operation_id"),
            expected=operation_id,
            code="hindsight_operation_mismatch",
        )
        if body.get("success") is not True or body.get("async") is not True:
            raise HindsightError("hindsight_submission_invalid")
        return body

    async def operation(self, bank_id: str, operation_id: str) -> dict:
        UUID(operation_id)
        body = await self._request(
            "GET",
            self.bank_path(bank_id) + f"/operations/{operation_id}",
            params={"include_payload": "true"},
        )
        _identity(
            body.get("operation_id"),
            expected=operation_id,
            code="hindsight_operation_mismatch",
        )
        if "bank_id" in body:
            _identity(body["bank_id"], expected=bank_id, code="hindsight_bank_mismatch")
        if body.get("status") not in OPERATION_STATUSES:
            raise HindsightError("hindsight_operation_invalid")
        return body

    async def retry_operation(self, bank_id: str, operation_id: str) -> dict:
        UUID(operation_id)
        body = await self._request(
            "POST", self.bank_path(bank_id) + f"/operations/{operation_id}/retry"
        )
        _identity(
            body.get("operation_id"),
            expected=operation_id,
            code="hindsight_operation_mismatch",
        )
        if body.get("success") is not True:
            raise HindsightError("hindsight_retry_invalid")
        return body

    async def operations(
        self,
        bank_id: str,
        *,
        kind: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> dict:
        params: dict = {"offset": offset, "limit": limit}
        if kind is not None:
            params["type"] = kind
        body = await self._request(
            "GET", self.bank_path(bank_id) + "/operations", params=params
        )
        if (
            not isinstance(body.get("operations"), list)
            or type(body.get("total")) is not int
        ):
            raise HindsightError("hindsight_operations_invalid")
        return body

    async def cancel_operation(self, bank_id: str, operation_id: str) -> dict:
        UUID(operation_id)
        body = await self._request(
            "DELETE", self.bank_path(bank_id) + f"/operations/{operation_id}"
        )
        _identity(
            body.get("operation_id"),
            expected=operation_id,
            code="hindsight_operation_mismatch",
        )
        if body.get("success") is not True:
            raise HindsightError("hindsight_cancel_invalid")
        return body

    async def recall(self, bank_id: str, payload: dict) -> dict:
        body = await self._request(
            "POST", self.bank_path(bank_id) + "/memories/recall", body=payload
        )
        if not isinstance(body.get("results"), list) or any(
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("text"), str)
            for item in body["results"]
        ):
            raise HindsightError("hindsight_recall_invalid")
        return body

    async def memories(
        self, bank_id: str, *, offset: int = 0, limit: int = 100
    ) -> dict:
        body = await self._request(
            "GET",
            self.bank_path(bank_id) + "/memories/list",
            params={"offset": offset, "limit": limit},
        )
        if (
            not isinstance(body.get("items"), list)
            or type(body.get("total")) is not int
        ):
            raise HindsightError("hindsight_memories_invalid")
        return body

    async def document(self, bank_id: str, document_id: str) -> dict:
        return await self._request(
            "GET", self.bank_path(bank_id) + "/documents/" + quote(document_id, safe="")
        )

    async def statistics(self, bank_id: str) -> dict:
        return await self._request("GET", self.bank_path(bank_id) + "/stats")
