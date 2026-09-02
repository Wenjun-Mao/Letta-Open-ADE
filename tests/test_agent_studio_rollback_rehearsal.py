from __future__ import annotations

import subprocess
from datetime import UTC, datetime

import httpx
import pytest

from scripts.agent_studio_rollback_state import snapshot_native_state
from scripts.agent_studio_rollback_web import _published_port
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
        lambda **_kwargs: (True, True),
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

    assert receipt["rehearsed"] is True
    assert receipt["legacy_health_passed"] is True
    assert receipt["legacy_web_image_built"] is True
    assert receipt["legacy_web_smoke_passed"] is True
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
        lambda **_kwargs: (True, True),
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
