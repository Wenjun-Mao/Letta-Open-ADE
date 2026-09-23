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
    prospective_thread_params,
)


FAKE_SERVER = r"""
import json
import os
import sys

def send(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()

for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    if method == "initialize":
        send({"id": request["id"], "result": {"platformFamily": "unix"}})
    elif method == "initialized":
        pass
    elif method == "config/read":
        send({"id": request["id"], "result": {"config": {"model": "gpt-6-luna"}}})
    elif method == "thread/start":
        send({"id": request["id"], "result": {"thread": {"id": "fake-thread"}}})
    elif method == "turn/interrupt":
        send({"id": 77, "method": "item/tool/call", "params": {
            "threadId": "fake-thread", "turnId": "fake-turn", "callId": "fake-call",
            "tool": os.environ.get("FAKE_TOOL", "search_memory"),
            "namespace": None,
            "arguments": {"query": "synthetic tea"},
        }})
        answer = json.loads(sys.stdin.readline())
        send({"method": "turn/completed", "params": {"turn": {
            "id": "fake-turn", "status": "interrupted"}}})
        send({"id": request["id"], "result": {"tool_answer": answer}})
"""


async def _fake_process(tool: str = "search_memory") -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-u",
        "-c",
        FAKE_SERVER,
        env={**os.environ, "FAKE_TOOL": tool},
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
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
    assert "model_providers.openai.request_max_retries=0" not in command


def test_fake_server_initialize_config_and_bound_tool_dispatch() -> None:
    async def exercise() -> None:
        process = await _fake_process()
        observed: list[dict] = []
        try:
            probe = StdioProbe(
                process,
                tool_handler=lambda arguments: (
                    observed.append(arguments) or {"facts": ["synthetic tea"]}
                ),
            )
            assert (await probe.initialize())["platformFamily"] == "unix"
            assert (await probe.request("config/read", {"includeLayers": False}))[
                "config"
            ]["model"] == "gpt-6-luna"
            assert (
                await probe.request(
                    "thread/start", prospective_thread_params(Path("/tmp"))
                )
            )["thread"]["id"] == "fake-thread"
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
            process.terminate()
            await process.wait()

    asyncio.run(exercise())


def test_fake_server_rejects_tool_outside_ade_allowlist() -> None:
    async def exercise() -> None:
        process = await _fake_process(tool="exec_command")
        called = False

        def handler(arguments: dict) -> dict:
            nonlocal called
            called = True
            return {}

        try:
            probe = StdioProbe(process, tool_handler=handler)
            await probe.initialize()
            with pytest.raises(SpikeProtocolError, match="non-allowlisted"):
                await probe.request(
                    "turn/interrupt", {"threadId": "fake-thread", "turnId": "fake-turn"}
                )
            assert called is False
        finally:
            process.terminate()
            await process.wait()

    asyncio.run(exercise())
