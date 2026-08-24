from __future__ import annotations

import asyncio
from types import SimpleNamespace

from ade_api.features.tool_center import runtime_api
from ade_api.features.tool_center.contracts import ToolTestInvokeRequest


def test_tool_probe_route_uses_agent_runtime_controls(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeAgentService:
        def send_runtime_message(self, **kwargs):
            captured.update(kwargs)
            return {
                "agent_id": kwargs["agent_id"],
                "result": {
                    "sequence": [
                        {"type": "tool_call", "name": "search_documents"},
                        {"type": "tool_return", "content": "ok"},
                    ]
                },
            }

    monkeypatch.setattr(runtime_api, "ensure_ade_api_enabled", lambda: None)

    response = asyncio.run(
        runtime_api.api_invoke_tool_probe(
            ToolTestInvokeRequest(
                agent_id="agent-1",
                input="search for the latest policy doc",
                expected_tool_name="search_documents",
                timeout_seconds=75,
                retry_count=4,
            ),
            _FakeAgentService(),
            SimpleNamespace(get_record=lambda _agent_id: None),
        )
    )

    assert captured["agent_id"] == "agent-1"
    assert captured["message"] == "search for the latest policy doc"
    assert captured["timeout_seconds"] == 75
    assert captured["retry_count"] == 4
    assert response["tool_call_count"] == 1
    assert response["tool_return_count"] == 1
    assert response["expected_tool_matched"] is True
