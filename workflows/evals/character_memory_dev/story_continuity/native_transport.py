"""One-attempt loopback HTTP client, separate from the offline-only harness."""

from __future__ import annotations

import asyncio
import time
from urllib.parse import urlsplit

import httpx


class NativeADE:
    def __init__(self, base_url: str, token: str, *, transport=None):
        address = urlsplit(base_url)
        if (
            address.scheme != "http"
            or address.hostname != "127.0.0.1"
            or not address.port
            or address.username
            or address.password
            or address.path
            or address.query
            or address.fragment
            or not token
        ):
            raise ValueError("Native probe requires its authenticated loopback service")
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def request(self, method: str, path: str, body: dict | None = None) -> dict:
        if not path.startswith("/api/v3/") or any(x in path for x in ("..", "?", "#")):
            raise ValueError("Expected fixed ADE API path")
        response = await self.client.request(method, path, json=body)
        if not response.is_success:
            # Preserve status, never include possibly sensitive server error bodies.
            raise ValueError(f"Native ADE {method} {path}: HTTP {response.status_code}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Expected ADE object response")
        return payload

    async def wait_terminal(self, run_id: str, *, seconds: float = 240) -> dict:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            run = await self.request("GET", f"/api/v3/runs/{run_id}")
            if run.get("id") != run_id:
                raise ValueError("Run identity mismatch")
            if run["status"] in {"succeeded", "failed", "cancelled"}:
                return run
            if run["status"] not in {"pending", "running"}:
                raise ValueError("Unknown run state")
            await asyncio.sleep(0.5)
        raise TimeoutError("Terminal readback deadline; never resubmit this turn")

    async def readback(self, conversation_id: str, subject_id: str, run: dict) -> dict:
        state = await self.request(
            "GET", f"/api/v3/history-trial/sessions/{conversation_id}/state"
        )
        memories = await self.request(
            "GET", f"/api/v3/history-trial/subjects/{subject_id}/memories"
        )
        if (
            run["status"] not in {"succeeded", "failed", "cancelled"}
            or run["conversation_id"] != conversation_id
            or state["id"] != conversation_id
            or state["memory_subject_id"] != subject_id
            or memories["subject_id"] != subject_id
            or state["purpose"] != "evaluation"
            or state["messages_truncated"]
        ):
            raise ValueError("Incomplete, nonterminal or cross-scope readback")
        return {"run": run, "state": state, "memories": memories}
