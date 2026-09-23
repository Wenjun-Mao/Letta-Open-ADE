"""No-generation app-server protocol spike for the local Luna feasibility study.

Only ``python -m ...app_server_spike`` is an operator entrypoint. It initializes
the installed CLI and reads a filtered config; it never starts a thread or turn.
The thread/tool helpers are exercised against a fake stdio server in tests.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .luna import preflight, subscription_environment


MAX_LINE_BYTES = 262_144
CLI_VERSION = "codex-cli 0.155.0-alpha.9.2"
PROTOCOL_VERSION = "codex-cli-0.155.0-alpha.9.2-app-server-v2"


class SpikeProtocolError(RuntimeError):
    pass


def app_server_command(binary: str) -> list[str]:
    # These are candidate restrictions, not proof that only dynamic tools exist.
    settings = (
        'approval_policy="never"',
        'sandbox_mode="read-only"',
        'forced_login_method="chatgpt"',
        'model="gpt-6-luna"',
        'model_reasoning_effort="medium"',
        'service_tier="default"',
        'web_search="disabled"',
        "features.shell_tool=false",
        "features.unified_exec=false",
        "features.apps=false",
        "features.hooks=false",
        "features.multi_agent=false",
        "features.browser_use=false",
        "features.computer_use=false",
    )
    return [
        binary,
        "app-server",
        "--stdio",
        "--strict-config",
        *(part for setting in settings for part in ("-c", setting)),
    ]


def synthetic_search_memory_spec() -> dict[str, Any]:
    """Version-pinned experimental field shape; no ADE handler is attached."""
    return {
        "type": "function",
        "name": "search_memory",
        "description": "Search synthetic facts for the bound test subject.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }


def prospective_thread_params(cwd: Path) -> dict[str, Any]:
    """Build, but do not submit, a prospective isolated test thread."""
    return {
        "model": "gpt-6-luna",
        "cwd": str(cwd),
        "ephemeral": True,
        "approvalPolicy": "never",
        "sandbox": "read-only",
        "allowProviderModelFallback": False,
        "baseInstructions": "You are a synthetic local protocol-test agent.",
        "developerInstructions": "Use only the supplied synthetic memory tool.",
        "dynamicTools": [synthetic_search_memory_spec()],
    }


class StdioProbe:
    """Small JSONL exchange; no turn-start method in the operator entrypoint."""

    def __init__(
        self,
        process: asyncio.subprocess.Process,
        *,
        tool_handler: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.process = process
        self.tool_handler = tool_handler
        self.next_id = 1
        self.notifications: list[dict[str, Any]] = []

    async def send(self, message: dict[str, Any]) -> None:
        if self.process.stdin is None:
            raise SpikeProtocolError("app-server stdin is unavailable")
        encoded = json.dumps(message, separators=(",", ":")).encode() + b"\n"
        if len(encoded) > MAX_LINE_BYTES:
            raise SpikeProtocolError("outbound protocol line is too large")
        self.process.stdin.write(encoded)
        await self.process.stdin.drain()

    async def read(self) -> dict[str, Any]:
        if self.process.stdout is None:
            raise SpikeProtocolError("app-server stdout is unavailable")
        try:
            line = await asyncio.wait_for(self.process.stdout.readline(), timeout=10)
        except (asyncio.TimeoutError, ValueError) as exc:
            raise SpikeProtocolError(
                "app-server response timeout or oversized line"
            ) from exc
        if not line or len(line) > MAX_LINE_BYTES:
            raise SpikeProtocolError("app-server closed or oversized response")
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SpikeProtocolError("app-server emitted malformed JSON") from exc
        if not isinstance(message, dict):
            raise SpikeProtocolError("app-server message must be an object")
        return message

    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        await self.send({"method": method, "id": request_id, "params": params})
        while True:
            message = await self.read()
            if message.get("id") == request_id and "method" not in message:
                if "error" in message:
                    raise SpikeProtocolError(f"app-server rejected {method}")
                result = message.get("result")
                if not isinstance(result, dict):
                    raise SpikeProtocolError("app-server result must be an object")
                return result
            if "id" in message and "method" in message:
                await self._answer_tool_request(message)
            elif "method" in message and "id" not in message:
                self.notifications.append(message)
            else:
                raise SpikeProtocolError("unexpected app-server response identity")

    async def _answer_tool_request(self, message: dict[str, Any]) -> None:
        params = message.get("params")
        if (
            message.get("method") != "item/tool/call"
            or not isinstance(params, dict)
            or params.get("tool") != "search_memory"
            or params.get("namespace") is not None
            or not isinstance(params.get("arguments"), dict)
            or set(params["arguments"]) != {"query"}
            or not isinstance(params["arguments"].get("query"), str)
            or not params["arguments"]["query"].strip()
            or any(
                not isinstance(params.get(key), str) or not params[key]
                for key in ("callId", "threadId", "turnId")
            )
            or self.tool_handler is None
        ):
            raise SpikeProtocolError("non-allowlisted server tool request")
        result = self.tool_handler(params["arguments"])
        if not isinstance(result, dict):
            raise SpikeProtocolError("tool handler must return an object")
        await self.send(
            {
                "id": message["id"],
                "result": {
                    "contentItems": [
                        {
                            "type": "inputText",
                            "text": json.dumps(result, separators=(",", ":")),
                        }
                    ],
                    "success": True,
                },
            }
        )

    async def initialize(self) -> dict[str, Any]:
        result = await self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "ade_luna_local_spike",
                    "title": "ADE local Luna protocol spike",
                    "version": PROTOCOL_VERSION,
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        await self.send({"method": "initialized", "params": {}})
        return result


async def inspect_installed_config() -> dict[str, Any]:
    """Read only a safe allowlist; never print a raw effective config or secrets."""
    env = subscription_environment()
    if preflight(env) != CLI_VERSION:
        raise SpikeProtocolError("installed Codex version changed; requalify schema")
    binary = shutil.which("codex")
    if binary is None:
        raise SpikeProtocolError("installed codex binary was not found")
    with tempfile.TemporaryDirectory(prefix="ade-luna-appserver-") as directory:
        process = await asyncio.create_subprocess_exec(
            *app_server_command(binary),
            cwd=directory,
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
            limit=MAX_LINE_BYTES,
        )
        try:
            probe = StdioProbe(process)
            initialized = await probe.initialize()
            result = await probe.request("config/read", {"includeLayers": False})
            config = result.get("config")
            if not isinstance(config, dict):
                raise SpikeProtocolError("config/read omitted effective config")
            safe_keys = (
                "model",
                "model_provider",
                "model_reasoning_effort",
                "service_tier",
                "approval_policy",
                "sandbox_mode",
                "web_search",
                "forced_login_method",
            )
            return {
                "protocol": PROTOCOL_VERSION,
                "platform_family": initialized.get("platformFamily"),
                "config": {key: config.get(key) for key in safe_keys},
            }
        finally:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except asyncio.TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(inspect_installed_config()), indent=2))
