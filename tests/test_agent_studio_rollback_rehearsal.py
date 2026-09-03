from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime

import httpx
import pytest

from scripts.agent_studio_rollback_state import snapshot_native_state
from scripts.agent_studio_rollback_web import (
    LegacyWebApiVerification,
    LegacyWebVerification,
    _published_port,
    exercise_legacy_agent_studio_proxy,
)
from scripts.rehearse_agent_studio_rollback import rehearse_rollback


def test_rollback_rehearsal_proves_v2_health_and_preserves_v3_state(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "scripts.rehearse_agent_studio_rollback._git",
        lambda _root, *args: "a" * 40 if args[0] == "rev-parse" else "",
    )
    monkeypatch.setattr(
        "scripts.rehearse_agent_studio_rollback._git_show",
        lambda *_args: 'return requestJson("/api/v2/agent-studio/agents")',
    )
    monkeypatch.setattr(
        "scripts.rehearse_agent_studio_rollback.source_fingerprint",
        lambda _root: "b" * 64,
    )
    monkeypatch.setattr(
        "scripts.rehearse_agent_studio_rollback._verify_legacy_web",
        lambda **_kwargs: LegacyWebVerification(
            image_built=True,
            page_loaded=True,
            api_read_passed=True,
            api_write_passed=True,
            api_cleanup_passed=True,
        ),
    )
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/api/v2/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/api/v3/worker-health":
            return httpx.Response(200, json={"worker_ready": True})
        if request.url.path == "/api/v3/agent-studio/definitions":
            return httpx.Response(200, json={"total": 1, "items": [{"id": "d1"}]})
        if request.url.path == "/api/v3/agent-studio/subjects":
            return httpx.Response(200, json={"total": 1, "items": [{"id": "s1"}]})
        if request.url.path == "/api/v3/agent-studio/sessions":
            return httpx.Response(
                200,
                json={
                    "total": 1,
                    "items": [{"conversation": {"id": "c1"}}],
                },
            )
        if request.url.path == "/api/v3/agent-studio/subjects/s1/memories":
            return httpx.Response(200, json={"subject_id": "s1", "facts": []})
        if request.url.path == "/api/v3/agent-studio/sessions/c1/state":
            return httpx.Response(
                200,
                json={
                    "id": "c1",
                    "messages": [],
                    "message_total": 0,
                    "messages_truncated": False,
                    "next_before_sequence": None,
                    "summary": None,
                },
            )
        raise AssertionError(request.url.path)

    receipt = rehearse_rollback(
        project_root=tmp_path,
        legacy_revision="0" * 40,
        legacy_base_url="https://legacy.test",
        native_base_url="https://native.test",
        legacy_api_key="legacy",
        native_api_key="native",
        compose_network="test_default",
        output_path=tmp_path / "rollback.json",
        command_runner=lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _seconds: None,
        now=lambda: datetime(2026, 9, 3, tzinfo=UTC),
    )

    assert receipt["error_code"] is None, receipt
    assert receipt["rehearsed"] is True
    assert receipt["legacy_health_passed"] is True
    assert receipt["legacy_web_image_built"] is True
    assert receipt["legacy_web_smoke_passed"] is True
    assert receipt["legacy_web_api_read_passed"] is True
    assert receipt["legacy_web_api_write_passed"] is True
    assert receipt["legacy_web_api_cleanup_passed"] is True
    assert receipt["native_state_preserved"] is True
    assert calls.count("/api/v3/agent-studio/sessions") == 2
    assert calls.count("/api/v3/agent-studio/sessions/c1/state") == 2
    assert calls.count("/api/v3/agent-studio/subjects/s1/memories") == 2


