"""Readback integrity, not semantic Memory or Character scoring."""

from datetime import datetime
import hashlib
import json

from .wire_capture import require


def validate_readbacks(readbacks, observation, manifest, case, run):
    source = readbacks.source_session
    probe = readbacks.probe_session
    scope = manifest.scope
    for session, conversation_id in (
        (source, manifest.source_conversation_id),
        (probe, manifest.probe_conversation_id),
    ):
        require(
            session["conversation"]["id"] == conversation_id
            and session["memory_subject"]["id"] == scope["subject_id"]
            and session["agent_definition"]["agent_definition_id"]
            == scope["character_root_id"],
            "session_scope_mismatch",
        )
        definition = session["agent_definition"]
        require(
            definition["persona_sha256"]
            == hashlib.sha256(run.runtime.persona_text.encode()).hexdigest()
            and definition["prompt_sha256"]
            == hashlib.sha256(run.runtime.system_prompt.encode()).hexdigest(),
            "authored_version_binding_mismatch",
        )
        deployments = {row["role"]: row for row in definition["deployments"]}
        require(
            deployments["conversation"]["fingerprint"]
            == run.runtime.character_identity_sha256
            and deployments["compaction"]["fingerprint"]
            == run.runtime.context_compaction_identity_sha256,
            "definition_model_binding_mismatch",
        )
    for state in (readbacks.source_initial_state, readbacks.probe_initial_state):
        require(
            state["conversation"]["messages"] == []
            and state["conversation"].get("summary") is None
            and state["conversation"]["message_total"] == 0,
            "initial_conversation_not_empty",
        )
    for page in (
        readbacks.source_initial_memories,
        readbacks.probe_initial_memories,
        readbacks.source_initial_deliveries,
    ):
        require(
            page["total"] == 0 and page["items"] == [], "initial_relationship_not_empty"
        )
    final_messages = readbacks.source_state["conversation"]["messages"]
    require(
        len(final_messages)
        == len(observation.source_messages)
        == len(case.history) * 2,
        "source_history_incomplete",
    )
    users = iter(case.history)
    for actual, saved in zip(observation.source_messages, final_messages, strict=True):
        require(
            actual.message_id == saved["id"]
            and actual.role == saved["role"]
            and actual.content == saved["content"]
            and actual.occurred_at
            == datetime.fromisoformat(saved["created_at"].replace("Z", "+00:00")),
            "source_record_not_from_saved_product_message",
        )
        if actual.role == "user":
            seed = next(users)
            require(
                actual.fixture_id == seed.fixture_id and actual.content == seed.content,
                "seed_not_exact",
            )
        else:
            require(actual.fixture_id is None, "authored_assistant_history_not_allowed")
    source_ids = {row["id"] for row in final_messages}
    deliveries = readbacks.deliveries
    require(
        deliveries["total"] == len(deliveries["items"]) == len(source_ids)
        and {row["message_id"] for row in deliveries["items"]} == source_ids,
        "delivery_source_set_mismatch",
    )
    require(
        all(
            row["status"] == "retained" and row["accepted_at"] and row["retained_at"]
            for row in deliveries["items"]
        ),
        "source_delivery_not_retained",
    )
    operations = readbacks.operations
    require(
        operations["total"] == len(operations["items"])
        and all(row["status"] == "completed" for row in operations["items"]),
        "native_processing_not_complete",
    )
    require(
        any(
            row["operation_type"] in {"consolidation", "consolidate"}
            for row in operations["items"]
        ),
        "automatic_consolidation_not_observed",
    )
    require(
        readbacks.memories["total"] == len(readbacks.memories["items"]),
        "memory_readback_incomplete",
    )
    require(
        {row["delivery"]["message_id"] for row in readbacks.source_documents}
        == source_ids,
        "native_source_readback_incomplete",
    )
    for document in readbacks.source_documents:
        original = json.loads(document["native_original_text"])
        saved = next(
            row
            for row in final_messages
            if row["id"] == document["delivery"]["message_id"]
        )
        require(
            original["message_id"] == saved["id"]
            and original["content"] == document["content"] == saved["content"]
            and original["speaker"] == saved["role"]
            and original["conversation_id"] == manifest.source_conversation_id,
            "native_source_identity_or_content_changed",
        )
        require(
            original["definition_version_id"]
            == document["definition_version_id"]
            == source["agent_definition"]["id"]
            and original["sequence"] == saved["sequence"]
            and original["status"]
            == ("accepted" if saved["role"] == "user" else "committed")
            and datetime.fromisoformat(original["occurred_at"].replace("Z", "+00:00"))
            == datetime.fromisoformat(saved["created_at"].replace("Z", "+00:00")),
            "native_source_time_or_version_changed",
        )
        context = json.loads(document["native_context"])
        require(
            context["relationship"] == manifest.scope,
            "native_antecedent_scope_mismatch",
        )
        previous = 0
        for antecedent in context["earlier_context_only"]:
            row = next(
                (
                    row
                    for row in final_messages
                    if row["id"] == antecedent["message_id"]
                ),
                None,
            )
            require(
                row is not None
                and previous < antecedent["sequence"] < saved["sequence"]
                and antecedent["content"] == row["content"]
                and antecedent["speaker"] == row["role"],
                "native_antecedent_not_original_dialogue",
            )
            previous = antecedent["sequence"]
    require(
        observation.memory_snapshot == readbacks.model_dump(mode="json"),
        "observation_memory_snapshot_mismatch",
    )
    require(
        observation.delivery_receipts == deliveries["items"],
        "observation_delivery_receipt_mismatch",
    )
