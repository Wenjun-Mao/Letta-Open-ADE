from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx


class PublicApiError(RuntimeError):
    """A safe error receipt for public ADE API failures.

    Provider response bodies and private reasoning must never enter parity evidence.
    """

    def __init__(self, *, engine: str, status_code: int, code: str) -> None:
        super().__init__(f"{engine} API {status_code} {code}")
        self.engine = engine
        self.status_code = status_code
        self.code = code


class PublicApiProtocolError(RuntimeError):
    pass


@dataclass(frozen=True)
class NormalizedEvent:
    sequence: int
    event_type: str
    attempt: int | None


class LegacyV2Client:
    """A retry-free client for the public Letta-backed Agent Studio API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def options(self) -> dict[str, Any]:
        return await self._request_json(
            "GET",
            "/api/v2/model-catalog/options",
            params={"scenario": "chat", "refresh": "true"},
        )

    async def template(self, kind: str, key: str) -> dict[str, Any]:
        if kind not in {"prompt", "persona"}:
            raise ValueError(f"Unsupported template kind: {kind}")
        collection = "prompts" if kind == "prompt" else "personas"
        return await self._request_json(
            "GET",
            f"/api/v2/prompt-center/{collection}/{key}",
            params={"scenario": "chat"},
        )

    async def create_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request_json("POST", "/api/v2/agent-studio/agents", payload)

    async def send_message(
        self,
        *,
        agent_id: str,
        message: str,
        timeout_seconds: float,
        retry_count: int,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/api/v2/agent-studio/agents/{agent_id}/messages",
            {
                "message": message,
                "timeout_seconds": timeout_seconds,
                "retry_count": retry_count,
            },
            timeout_seconds=max(timeout_seconds + 60, 90),
        )

    async def persistent_state(self, agent_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET",
            f"/api/v2/agent-studio/agents/{agent_id}/persistent-state",
            params={"limit": "500"},
        )

    async def archive_agent(self, agent_id: str) -> dict[str, Any]:
        return await self._request_json(
            "POST", f"/api/v2/agent-studio/agents/{agent_id}/archive", {}
        )

    async def purge_agent(self, agent_id: str) -> dict[str, Any]:
        return await self._request_json(
            "DELETE", f"/api/v2/agent-studio/agents/{agent_id}/purge"
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        params: dict[str, str] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                f"{self.base_url}{path}",
                headers=self._headers,
                json=payload,
                params=params,
                timeout=timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise PublicApiError(
                engine="legacy", status_code=0, code="transport_error"
            ) from exc
        return _response_json(response, engine="legacy")


class NativeV3Client:
    """A retry-free client for the isolated ADE-native v3 public API."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, read=None)
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def worker_health(self) -> dict[str, Any]:
        return await self._request_json("GET", "/api/v3/worker-health")

    async def create_agent_studio_session(
        self,
        *,
        idempotency_key: str,
        definition_key: str,
        name: str,
        subject_external_key: str,
        subject_display_name: str,
        title: str,
        model_key: str,
        reviewer_model_key: str,
        embedding_model_key: str,
        prompt_key: str,
        persona_key: str,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/api/v3/agent-studio/sessions",
            {
                "idempotency_key": idempotency_key,
                "title": title,
                "new_definition": {
                    "definition_key": definition_key,
                    "name": name,
                    "model_key": model_key,
                    "reviewer_model_key": reviewer_model_key,
                    "embedding_model_key": embedding_model_key,
                    "prompt_key": prompt_key,
                    "persona_key": persona_key,
                    "tool_names": ["search_memory"],
                },
                "new_subject": {
                    "external_key": subject_external_key,
                    "display_name": subject_display_name,
                },
            },
        )

    async def archive_agent_studio_session(
        self, conversation_id: str
    ) -> dict[str, Any]:
        return await self._request_json(
            "DELETE", f"/api/v3/agent-studio/sessions/{conversation_id}"
        )

    async def restore_agent_studio_session(
        self, conversation_id: str
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            f"/api/v3/agent-studio/sessions/{conversation_id}/restore",
            {},
        )

    async def accept_turn(
        self,
        *,
        conversation_id: str,
        content: str,
        idempotency_key: str,
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

    async def conversation_state(self, conversation_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", f"/api/v3/agent-studio/sessions/{conversation_id}/state"
        )

    async def subject_memories(self, subject_id: str) -> dict[str, Any]:
        return await self._request_json(
            "GET", f"/api/v3/agent-studio/subjects/{subject_id}/memories"
        )

    async def await_terminal(
        self,
        accepted: dict[str, Any],
        *,
        timeout_seconds: float,
    ) -> tuple[dict[str, Any], tuple[NormalizedEvent, ...]]:
        run_id = _required_string(accepted, "run_id")
        events_url = _required_string(accepted, "events_url")
        events: list[NormalizedEvent] = []
        try:
            async with asyncio.timeout(timeout_seconds):
                async for event in self._stream_events(events_url):
                    events.append(event)
        except TimeoutError as exc:
            raise PublicApiError(
                engine="native", status_code=0, code="terminal_timeout"
            ) from exc
        return await self.get_run(run_id), tuple(events)

    async def _stream_events(self, events_url: str) -> AsyncIterator[NormalizedEvent]:
        url = self._same_origin_url(events_url)
        try:
            async with self._client.stream(
                "GET", url, headers=self._headers
            ) as response:
                if not response.is_success:
                    await response.aread()
                    _raise_public_api_error(response, engine="native")
                parser = _SseParser()
                async for line in response.aiter_lines():
                    event = parser.feed(line)
                    if event is not None:
                        yield event
                event = parser.finish()
                if event is not None:
                    yield event
        except httpx.HTTPError as exc:
            raise PublicApiError(
                engine="native", status_code=0, code="transport_error"
            ) from exc

    async def _request_json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                self._same_origin_url(path),
                headers=self._headers,
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise PublicApiError(
                engine="native", status_code=0, code="transport_error"
            ) from exc
        return _response_json(response, engine="native")

    def _same_origin_url(self, value: str) -> str:
        candidate = urlsplit(value)
        base = urlsplit(self.base_url)
        if candidate.scheme or candidate.netloc:
            if (candidate.scheme, candidate.netloc) != (base.scheme, base.netloc):
                raise PublicApiProtocolError(
                    "native v3 event URL escaped the configured origin"
                )
            return value
        if not value.startswith("/"):
            raise PublicApiProtocolError("native v3 event URL must be an absolute path")
        return f"{self.base_url}{value}"


class _SseParser:
    def __init__(self) -> None:
        self._event_type = "message"
        self._data: list[str] = []

    def feed(self, line: str) -> NormalizedEvent | None:
        if not line:
            return self._emit()
        if line.startswith(":"):
            return None
        field, separator, value = line.partition(":")
        if not separator:
            return None
        if value.startswith(" "):
            value = value[1:]
        if field == "event":
            self._event_type = value or "message"
        elif field == "data":
            self._data.append(value)
        return None

    def finish(self) -> NormalizedEvent | None:
        return self._emit()

    def _emit(self) -> NormalizedEvent | None:
        if not self._data:
            self._event_type = "message"
            return None
        raw = "\n".join(self._data)
        self._data = []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PublicApiProtocolError("native v3 SSE event was not JSON") from exc
        if not isinstance(data, dict):
            raise PublicApiProtocolError("native v3 SSE event was not an object")
        event = NormalizedEvent(
            sequence=_integer(data.get("sequence")),
            event_type=str(data.get("type") or self._event_type),
            attempt=_optional_integer(data.get("attempt")),
        )
        self._event_type = "message"
        return event


def _response_json(response: httpx.Response, *, engine: str) -> dict[str, Any]:
    if not response.is_success:
        _raise_public_api_error(response, engine=engine)
    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise PublicApiProtocolError(f"{engine} API returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise PublicApiProtocolError(f"{engine} API returned a non-object JSON payload")
    return payload


def _raise_public_api_error(response: httpx.Response, *, engine: str) -> None:
    code = "api_error"
    try:
        payload = response.json()
    except json.JSONDecodeError:
        payload = {}
    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, dict):
        code = str(detail.get("code") or code)
    raise PublicApiError(engine=engine, status_code=response.status_code, code=code)


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise PublicApiProtocolError(f"native v3 response is missing {key}")
    return value


def _integer(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise PublicApiProtocolError("native v3 event sequence was invalid") from exc


def _optional_integer(value: object) -> int | None:
    return None if value is None else _integer(value)