def test_rollback_rehearsal_fails_closed_when_v3_state_changes(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "scripts.rehearse_agent_studio_rollback._git",
        lambda _root, *args: "a" * 40 if args[0] == "rev-parse" else "",
    )
    monkeypatch.setattr(
        "scripts.rehearse_agent_studio_rollback._git_show",
        lambda *_args: "/api/v2/agent-studio/agents",
    )
    monkeypatch.setattr(
        "scripts.rehearse_agent_studio_rollback.source_fingerprint",
        lambda _root: "b" * 64,
    )
    monkeypatch.setattr(
        "scripts.rehearse_agent_studio_rollback._verify_legacy_web",
        lambda **_kwargs: LegacyWebVerification(
            image_built=True,
            page_loaded=True,
            api_read_passed=True,
            api_write_passed=True,
            api_cleanup_passed=True,
        ),
    )
    session_snapshots = iter(
        (
            {"total": 1, "items": [{"conversation": {"id": "c1"}}]},
            {"total": 1, "items": [{"conversation": {"id": "changed"}}]},
        )
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v3/agent-studio/sessions":
            return httpx.Response(200, json=next(session_snapshots))
        if request.url.path == "/api/v3/agent-studio/definitions":
            return httpx.Response(200, json={"total": 0, "items": []})
        if request.url.path == "/api/v3/agent-studio/subjects":
            return httpx.Response(200, json={"total": 0, "items": []})
        if request.url.path.startswith("/api/v3/agent-studio/sessions/"):
            conversation_id = request.url.path.split("/")[-2]
            return httpx.Response(
                200,
                json={
                    "id": conversation_id,
                    "messages": [],
                    "message_total": 0,
                    "messages_truncated": False,
                    "next_before_sequence": None,
                    "summary": None,
                },
            )
        if request.url.path == "/api/v3/worker-health":
            return httpx.Response(200, json={"worker_ready": True})
        return httpx.Response(200, json={"status": "ok"})

    receipt = rehearse_rollback(
        project_root=tmp_path,
        legacy_revision="0" * 40,
        legacy_base_url="https://legacy.test",
        native_base_url="https://native.test",
        legacy_api_key="legacy",
        native_api_key="native",
        compose_network="test_default",
        output_path=tmp_path / "rollback.json",
        command_runner=lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        ),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _seconds: None,
    )

    assert receipt["rehearsed"] is False
    assert receipt["native_state_preserved"] is False


def test_native_snapshot_follows_message_pagination() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v3/agent-studio/definitions":
            return httpx.Response(200, json={"total": 0, "items": []})
        if path == "/api/v3/agent-studio/subjects":
            return httpx.Response(200, json={"total": 0, "items": []})
        if path == "/api/v3/agent-studio/sessions":
            return httpx.Response(
                200,
                json={"total": 1, "items": [{"conversation": {"id": "c1"}}]},
            )
        if path == "/api/v3/agent-studio/sessions/c1/state":
            before = request.url.params.get("before_sequence")
            messages = (
                [{"id": "m2", "sequence": 2}]
                if before is None
                else [{"id": "m1", "sequence": 1}]
            )
            return httpx.Response(
                200,
                json={
                    "id": "c1",
                    "messages": messages,
                    "message_total": 2,
                    "messages_truncated": before is None,
                    "next_before_sequence": 2 if before is None else None,
                    "summary": None,
                },
            )
        raise AssertionError(path)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        snapshot = snapshot_native_state(client, "https://native.test", "key")

    assert [
        message["sequence"]
        for message in snapshot["conversation_states"]["c1"]["messages"]
    ] == [1, 2]


def test_legacy_web_port_parser_rejects_unusable_output() -> None:
    assert _published_port("127.0.0.1:49152\n") == 49152
    with pytest.raises(RuntimeError, match="legacy_web_port_invalid"):
        _published_port("")


