"""Read saved product and native inspection evidence, without issuing extra recall."""

import asyncio
from datetime import datetime
from dataclasses import dataclass
import time

from .models import Scope, SourceMessage
from .public_http import get_json
from .wire_capture import require


def state_path(conversation_id):
    return f"/api/v3/evaluation-sessions/{conversation_id}/state"


def memory_path(session):
    return f"/api/v3/memory/subjects/{session['memory_subject']['id']}/characters/{session['agent_definition']['agent_definition_id']}"


async def page(api, path):
    value = await get_json(api, path, params={"limit": 200, "offset": 0})
    require(value["total"] == len(value["items"]), "stage1_inspection_page_incomplete")
    return value


async def saved_state(api, conversation_id):
    value = await get_json(
        api, state_path(conversation_id), params={"message_limit": 200}
    )
    require(
        not value["conversation"]["messages_truncated"], "saved_source_page_incomplete"
    )
    return value


async def fresh_readbacks(api, source, probe):
    route = memory_path(source)
    result = {
        "source_initial_state": await saved_state(api, source["conversation"]["id"]),
        "probe_initial_state": await saved_state(api, probe["conversation"]["id"]),
        "source_initial_memories": await page(api, route + "/memories"),
        "probe_initial_memories": await page(api, memory_path(probe) + "/memories"),
        "source_initial_deliveries": await page(api, route + "/deliveries"),
    }
    for key in ("source_initial_state", "probe_initial_state"):
        state = result[key]["conversation"]
        require(
            state["messages"] == [] and state.get("summary") is None,
            "fresh_conversation_contains_history",
        )
    for key in (
        "source_initial_memories",
        "probe_initial_memories",
        "source_initial_deliveries",
    ):
        require(
            result[key]["total"] == 0,
            "fresh_relationship_contains_memory_or_deliveries",
        )
    return result


@dataclass
class ProcessingReadback:
    deliveries: dict | None = None
    operations: dict | None = None

    @property
    def retention(self):
        if self.deliveries is None:
            return "not_observed"
        states = [row["status"] for row in self.deliveries["items"]]
        return (
            "failed"
            if any(value in {"failed", "uncertain"} for value in states)
            else "complete"
            if states and all(value == "retained" for value in states)
            else "pending"
        )

    @property
    def consolidation(self):
        if self.operations is None:
            return "not_observed"
        rows = [
            row
            for row in self.operations["items"]
            if row["operation_type"] in {"consolidation", "consolidate"}
        ]
        return (
            "failed"
            if any(row["status"] in {"failed", "cancelled"} for row in rows)
            else "complete"
            if rows and all(row["status"] == "completed" for row in rows)
            else "pending"
        )


async def wait_processed(
    api,
    session,
    *,
    expected_message_ids: set[str],
    deadline: float,
    progress: ProcessingReadback,
):
    route = memory_path(session)
    while time.monotonic() < deadline:
        deliveries = await page(api, route + "/deliveries")
        operations = await page(api, route + "/operations")
        progress.deliveries, progress.operations = deliveries, operations
        require(
            {row["message_id"] for row in deliveries["items"]} == expected_message_ids,
            "unexpected_source_delivery_set",
        )
        if any(row["status"] in {"failed", "uncertain"} for row in deliveries["items"]):
            raise RuntimeError("source_delivery_failed_or_uncertain")
        if any(row["status"] in {"failed", "cancelled"} for row in operations["items"]):
            raise RuntimeError("native_processing_failed")
        consolidated = any(
            row["operation_type"] in {"consolidation", "consolidate"}
            for row in operations["items"]
        )
        if (
            deliveries["items"]
            and all(row["status"] == "retained" for row in deliveries["items"])
            and consolidated
            and all(row["status"] == "completed" for row in operations["items"])
        ):
            return deliveries, operations
        await asyncio.sleep(3)
    raise TimeoutError("source_processing_incomplete_at_slot_deadline")


def original_sources(state, case, scope: dict, *, require_complete=True):
    messages = state["conversation"]["messages"]
    seeds = iter(case.history)
    actual_scope = Scope(
        workspace=scope["workspace_id"],
        subject=scope["subject_id"],
        character_root=scope["character_root_id"],
    )
    records = []
    for message in messages:
        fixture = next(seeds) if message["role"] == "user" else None
        if fixture:
            require(fixture.content == message["content"], "saved_seed_changed")
        records.append(
            SourceMessage(
                message_id=message["id"],
                fixture_id=fixture.fixture_id if fixture else None,
                conversation_id=state["conversation"]["id"],
                scope=actual_scope,
                role=message["role"],
                content=message["content"],
                occurred_at=datetime.fromisoformat(
                    message["created_at"].replace("Z", "+00:00")
                ),
                status="accepted" if message["role"] == "user" else "committed",
            )
        )
    if require_complete:
        require(
            len(records) == 2 * len(case.history),
            "setup_did_not_commit_all_original_messages",
        )
    return records
