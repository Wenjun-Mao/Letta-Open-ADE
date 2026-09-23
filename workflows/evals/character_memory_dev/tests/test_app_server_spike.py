"""Synthetic stdio protocol tests; never start a Codex model turn."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from workflows.evals.character_memory_dev.app_server_spike import (
    SpikeProtocolError,
    StdioProbe,
    app_server_command,
    disabled_mcp_server_names,
    mcp_inventory_command,
    prospective_thread_params,
    stop_process_group,
    verify_app_server_mcp_config,
)


FAKE_SERVER = r"""
import json
import os
import sys
import time

def send(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    scenario = os.environ.get("FAKE_SCENARIO", "normal")
    if method == "initialize":
        send({"id": request["id"], "result": {"platformFamily": "unix"}})
    elif method == "initialized":
        pass
    elif method == "config/read":
        send({"id": request["id"], "result": {"config": {"model": "gpt-6-luna"}}})
    elif method == "thread/start":
        send({"id": request["id"], "result": {"thread": {"id": "fake-thread"}}})
    elif method == "turn/interrupt":
        if scenario == "notifications":
            while True:
                send({"method": "item/agentMessage/delta", "params": {"text": "x"}})
                time.sleep(0.005)
        params = {
            "threadId": "other-thread" if scenario == "wrong-thread" else "fake-thread",
            "turnId": "other-turn" if scenario == "wrong-turn" else "fake-turn",
            "callId": "fake-call",
            "tool": os.environ.get("FAKE_TOOL", "search_memory"),
            "namespace": None,
            "arguments": {"query": "synthetic tea"},
        }
        send({"id": 77, "method": "item/tool/call", "params": params})
        answer = json.loads(sys.stdin.readline())
        if scenario == "duplicate":
            send({"id": 78, "method": "item/tool/call", "params": params})
            answer = json.loads(sys.stdin.readline())
        send({"method": "turn/completed", "params": {"turn": {
            "id": "fake-turn", "status": "interrupted"}}})
        send({"id": request["id"], "result": {"tool_answer": answer}})
"""


async def _fake_process(
    tool: str = "search_memory", scenario: str = "normal"
) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        "-c",
        FAKE_SERVER,
        env={**os.environ, "FAKE_TOOL": tool, "FAKE_SCENARIO": scenario},
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )


def test_thread_shape_is_explicit_and_not_submitted(tmp_path: Path) -> None:
    params = prospective_thread_params(tmp_path)
    assert params["model"] == "gpt-6-luna"
    assert params["ephemeral"] is True
    assert params["allowProviderModelFallback"] is False
    assert params["sandbox"] == "read-only"
    assert params["baseInstructions"] and params["developerInstructions"]
    assert [tool["name"] for tool in params["dynamicTools"]] == ["search_memory"]
    command = app_server_command("/usr/bin/codex")
    assert "--stdio" in command
    assert 'web_search="disabled"' in command
    assert "features.shell_tool=false" in command
    assert "features.apps=false" in command
    assert "mcp_servers.cua_repl.enabled=false" in command
    assert "mcp_servers.node_repl.enabled=false" in command
    assert "mcp_servers.openaiDeveloperDocs.enabled=false" in command
    assert "mcp_servers.cua_repl.enabled=false" in mcp_inventory_command(
        "/usr/bin/codex"
    )
    assert "model_providers.openai.request_max_retries=0" not in command


@pytest.mark.parametrize(
    "inventory, error",
    [
        ([{"name": "node_repl", "enabled": True}], "exposes a server"),
        ([{"name": "node_repl", "enabled": "false"}], "unexpected shape"),
        ([{"name": "node_repl", "enabled": False}] * 2, "exposes a server"),
    ],
)
def test_mcp_inventory_fails_closed(inventory: list[dict], error: str) -> None:
    with pytest.raises(SpikeProtocolError, match=error):
        disabled_mcp_server_names(json.dumps(inventory).encode())


def test_mcp_inventory_accepts_only_disabled_servers() -> None:
    assert disabled_mcp_server_names(
        json.dumps([{"name": "node_repl", "enabled": False}]).encode()
    ) == ["node_repl"]


def test_app_server_mcp_config_fails_closed() -> None:
    verify_app_server_mcp_config(
        {"mcp_servers": {"node_repl": {"enabled": False}}}
    )
    for config in (
        {},
        {"mcp_servers": {"node_repl": {"enabled": True}}},
        {"mcp_servers": {"node_repl": {}}},
    ):
        with pytest.raises(SpikeProtocolError, match="does not disable"):
            verify_app_server_mcp_config(config)


def test_fake_server_initialize_config_and_bound_tool_dispatch() -> None:
    async def exercise() -> None:
        process = await _fake_process()
        observed: list[dict] = []

        async def handler(arguments: dict) -> dict:
            observed.append(arguments)
            return {"facts": ["synthetic tea"]}

        try:
            probe = StdioProbe(process, tool_handler=handler)
            assert (await probe.initialize())["platformFamily"] == "unix"
            assert (await probe.request("config/read", {"includeLayers": False}))[
                "config"
            ]["model"] == "gpt-6-luna"
            assert (
                await probe.request(
                    "thread/start", prospective_thread_params(Path("/tmp"))
                )
            )["thread"]["id"] == "fake-thread"
            probe.bind_tool_scope(thread_id="fake-thread", turn_id="fake-turn")
            interrupted = await probe.request(
                "turn/interrupt", {"threadId": "fake-thread", "turnId": "fake-turn"}
            )
            assert observed == [{"query": "synthetic tea"}]
            response = interrupted["tool_answer"]
            assert response["id"] == 77
            assert response["result"]["success"] is True
            assert json.loads(response["result"]["contentItems"][0]["text"]) == {
                "facts": ["synthetic tea"]
            }
            assert probe.notifications[-1]["method"] == "turn/completed"
        finally:
            await stop_process_group(process)

    asyncio.run(exercise())


def test_fake_server_rejects_tool_outside_ade_allowlist() -> None:
    async def exercise() -> None:
        process = await _fake_process(tool="exec_command")
        called = False

        async def handler(arguments: dict) -> dict:
            nonlocal called
            called = True
            return {}

        try:
            probe = StdioProbe(process, tool_handler=handler)
            await probe.initialize()
            probe.bind_tool_scope(thread_id="fake-thread", turn_id="fake-turn")
            with pytest.raises(SpikeProtocolError, match="non-allowlisted"):
                await probe.request(
                    "turn/interrupt", {"threadId": "fake-thread", "turnId": "fake-turn"}
                )
            assert called is False
        finally:
            await stop_process_group(process)

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "scenario", ["unbound", "wrong-thread", "wrong-turn", "duplicate"]
)
def test_fake_server_rejects_unbound_or_duplicate_call_id(scenario: str) -> None:
    async def exercise() -> None:
        process = await _fake_process(scenario=scenario)
        calls = 0

        async def handler(arguments: dict) -> dict:
            nonlocal calls
            calls += 1
            return {"facts": []}

        try:
            probe = StdioProbe(process, tool_handler=handler)
            await probe.initialize()
            if scenario != "unbound":
                probe.bind_tool_scope(thread_id="fake-thread", turn_id="fake-turn")
            with pytest.raises(SpikeProtocolError, match="non-allowlisted"):
                await probe.request(
                    "turn/interrupt", {"threadId": "fake-thread", "turnId": "fake-turn"}
                )
            assert calls == (1 if scenario == "duplicate" else 0)
        finally:
            await stop_process_group(process)

    asyncio.run(exercise())


@pytest.mark.parametrize("limit", ["deadline", "notifications", "bytes"])
def test_fake_server_notification_stream_is_bounded(limit: str) -> None:
    async def exercise() -> None:
        process = await _fake_process(scenario="notifications")
        try:
            probe = StdioProbe(
                process,
                request_timeout_seconds=0.06 if limit == "deadline" else 2,
                max_notifications=2 if limit == "notifications" else 1000,
                max_total_bytes=220 if limit == "bytes" else 2_000_000,
            )
            await probe.initialize()
            expected = {
                "deadline": "timeout",
                "notifications": "notification limit",
                "bytes": "total response bytes",
            }[limit]
            with pytest.raises(SpikeProtocolError, match=expected):
                await probe.request(
                    "turn/interrupt", {"threadId": "fake-thread", "turnId": "fake-turn"}
                )
        finally:
            await stop_process_group(process)

    asyncio.run(exercise())


def test_fake_process_group_is_reaped_after_interruption() -> None:
    async def exercise() -> None:
        child_code = (
            "import signal,time;"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN);"
            "print('child-ready', flush=True);"
            "time.sleep(30)"
        )
        parent_code = (
            "import subprocess,sys,time;"
            f"subprocess.Popen([sys.executable, '-u', '-c', {child_code!r}]);"
            "time.sleep(30)"
        )
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            "-c",
            parent_code,
            stdout=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        assert process.stdout is not None
        assert (
            await asyncio.wait_for(process.stdout.readline(), timeout=2)
            == b"child-ready\n"
        )
        await stop_process_group(process)
        assert process.returncode is not None
        assert await asyncio.wait_for(process.stdout.read(), timeout=2) == b""

    asyncio.run(exercise())
