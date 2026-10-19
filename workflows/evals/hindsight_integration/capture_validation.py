"""Join public ADE, runtime observations and final Router request records."""

import hashlib

from .checks import reject_sensitive_fields
from .capture_components import context_components, validate_conversation_chain
from .wire_capture import require, validate_wire


def qualify_run_capture(
    *,
    run: dict,
    export: dict,
    state: dict,
    wires: list[dict],
    scope: dict,
    expected_input: str,
    source: dict,
    fresh_probe: bool,
    events: list[dict],
) -> dict:
    reject_sensitive_fields(export)
    require(run["status"] == export["run_status"] == "succeeded", "run_not_succeeded")
    run_id = run["id"]
    require(
        export["run_id"] == run_id and export["workspace_id"] == scope["workspace_id"],
        "export_scope_mismatch",
    )
    require(state["id"] == run["conversation_id"], "conversation_mismatch")
    require(
        state["memory_subject_id"] == scope["subject_id"],
        "conversation_subject_mismatch",
    )
    user = [
        row
        for row in state["messages"]
        if row["run_id"] == run_id and row["role"] == "user"
    ]
    reply = [
        row
        for row in state["messages"]
        if row["run_id"] == run_id and row["role"] == "assistant"
    ]
    require(
        len(user) == len(reply) == 1 and user[0]["content"] == expected_input,
        "saved_message_mismatch",
    )
    require(
        export["committed_assistant_message_ids"] == [reply[0]["id"]],
        "uncommitted_reply",
    )
    saved = {row["id"]: row for row in export["saved_attempts"]}
    require(len(saved) == run["attempt_count"], "saved_attempt_count_mismatch")
    require(
        sum(row["status"] == "succeeded" for row in saved.values()) == 1,
        "no_unique_successful_attempt",
    )
    observed = {row["attempt_id"]: row["records"] for row in export["observations"]}
    require(len(observed) == len(export["observations"]), "duplicate_attempt_capture")
    require(set(saved) == set(observed), "missing_or_foreign_attempt_capture")
    wire_map = {item["request"]["request_id"]: item for item in wires}
    require(len(wire_map) == len(wires), "duplicate_wire_identity")
    used_wire_ids = set()
    packed = []
    for attempt_id, records in observed.items():
        require(
            records
            and records[0]["type"] == "attempt_execution.started"
            and records[-1]["type"] == "attempt_execution.finished",
            "attempt_capture_unfinished",
        )
        for sequence, row in enumerate(records, 1):
            require(
                row["sequence"] == sequence and row["input_complete"] is True,
                "attempt_capture_gap_or_private_input",
            )
            identity = row["identity"]
            require(
                identity
                == {
                    "run_id": run_id,
                    "attempt_id": attempt_id,
                    "workspace_id": scope["workspace_id"],
                    "conversation_id": run["conversation_id"],
                },
                "attempt_identity_mismatch",
            )
        build = records[0]["value"]
        require(
            all(
                build[key] == source[key]
                for key in ("source_revision", "source_fingerprint", "source_dirty")
            ),
            "captured_source_mismatch",
        )
        require(build["source_dirty"] in {"false", "0"}, "dirty_source_capture")
        require(
            records[-1]["value"]["observation_incomplete"] is False,
            "observer_reported_incomplete",
        )
        starts = {
            row["value"]["request_id"]: row["value"]
            for row in records
            if row["type"] == "model_request.started"
        }
        finishes = {
            row["value"]["request_id"]: row["value"]
            for row in records
            if row["type"] == "model_request.finished"
        }
        require(
            len(starts)
            == sum(row["type"] == "model_request.started" for row in records)
            and len(finishes)
            == sum(row["type"] == "model_request.finished" for row in records),
            "duplicate_request_capture",
        )
        require(set(starts) == set(finishes), "request_capture_unfinished")
        public_ids = [
            row["payload"]["request_id"]
            for row in events
            if row["type"] == "model.request.started"
            and row.get("attempt") == saved[attempt_id]["attempt_number"]
        ]
        require(
            len(public_ids) == len(starts) and set(public_ids) == set(starts),
            "public_request_count_or_identity_mismatch",
        )
        contexts = [
            row["value"] for row in records if row["type"] == "context.composed"
        ]
        sources = [row["value"] for row in records if row["type"] == "context.sources"]
        lookups = [
            row["value"] for row in records if row["type"] == "memory_lookup.completed"
        ]
        if saved[attempt_id]["status"] == "succeeded":
            require(
                len(contexts) == len(sources) == 1,
                "context_capture_missing_or_duplicated",
            )
            require(
                sources[0]["current_user_message_id"] == user[0]["id"],
                "current_source_mismatch",
            )
            require(
                sources[0]["definition_root_id"] == scope["character_root_id"],
                "context_character_mismatch",
            )
            automatic = [row for row in lookups if row["phase"] == "automatic"]
            require(len(automatic) == 1, "automatic_recall_missing_or_duplicated")
            require(
                all(row["bank_id"] == sources[0]["bank_id"] for row in lookups),
                "cross_bank_lookup",
            )
            require(
                set(contexts[0]["automatic_memory_ids"])
                <= set(automatic[0]["selected_ids"]),
                "unobserved_memory_in_context",
            )
            if fresh_probe:
                require(
                    sources[0]["message_ids"] == [user[0]["id"]]
                    and sources[0]["summary"] is None,
                    "probe_has_local_history_or_summary",
                )
                require(
                    not any(
                        part["kind"] == "local_dialogue"
                        or (part["kind"] == "summary" and part["present"])
                        for part in contexts[0]["components"]
                    ),
                    "probe_context_has_non_hindsight_history",
                )
        conversation_chain = []
        for request_id, start in starts.items():
            if start["operation"] == "catalog":
                continue
            finish = finishes[request_id]
            router_id = finish["router_request_id"]
            require(
                router_id in wire_map and router_id not in used_wire_ids,
                "missing_or_reused_wire_request",
            )
            wire = wire_map[router_id]
            request = validate_wire(wire)
            if source.get("activation_id"):
                require(
                    request["activation_id"] == source["activation_id"]
                    and request["source_revision"] == source["source_revision"],
                    "wire_activation_or_source_mismatch",
                )
            metadata = request["metadata"]
            require(
                all(
                    metadata.get(key) == value
                    for key, value in {
                        **scope,
                        "run_id": run_id,
                        "attempt_id": attempt_id,
                        "conversation_id": run["conversation_id"],
                        "ade_request_id": request_id,
                        "role": start["stage"],
                        "phase": "reply",
                    }.items()
                ),
                "wire_join_mismatch",
            )
            require(
                request["body"]["messages"] == start["payload"]["messages"],
                "router_changed_messages",
            )
            require(
                request["body"].get("tools") == start["payload"].get("tools"),
                "router_changed_tools",
            )
            used_wire_ids.add(router_id)
            parts = (
                context_components(contexts[0], request["body"])
                if start["stage"] == "conversation"
                else []
            )
            if start["stage"] == "conversation":
                conversation_chain.append((start, wire))
            elif start["stage"] == "compaction":
                compaction_sources = [
                    row["value"]
                    for row in records
                    if row["type"] == "compaction.sources"
                ]
                require(len(compaction_sources) == 1, "compaction_sources_missing")
                parts = [
                    {
                        "kind": "compaction_policy"
                        if index == 0
                        else "compaction_input",
                        "message_index": index,
                        "start": 0,
                        "end": len(item["content"]),
                        "sha256": hashlib.sha256(item["content"].encode()).hexdigest(),
                        "source_ids": compaction_sources[0]["source_message_ids"]
                        if index
                        else [],
                    }
                    for index, item in enumerate(request["body"]["messages"])
                ]
            packed.append(
                {
                    "attempt_id": attempt_id,
                    "stage": start["stage"],
                    "ade_request_id": request_id,
                    "router_request_id": router_id,
                    "components": parts,
                }
            )
        if saved[attempt_id]["status"] == "succeeded":
            validate_conversation_chain(
                conversation_chain, reply[0]["content"], lookups
            )
            completed = [
                row["payload"]
                for row in events
                if row["type"] == "run.completed"
                and row.get("attempt") == saved[attempt_id]["attempt_number"]
            ]
            require(
                len(completed) == 1
                and completed[0]["model_request_counts"]["conversation"]
                == len(conversation_chain),
                "committed_request_count_mismatch",
            )
    require(used_wire_ids == set(wire_map), "unjoined_wire_request")
    require(
        any(row["stage"] == "conversation" for row in packed), "no_character_request"
    )
    return {
        "run_id": run_id,
        "user_message_id": user[0]["id"],
        "reply_message_id": reply[0]["id"],
        "reply": reply[0]["content"],
        "requests": packed,
    }
