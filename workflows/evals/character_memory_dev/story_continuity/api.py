"""In-process ADE HTTP harness only; no socket transport or live entrypoint."""

from __future__ import annotations

import httpx


class OfflineADE:
    def __init__(self, transport: httpx.MockTransport | httpx.ASGITransport):
        if type(transport) not in {httpx.MockTransport, httpx.ASGITransport}:
            raise ValueError(
                "Only explicitly injected in-process test transports allowed"
            )
        self.transport = transport

    async def request(self, method: str, path: str, body: dict | None = None) -> dict:
        if not path.startswith("/api/v3/") or ".." in path or "?" in path:
            raise ValueError("Expected fixed ADE API path")
        async with httpx.AsyncClient(
            transport=self.transport,
            base_url="http://offline.invalid",
            trust_env=False,
            follow_redirects=False,
        ) as client:
            response = await client.request(method, path, json=body)
        if not response.is_success:
            raise ValueError(f"Offline ADE {response.status_code}: {response.text}")
        return response.json()

    async def create(self, request: dict) -> dict:
        return await self.request("POST", "/api/v3/history-trial/sessions", request)

    async def create_version(self, root_id: str, request: dict) -> dict:
        return await self.request(
            "POST", f"/api/v3/history-trial/definitions/{root_id}/versions", request
        )

    async def archive(self, conversation_id: str) -> dict:
        return await self.request(
            "DELETE", f"/api/v3/history-trial/sessions/{conversation_id}"
        )

    async def accept(self, conversation_id: str, *, prompt: str, key: str) -> dict:
        return await self.request(
            "POST",
            f"/api/v3/conversations/{conversation_id}/turns",
            {
                "content": prompt,
                "idempotency_key": key,
                "retry_count": 0,
                "timeout_seconds": 180,
            },
        )

    async def readback(
        self, conversation_id: str, subject_id: str, run_id: str
    ) -> dict:
        run = await self.request("GET", f"/api/v3/runs/{run_id}")
        if run["status"] not in {"succeeded", "failed", "cancelled"}:
            raise ValueError("Terminal run required; no hidden polling/retries")
        state = await self.request(
            "GET", f"/api/v3/history-trial/sessions/{conversation_id}/state"
        )
        if state["messages_truncated"]:
            raise ValueError(
                "Incomplete message readback; stop rather than infer absence"
            )
        memories = await self.request(
            "GET", f"/api/v3/history-trial/subjects/{subject_id}/memories"
        )
        if (
            run["id"] != run_id
            or run["conversation_id"] != conversation_id
            or state["id"] != conversation_id
            or memories["subject_id"] != subject_id
            or state["memory_subject_id"] != subject_id
            or state["purpose"] != "evaluation"
        ):
            raise ValueError("Readback identity/scope mismatch")
        return {
            "run": run,
            "state": state,
            "memories": memories,
            "entity_coverage": "fact_associated_projection_only",
        }