def test_legacy_web_proxy_exercises_disposable_v2_agent_lifecycle() -> None:
    calls: list[tuple[str, str, str]] = []
    agent_id = "legacy-agent-1"

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.host, request.url.path))
        assert request.url.host == "legacy-web.test"
        if (
            request.method == "GET"
            and request.url.path == "/api/v2/model-catalog/options"
        ):
            return httpx.Response(
                200,
                json={
                    "models": [{"key": "openai-proxy/test-model"}],
                    "embeddings": [{"key": "letta/test-embedding"}],
                    "prompts": [{"key": "chat_prompt"}],
                    "personas": [{"key": "chat_persona"}],
                    "defaults": {
                        "prompt_key": "chat_prompt",
                        "persona_key": "chat_persona",
                        "embedding": "letta/test-embedding",
                    },
                },
            )
        if (
            request.method == "POST"
            and request.url.path == "/api/v2/agent-studio/agents"
        ):
            payload = json.loads(request.content)
            assert payload["scenario"] == "chat"
            assert payload["model"] == "openai-proxy/test-model"
            assert payload["prompt_key"] == "chat_prompt"
            assert payload["persona_key"] == "chat_persona"
            assert payload["embedding"] == "letta/test-embedding"
            return httpx.Response(200, json={"id": agent_id})
        if (
            request.method == "GET"
            and request.url.path
            == f"/api/v2/agent-studio/agents/{agent_id}/persistent-state"
        ):
            memory_value = (
                "before"
                if len([call for call in calls if call[0] == "PATCH"]) == 0
                else "rollback marker"
            )
            return httpx.Response(
                200,
                json={"memory_blocks": [{"label": "human", "value": memory_value}]},
            )
        if (
            request.method == "PATCH"
            and request.url.path
            == f"/api/v2/agent-studio/agents/{agent_id}/memory/human"
        ):
            assert json.loads(request.content) == {"value": "rollback marker"}
            return httpx.Response(
                200,
                json={"value_before": "before", "value_after": "rollback marker"},
            )
        if (
            request.method == "POST"
            and request.url.path == f"/api/v2/agent-studio/agents/{agent_id}/archive"
        ):
            return httpx.Response(200, json={"id": agent_id, "archived": True})
        if (
            request.method == "DELETE"
            and request.url.path == f"/api/v2/agent-studio/agents/{agent_id}/purge"
        ):
            return httpx.Response(
                200, json={"ok": True, "id": agent_id, "kind": "agent"}
            )
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = exercise_legacy_agent_studio_proxy(
            client=client,
            legacy_web_base_url="http://legacy-web.test",
            agent_name="ade-rollback-agent",
            memory_marker="rollback marker",
        )

    assert result == LegacyWebApiVerification(
        api_read_passed=True,
        api_write_passed=True,
        api_cleanup_passed=True,
    )
    assert calls == [
        ("GET", "legacy-web.test", "/api/v2/model-catalog/options"),
        ("POST", "legacy-web.test", "/api/v2/agent-studio/agents"),
        (
            "GET",
            "legacy-web.test",
            f"/api/v2/agent-studio/agents/{agent_id}/persistent-state",
        ),
        (
            "PATCH",
            "legacy-web.test",
            f"/api/v2/agent-studio/agents/{agent_id}/memory/human",
        ),
        (
            "GET",
            "legacy-web.test",
            f"/api/v2/agent-studio/agents/{agent_id}/persistent-state",
        ),
        (
            "POST",
            "legacy-web.test",
            f"/api/v2/agent-studio/agents/{agent_id}/archive",
        ),
        ("DELETE", "legacy-web.test", f"/api/v2/agent-studio/agents/{agent_id}/purge"),
    ]


def test_legacy_web_smoke_fails_when_proxy_cleanup_fails() -> None:
    agent_id = "legacy-agent-1"

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v2/model-catalog/options":
            return httpx.Response(
                200,
                json={
                    "models": [{"key": "openai-proxy/test-model"}],
                    "prompts": [{"key": "chat_prompt"}],
                    "personas": [{"key": "chat_persona"}],
                    "defaults": {
                        "prompt_key": "chat_prompt",
                        "persona_key": "chat_persona",
                    },
                },
            )
        if request.method == "POST" and request.url.path.endswith("/archive"):
            return httpx.Response(200, json={"id": agent_id, "archived": True})
        if request.method == "POST":
            return httpx.Response(200, json={"id": agent_id})
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "memory_blocks": [{"label": "human", "value": "rollback marker"}]
                },
            )
        if request.method == "PATCH":
            return httpx.Response(200, json={"value_after": "rollback marker"})
        if request.method == "DELETE":
            return httpx.Response(500, json={"detail": "ignored"})
        raise AssertionError(request.url.path)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = exercise_legacy_agent_studio_proxy(
            client=client,
            legacy_web_base_url="http://legacy-web.test",
            agent_name="ade-rollback-agent",
            memory_marker="rollback marker",
        )

    assert result.api_read_passed is True
    assert result.api_write_passed is True
    assert result.api_cleanup_passed is False
    assert (
        LegacyWebVerification(
            image_built=True,
            page_loaded=True,
            api_read_passed=result.api_read_passed,
            api_write_passed=result.api_write_passed,
            api_cleanup_passed=result.api_cleanup_passed,
        ).smoke_passed
        is False
    )
