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
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .luna import preflight, subscription_environment


MAX_LINE_BYTES = 262_144
MAX_TOTAL_BYTES = 2_000_000
MAX_NOTIFICATIONS = 128
REQUEST_TIMEOUT_SECONDS = 10.0
CLI_VERSION = "codex-cli 0.155.0-alpha.9.2"
PROTOCOL_VERSION = "codex-cli-0.155.0-alpha.9.2-app-server-v2"
DISABLED_TOOL_FEATURES = (
    "shell_tool",
    "unified_exec",
    "apps",
    "plugins",
    "hooks",
    "multi_agent",
    "browser_use",
    "computer_use",
)
APP_SERVER_SETTINGS = (
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
    "features.plugins=false",
    "features.hooks=false",
    "features.multi_agent=false",
    "features.browser_use=false",
    "features.computer_use=false",
    # Host-injected stdio servers have no transport in the invocation config
    # layer. A disabled override still needs a valid transport to parse.
    'mcp_servers.cua_repl.command="/usr/bin/false"',
    "mcp_servers.cua_repl.enabled=false",
    'mcp_servers.node_repl.command="/usr/bin/false"',
    "mcp_servers.node_repl.enabled=false",
    "mcp_servers.openaiDeveloperDocs.enabled=false",
)


class SpikeProtocolError(RuntimeError):
    pass


def app_server_command(binary: str) -> list[str]:
    # These are candidate restrictions, not proof that only dynamic tools exist.
    return [
        binary,
        "app-server",
        "--stdio",
        "--strict-config",
        *(part for setting in APP_SERVER_SETTINGS for part in ("-c", setting)),
    ]


def mcp_inventory_command(binary: str) -> list[str]:
    return [
        binary,
        *(part for setting in APP_SERVER_SETTINGS for part in ("-c", setting)),
        "mcp",
        "list",
        "--json",
    ]


def disabled_mcp_server_names(stdout: bytes) -> list[str]:
    if len(stdout) > MAX_LINE_BYTES:
        raise SpikeProtocolError("MCP inventory exceeded size limit")
    try:
        inventory = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise SpikeProtocolError("MCP inventory was malformed") from exc
    if not isinstance(inventory, list) or any(
        not isinstance(server, dict)
        or not isinstance(server.get("name"), str)
        or not isinstance(server.get("enabled"), bool)
        for server in inventory
    ):
        raise SpikeProtocolError("MCP inventory had an unexpected shape")
    names = [server["name"] for server in inventory]
    if len(names) != len(set(names)) or any(
        server["enabled"] for server in inventory
    ):
        raise SpikeProtocolError("MCP inventory still exposes a server")
    return names


def verify_app_server_mcp_config(config: dict[str, Any]) -> None:
    servers = config.get("mcp_servers")
    if not isinstance(servers, dict) or any(
        not isinstance(server, dict) or server.get("enabled") is not False
        for server in servers.values()
    ):
        raise SpikeProtocolError("app-server config does not disable every MCP server")


