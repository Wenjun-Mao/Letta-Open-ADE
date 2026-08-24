from __future__ import annotations

import asyncio
from types import SimpleNamespace

from ade_api.features.agent_studio import messages_api
from ade_api.features.agent_studio.contracts import ChatRequest
import ade_api.integrations.letta.agent_service as agent_service_module
from ade_api.integrations.letta.agent_service import (
    DEFAULT_RUNTIME_RETRY_COUNT,
    DEFAULT_RUNTIME_TIMEOUT_SECONDS,
    LettaAgentService,
)


class _FakeMessagesApi:
    def create(
        self,
        *,
        agent_id: str,
        input: str | None = None,
        messages: list[dict[str, str]] | None = None,
        override_model: str | None = None,
        override_system: str | None = None,
        extra_body: dict[str, str] | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(messages=[])


class _FakeAgentsApi:
    def __init__(self) -> None:
        self.messages = _FakeMessagesApi()


class _FakeLettaClient:
    def __init__(
        self, *, timeout: float | None = None, max_retries: int | None = None
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.agents = _FakeAgentsApi()

    def with_options(self, *, timeout: float, max_retries: int) -> "_FakeLettaClient":
        return _FakeLettaClient(timeout=timeout, max_retries=max_retries)


def test_send_chat_message_uses_default_timeout_and_zero_retries(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_chat(*, client, agent_id: str, **kwargs):
        captured["client"] = client
        captured["agent_id"] = agent_id
        captured["kwargs"] = kwargs
        return {
            "total_steps": 0,
            "sequence": [],
            "memory_diff": {},
            "raw_messages": ["ignore-me"],
        }

    monkeypatch.setattr(agent_service_module, "chat", fake_chat)

    service = LettaAgentService(_FakeLettaClient())
    result = service.send_chat_message(agent_id="agent-1", message="hello world")

    configured_client = captured["client"]
    assert isinstance(configured_client, _FakeLettaClient)
    assert configured_client.timeout == DEFAULT_RUNTIME_TIMEOUT_SECONDS
    assert configured_client.max_retries == DEFAULT_RUNTIME_RETRY_COUNT
    assert captured["agent_id"] == "agent-1"
    assert captured["kwargs"] == {"input": "hello world"}
    assert "raw_messages" not in result


def test_send_runtime_message_forwards_explicit_timeout_and_retry(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_chat(*, client, agent_id: str, **kwargs):
        captured["client"] = client
        captured["agent_id"] = agent_id
        captured["kwargs"] = kwargs
        return {
            "total_steps": 1,
            "sequence": [{"type": "assistant", "content": "done"}],
            "memory_diff": {},
            "raw_messages": ["ignore-me"],
        }

    monkeypatch.setattr(agent_service_module, "chat", fake_chat)

    service = LettaAgentService(_FakeLettaClient())
    payload = service.send_runtime_message(
        agent_id="agent-1",
        message="check tools",
        override_model="lmstudio_openai/qwen3.5-27b",
        override_system="You are concise.",
        timeout_seconds=91,
        retry_count=2,
    )

    configured_client = captured["client"]
    assert isinstance(configured_client, _FakeLettaClient)
    assert configured_client.timeout == 91
    assert configured_client.max_retries == 2
    assert captured["kwargs"] == {
        "input": "check tools",
        "override_model": "lmstudio_openai/qwen3.5-27b",
        "override_system": "You are concise.",
    }
    assert payload["result"]["sequence"][0]["content"] == "done"


def test_api_chat_forwards_timeout_and_retry_to_service(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeAgentService:
        def send_chat_message(self, **kwargs):
            captured.update(kwargs)
            return {"total_steps": 0, "sequence": [], "memory_diff": {}}

    monkeypatch.setattr(messages_api, "ensure_ade_api_enabled", lambda: None)
    monkeypatch.setattr(messages_api, "is_datetime_query", lambda message: False)

    response = asyncio.run(
        messages_api.api_chat(
            "agent-1",
            ChatRequest(
                message="hello",
                timeout_seconds=120,
                retry_count=3,
            ),
            _FakeAgentService(),
            SimpleNamespace(get_record=lambda _agent_id: None),
        )
    )

    assert captured["agent_id"] == "agent-1"
    assert captured["message"] == "hello"
    assert captured["timeout_seconds"] == 120
    assert captured["retry_count"] == 3
    assert response["sequence"] == []
