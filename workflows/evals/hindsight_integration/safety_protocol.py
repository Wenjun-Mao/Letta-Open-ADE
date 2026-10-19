"""Public product/fault controls for the finite Stage 1 safety observations."""

import asyncio
import json
from pathlib import Path
import time
from uuid import uuid4

from .live_bindings import wire_records
from .live_readbacks import validate_authored_binding
from .product_views import memory_path, page, saved_state
from .public_http import get_json, post_json
from .records import seal, write_new
from .wire_capture import require


class SafetyContext:
    def __init__(self, *, api, router, fault, root: Path, deadline, runtime):
        self.api, self.router, self.fault = api, router, fault
        self.root, self.deadline = root, deadline
        self.sessions, self.runs, self.rules = [], [], []
        self.runtime = runtime

    async def until(self, read, predicate, *, seconds=None, code):
        deadline = (
            min(self.deadline, time.monotonic() + seconds) if seconds else self.deadline
        )
        while time.monotonic() < deadline:
            value = await read()
            if predicate(value):
                return value
            await asyncio.sleep(0.5)
        raise TimeoutError(code)

    async def session(self, label):
        value = await post_json(
            self.api,
            "/api/v3/evaluation-sessions",
            {
                "idempotency_key": "stage1-safety-" + uuid4().hex,
                "title": "Stage1 safety " + label,
                "model_key": self.runtime.character_route,
                "compaction_model_key": self.runtime.character_route,
                "prompt_key": "chat_v20261019",
                "persona_key": "chat_linxiaotang",
                "tool_names": ["search_memory"],
            },
        )
        validate_authored_binding(value, self.runtime)
        state = await saved_state(self.api, value["conversation"]["id"])
        memories = await page(self.api, memory_path(value) + "/memories")
        deliveries = await page(self.api, memory_path(value) + "/deliveries")
        require(
            state["conversation"]["messages"] == []
            and state["conversation"]["summary"] is None
            and memories["total"] == deliveries["total"] == 0,
            "safety_relationship_not_fresh",
        )
        self.sessions.append(value)
        write_new(self.root / f"session-{len(self.sessions):02d}.json", value)
        return value

    async def accept(self, session, content, *, retries=0):
        receipt = await post_json(
            self.api,
            f"/api/v3/conversations/{session['conversation']['id']}/turns",
            {
                "content": content,
                "idempotency_key": "stage1-safety-turn-" + uuid4().hex,
                "timeout_seconds": 180,
                "retry_count": retries,
            },
        )
        self.runs.append(receipt["run_id"])
        return receipt

    async def terminal(self, run_id, *, expected, seconds=None):
        run = await self.until(
            lambda: get_json(self.api, f"/api/v3/runs/{run_id}"),
            lambda value: (
                value["status"] in {"succeeded", "failed", "cancelled", "paused"}
            ),
            seconds=seconds,
            code="safety_run_not_terminal",
        )
        require(run["status"] == expected, "unexpected_safety_run_status")
        return run

    async def rule(self, session, *, target, mode):
        value = await post_json(
            self.fault,
            "/control/rules",
            {
                "id": str(uuid4()),
                "conversation_id": session["conversation"]["id"],
                "target": target,
                "mode": mode,
                "hold_seconds": 240,
            },
        )
        self.rules.append(value["id"])
        return value["id"]

    async def matched(self, identity):
        return await self.until(
            lambda: get_json(self.fault, f"/control/rules/{identity}"),
            lambda row: row["matched"],
            seconds=90,
            code="safety_fault_not_matched",
        )

    async def release(self, identity):
        return await post_json(self.fault, f"/control/rules/{identity}/release", {})

    async def retained(self, session, *, seconds=None):
        route = memory_path(session)
        state = await saved_state(self.api, session["conversation"]["id"])
        expected = {row["id"] for row in state["conversation"]["messages"]}
        require(bool(expected), "safety_source_is_empty")

        async def read_deliveries():
            value = await page(self.api, route + "/deliveries")
            require(
                {row["message_id"] for row in value["items"]} == expected,
                "safety_delivery_source_set_mismatch",
            )
            require(
                not any(
                    row["status"] in {"failed", "uncertain"} for row in value["items"]
                ),
                "safety_delivery_failed_or_uncertain",
            )
            return value

        value = await self.until(
            read_deliveries,
            lambda row: (
                {item["message_id"] for item in row["items"]} == expected
                and all(item["status"] == "retained" for item in row["items"])
            ),
            seconds=seconds,
            code="safety_delivery_not_retained",
        )
        documents = [
            await get_json(self.api, route + "/sources/" + row["document_id"])
            for row in value["items"]
        ]
        require(
            {row["delivery"]["message_id"] for row in documents} == expected,
            "safety_original_document_set_mismatch",
        )
        messages = {row["id"]: row for row in state["conversation"]["messages"]}
        for document in documents:
            original = json.loads(document["native_original_text"])
            saved = messages[document["delivery"]["message_id"]]
            require(
                original["message_id"] == saved["id"]
                and original["content"] == document["content"] == saved["content"]
                and original["speaker"] == saved["role"]
                and original["sequence"] == saved["sequence"]
                and original["conversation_id"] == session["conversation"]["id"]
                and original["definition_version_id"]
                == session["agent_definition"]["id"]
                and original["status"]
                == ("accepted" if saved["role"] == "user" else "committed"),
                "safety_original_source_changed",
            )
        return {"deliveries": value, "sources": documents}

    async def messages(self, session, *, users, assistants):
        state = await saved_state(self.api, session["conversation"]["id"])
        messages = state["conversation"]["messages"]
        require(
            len([row for row in messages if row["role"] == "user"]) == users
            and len([row for row in messages if row["role"] == "assistant"])
            == assistants,
            "safety_saved_message_count_mismatch",
        )
        return state

    async def capture(self):
        runs = []
        for run_id in self.runs:
            runs.append(
                {
                    "run": await get_json(self.api, f"/api/v3/runs/{run_id}"),
                    "private_export": await get_json(
                        self.api, f"/api/v3/private-observations/runs/{run_id}"
                    ),
                    "wires": await wire_records(self.router, run_id=run_id),
                }
            )
        return seal("product-safety-readback", {"runs": runs})