def verify_app_server_tool_features(config: dict[str, Any]) -> None:
    features = config.get("features")
    if not isinstance(features, dict) or any(
        features.get(name) is not False for name in DISABLED_TOOL_FEATURES
    ):
        raise SpikeProtocolError("app-server tool feature config is not disabled")


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
        tool_handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
        | None = None,
        request_timeout_seconds: float = REQUEST_TIMEOUT_SECONDS,
        max_total_bytes: int = MAX_TOTAL_BYTES,
        max_notifications: int = MAX_NOTIFICATIONS,
    ) -> None:
        if (
            request_timeout_seconds <= 0
            or max_total_bytes <= 0
            or max_notifications <= 0
        ):
            raise ValueError("protocol limits must be positive")
        self.process = process
        self.tool_handler = tool_handler
        self.request_timeout_seconds = request_timeout_seconds
        self.max_total_bytes = max_total_bytes
        self.max_notifications = max_notifications
        self.next_id = 1
        self.notifications: list[dict[str, Any]] = []
        self._total_bytes = 0
        self._tool_scope: tuple[str, str] | None = None
        self._seen_call_ids: set[str] = set()

    def bind_tool_scope(self, *, thread_id: str, turn_id: str) -> None:
        """One synthetic turn may dispatch tools; no implicit scope inference."""
        if not thread_id or not turn_id or self._tool_scope is not None:
            raise SpikeProtocolError("tool scope must be bound exactly once")
        self._tool_scope = (thread_id, turn_id)

    async def send(self, message: dict[str, Any], *, deadline: float) -> None:
        if self.process.stdin is None:
            raise SpikeProtocolError("app-server stdin is unavailable")
        encoded = json.dumps(message, separators=(",", ":")).encode() + b"\n"
        if len(encoded) > MAX_LINE_BYTES:
            raise SpikeProtocolError("outbound protocol line is too large")
        self.process.stdin.write(encoded)
        try:
            await asyncio.wait_for(
                self.process.stdin.drain(), timeout=_remaining(deadline)
            )
        except asyncio.TimeoutError as exc:
            raise SpikeProtocolError("app-server operation timed out") from exc

    async def read(self, *, deadline: float) -> dict[str, Any]:
        if self.process.stdout is None:
            raise SpikeProtocolError("app-server stdout is unavailable")
        try:
            line = await asyncio.wait_for(
                self.process.stdout.readline(), timeout=_remaining(deadline)
            )
        except (asyncio.TimeoutError, ValueError) as exc:
            raise SpikeProtocolError(
                "app-server response timeout or oversized line"
            ) from exc
        if not line or len(line) > MAX_LINE_BYTES:
            raise SpikeProtocolError("app-server closed or oversized response")
        self._total_bytes += len(line)
        if self._total_bytes > self.max_total_bytes:
            raise SpikeProtocolError("app-server total response bytes exceeded limit")
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SpikeProtocolError("app-server emitted malformed JSON") from exc
        if not isinstance(message, dict):
            raise SpikeProtocolError("app-server message must be an object")
        return message

    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        deadline = time.monotonic() + self.request_timeout_seconds
        request_id = self.next_id
        self.next_id += 1
        await self.send(
            {"method": method, "id": request_id, "params": params},
            deadline=deadline,
        )
        while True:
            message = await self.read(deadline=deadline)
            if message.get("id") == request_id and "method" not in message:
                if "error" in message:
                    raise SpikeProtocolError(f"app-server rejected {method}")
                result = message.get("result")
                if not isinstance(result, dict):
                    raise SpikeProtocolError("app-server result must be an object")
                return result
            if "id" in message and "method" in message:
                await self._answer_tool_request(message, deadline=deadline)
            elif "method" in message and "id" not in message:
                if len(self.notifications) >= self.max_notifications:
                    raise SpikeProtocolError("app-server notification limit exceeded")
                self.notifications.append(message)
            else:
                raise SpikeProtocolError("unexpected app-server response identity")

    async def _answer_tool_request(
        self, message: dict[str, Any], *, deadline: float
    ) -> None:
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
            or self._tool_scope != (params["threadId"], params["turnId"])
            or params["callId"] in self._seen_call_ids
            or self.tool_handler is None
        ):
            raise SpikeProtocolError("non-allowlisted server tool request")
        self._seen_call_ids.add(params["callId"])
        try:
            result = await asyncio.wait_for(
                self.tool_handler(params["arguments"]), timeout=_remaining(deadline)
            )
        except asyncio.TimeoutError as exc:
            raise SpikeProtocolError("app-server tool handler timed out") from exc
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
            },
            deadline=deadline,
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
        await self.send(
            {"method": "initialized", "params": {}},
            deadline=time.monotonic() + self.request_timeout_seconds,
        )
        return result


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise SpikeProtocolError("app-server operation timed out")
    return remaining


async def stop_process_group(process: asyncio.subprocess.Process) -> None:
    """Terminate the dedicated app-server process group, escalating if needed."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(process.wait(), timeout=2)
    except asyncio.TimeoutError:
        pass
    # The parent may have exited while a child ignored TERM and kept pipes open.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    await process.wait()


async def inspect_mcp_inventory(binary: str, env: dict[str, str], cwd: str) -> list[str]:
    """Fail closed if this exact invocation still exposes an MCP server."""
    process = await asyncio.create_subprocess_exec(
        *mcp_inventory_command(binary),
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + REQUEST_TIMEOUT_SECONDS
        try:
            if process.stdout is None:
                raise SpikeProtocolError("MCP inventory stdout is unavailable")
            stdout = await asyncio.wait_for(
                process.stdout.read(MAX_LINE_BYTES + 1),
                timeout=_remaining(deadline),
            )
        except asyncio.TimeoutError as exc:
            raise SpikeProtocolError("MCP inventory timed out") from exc
        if len(stdout) > MAX_LINE_BYTES:
            raise SpikeProtocolError("MCP inventory exceeded size limit")
        try:
            await asyncio.wait_for(process.wait(), timeout=_remaining(deadline))
        except asyncio.TimeoutError as exc:
            raise SpikeProtocolError("MCP inventory timed out") from exc
        if process.returncode != 0:
            raise SpikeProtocolError("MCP inventory command failed")
        return disabled_mcp_server_names(stdout)
    finally:
        if process.returncode is None:
            await stop_process_group(process)


async def inspect_installed_config() -> dict[str, Any]:
    """Read only a safe allowlist; never print a raw effective config or secrets."""
    env = subscription_environment()
    if preflight(env) != CLI_VERSION:
        raise SpikeProtocolError("installed Codex version changed; requalify schema")
    binary = shutil.which("codex")
    if binary is None:
        raise SpikeProtocolError("installed codex binary was not found")
    with tempfile.TemporaryDirectory(prefix="ade-luna-appserver-") as directory:
        disabled_mcp_servers = await inspect_mcp_inventory(binary, env, directory)
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
            verify_app_server_mcp_config(config)
            verify_app_server_tool_features(config)
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
                "disabled_mcp_servers": disabled_mcp_servers,
                "disabled_tool_features": list(DISABLED_TOOL_FEATURES),
            }
        finally:
            await stop_process_group(process)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(inspect_installed_config()), indent=2))
