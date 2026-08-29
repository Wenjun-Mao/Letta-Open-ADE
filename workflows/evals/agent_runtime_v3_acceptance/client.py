from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx


class RuntimeClientError(RuntimeError):
    pass


class ApiResponseError(RuntimeClientError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(f"v3 API {status_code} {code}: {message}")
        self.status_code = status_code
        self.code = code
        self.message = message


class RunTimeout(RuntimeClientError):
    pass


@dataclass(frozen=True)
class SseEvent:
    event_id: str | None
    event_type: str
    data: dict[str, Any]


class RuntimeV3Client:
    """Authenticated client for the public v3 REST and normalized SSE contracts."""

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        # SSE read duration is owned by await_terminal's explicit workflow
        # deadline, not HTTPX's unrelated five-second default.
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, read=None)
        )
        self._owns_client = client is None
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def create_definition(
        self,
        *,
        definition_key: str,
        name: str,
        model_key: str,
        reviewer_model_key: str,
        embedding_model_key: str,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/api/v3/agent-definitions",
            {
                "definition_key": definition_key,
                "name": name,
                "model_key": model_key,
                "reviewer_model_key": reviewer_model_key,
                "embedding_model_key": embedding_model_key,
            },
        )

    async def create_subject(
        self, external_key: str, display_name: str
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/api/v3/memory-subjects",
            {"external_key": external_key, "display_name": display_name},
        )

    async def create_conversation(
        self, agent_definition_id: str, memory_subject_id: str
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/api/v3/conversations",
            {
                "agent_definition_id": agent_definition_id,
                "memory_subject_id": memory_subject_id,
            },
        )

    async def accept_turn(
        self,
        conversation_id: str,
        content: str,
        idempotency_key: str,
        *,
        timeout_seconds: float,
        retry_count: int,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/api/v3/conversations/{conversation_id}/turns",
            {
                "content": content,
                "idempotency_key": idempotency_key,
                "timeout_seconds": timeout_seconds,
                "retry_count": retry_count,
            },
        )

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return await self._request_json("GET", f"/api/v3/runs/{run_id}")

    async def cancel_run(self, run_id: str) -> dict[str, Any]:
        return await self._request_json("POST", f"/api/v3/runs/{run_id}/cancel", {})

    async def get_conversation_state(self, conversation_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", f"/api/v3/conversations/{conversation_id}/state"
        )

    async def get_subject_memories(self, subject_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", f"/api/v3/memory-subjects/{subject_id}/memories"
        )

    async def stream_events(
        self, events_url: str, *, last_event_id: str | None = None
    ) -> AsyncIterator[SseEvent]:
        headers = dict(self._headers)
        headers["Accept"] = "text/event-stream"
        if last_event_id:
            headers["Last-Event-ID"] = last_event_id
        async with self._client.stream(
            "GET", self._url(events_url), headers=headers
        ) as response:
            await _raise_for_response(response)
            parser = _SseParser()
            async for line in response.aiter_lines():
                event = parser.feed(line)
                if event is not None:
                    yield event
            event = parser.finish()
            if event is not None:
                yield event

    async def await_terminal(
        self, accepted: dict[str, Any], *, timeout_seconds: float
    ) -> tuple[dict[str, Any], tuple[SseEvent, ...]]:
        run_id = _required_string(accepted, "run_id")
        events_url = _required_string(accepted, "events_url")
        events: list[SseEvent] = []
        try:
            async with asyncio.timeout(timeout_seconds):
                async for event in self.stream_events(events_url):
                    events.append(event)
        except TimeoutError as exc:
            raise RunTimeout(
                f"run {run_id} did not finish before the client deadline"
            ) from exc
        return await self.get_run(run_id), tuple(events)

    async def _request_json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        response = await self._client.request(
            method,
            self._url(path),
            headers=self._headers,
            json=payload,
        )
        await _raise_for_response(response)
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise RuntimeClientError("v3 API returned malformed JSON") from exc
        if not isinstance(data, dict):
            raise RuntimeClientError("v3 API returned a non-object JSON response")
        return data

    def _url(self, value: str) -> str:
        candidate = urlsplit(value)
        base = urlsplit(self.api_base_url)
        if candidate.scheme or candidate.netloc:
            if (candidate.scheme, candidate.netloc) != (base.scheme, base.netloc):
                raise RuntimeClientError(
                    "v3 API URL must remain on the configured API origin"
                )
            return value
        if not value.startswith("/"):
            raise RuntimeClientError("v3 API URL must be absolute-path relative")
        return f"{self.api_base_url}{value}"


def parse_sse(lines: Iterable[str]) -> Iterable[SseEvent]:
    parser = _SseParser()
    for line in lines:
        event = parser.feed(line.rstrip("\n").rstrip("\r"))
        if event is not None:
            yield event
    event = parser.finish()
    if event is not None:
        yield event


class _SseParser:
    def __init__(self) -> None:
        self._event_id: str | None = None
        self._event_type = "message"
        self._data: list[str] = []

    def feed(self, line: str) -> SseEvent | None:
        if not line:
            return self._emit()
        if line.startswith(":"):
            return None
        field, separator, value = line.partition(":")
        if not separator:
            return None
        if value.startswith(" "):
            value = value[1:]
        if field == "id":
            self._event_id = value
        elif field == "event":
            self._event_type = value or "message"
        elif field == "data":
            self._data.append(value)
        return None

    def finish(self) -> SseEvent | None:
        return self._emit()

    def _emit(self) -> SseEvent | None:
        if not self._data:
            self._reset()
            return None
        raw = "\n".join(self._data)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeClientError("v3 SSE event contains malformed JSON") from exc
        if not isinstance(data, dict):
            raise RuntimeClientError("v3 SSE event payload must be an object")
        event = SseEvent(self._event_id, self._event_type, data)
        self._reset()
        return event

    def _reset(self) -> None:
        self._event_id = None
        self._event_type = "message"
        self._data = []


async def _raise_for_response(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        await response.aread()
        data = response.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = {}
    detail = data.get("detail") if isinstance(data, dict) else None
    if isinstance(detail, dict):
        code = str(detail.get("code") or "api_error")
        message = str(detail.get("message") or code)
    else:
        code = "api_error"
        message = str(detail or response.reason_phrase or "request failed")
    raise ApiResponseError(response.status_code, code, message)


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise RuntimeClientError(f"v3 API response is missing {key}")
    return value
