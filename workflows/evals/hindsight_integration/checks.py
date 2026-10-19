"""Structural evidence checks. These never grade conversation meaning."""

from __future__ import annotations

from .models import Attempt, Capture, Case, Run


def reject_sensitive_fields(value: object) -> None:
    """Reject credential/private-reasoning fields; do not silently redact evidence."""
    forbidden = {
        "authorization",
        "api_key",
        "access_token",
        "refresh_token",
        "password",
        "client_secret",
        "reasoning_content",
        "encrypted_content",
    }
    if isinstance(value, dict):
        if any(str(key).lower() in forbidden for key in value):
            raise ValueError(
                "Credential or private-reasoning field in capture; exclude it at the source"
            )
        for child in value.values():
            reject_sensitive_fields(child)
    elif isinstance(value, list):
        for child in value:
            reject_sensitive_fields(child)


def mechanical_issues(
    run: Run, case: Case, attempt: Attempt, capture: Capture
) -> list[str]:
    observation = capture.observation
    issues: list[str] = []
    if observation.status != "completed":
        issues.append(f"execution_{observation.status}")
    if observation.stage != "finished":
        issues.append(f"stopped_at_{observation.stage}")
    if observation.observed_runtime != run.runtime:
        issues.append("runtime_binding_mismatch_or_missing")
    if not observation.input_complete:
        issues.append("incomplete_generation_input")
    if not observation.source_complete:
        issues.append("incomplete_source_capture")
    if observation.mode == "live_capture" and observation.product_capture is None:
        issues.append("missing_validated_product_capture_provenance")
    expected_provenance = {
        "user_dialogue": "product_dialogue",
        "controlled_history": "controlled_history",
        "creation": "no_history",
    }[case.history_kind]
    if observation.history_provenance != expected_provenance:
        issues.append("history_provenance_mismatch_or_missing")
    source, target = observation.source_scope, observation.target_scope
    if source is None or target is None:
        issues.append("missing_relationship_scope")
    else:
        for field in ("workspace", "subject", "character_root"):
            expected_equal = getattr(case.source_scope, field) == getattr(
                case.target_scope, field
            )
            if (getattr(source, field) == getattr(target, field)) != expected_equal:
                issues.append(f"relationship_{field}_mismatch")
        if any(scope != target for scope in observation.recalled_scopes):
            issues.append("cross_relationship_recall")
    if not observation.probe_conversation_id:
        issues.append("missing_probe_conversation")
    if case.history and (
        not observation.source_conversation_id
        or observation.source_conversation_id == observation.probe_conversation_id
    ):
        issues.append("probe_is_not_a_fresh_conversation")
    receipt = observation.fresh_state_receipt or {}
    if (
        receipt.get("source_empty_before_setup") is not True
        or receipt.get("target_empty_before_setup") is not True
    ):
        issues.append("missing_fresh_state_proof")
    if not receipt.get("source_readback") or not receipt.get("target_readback"):
        issues.append("missing_fresh_state_readback")

    _source_issues(case, capture, issues)
    if case.history:
        if observation.retention != "complete":
            issues.append("source_retention_not_complete")
        if observation.consolidation != "complete":
            issues.append("source_consolidation_not_complete")
        if not observation.delivery_receipts:
            issues.append("missing_delivery_receipts")
    elif (
        observation.retention != "not_applicable"
        or observation.consolidation != "not_applicable"
    ):
        issues.append("empty_history_processing_mismatch")
    if observation.memory_snapshot is None or observation.recall_payload is None:
        issues.append("missing_memory_or_recall_capture")
    _request_issues(run, case, attempt, capture, issues)
    if (
        not observation.reply
        or not observation.reply_committed
        or not observation.reply_message_id
    ):
        issues.append("missing_committed_reply")
    if capture.captured_at < attempt.started_at:
        issues.append("capture_precedes_attempt")
    return sorted(set(issues))


def _source_issues(case: Case, capture: Capture, issues: list[str]) -> None:
    observation = capture.observation
    messages = observation.source_messages
    if len({message.message_id for message in messages}) != len(messages):
        issues.append("duplicate_source_message")
    bound = [message for message in messages if message.fixture_id is not None]
    if [message.fixture_id for message in bound] != [
        message.fixture_id for message in case.history
    ]:
        issues.append("source_fixture_sequence_mismatch")
    else:
        for actual, expected in zip(bound, case.history, strict=True):
            if actual.role != expected.role or actual.content != expected.content:
                issues.append("source_fixture_content_mismatch")
    if not case.history and messages:
        issues.append("unexpected_creation_history")
    for message in messages:
        if (
            message.scope != observation.source_scope
            or message.conversation_id != observation.source_conversation_id
        ):
            issues.append("source_attribution_mismatch")
        expected_status = "accepted" if message.role == "user" else "committed"
        if message.status != expected_status:
            issues.append("source_message_not_accepted_or_committed")
    if any(a.occurred_at > b.occurred_at for a, b in zip(messages, messages[1:])):
        issues.append("source_chronology_mismatch")
    if observation.requests and messages:
        if max(message.occurred_at for message in messages) > min(
            request.sent_at for request in observation.requests
        ):
            issues.append("source_follows_probe_request")


def _request_issues(
    run: Run, case: Case, attempt: Attempt, capture: Capture, issues: list[str]
) -> None:
    requests = capture.observation.requests
    if not requests:
        issues.append("missing_generation_requests")
    if len({request.request_id for request in requests}) != len(requests):
        issues.append("duplicate_generation_request")
    for request in requests:
        if not attempt.started_at <= request.sent_at <= capture.captured_at:
            issues.append("generation_request_outside_attempt")
        if request.served_identity_sha256 != run.runtime.character_identity_sha256:
            issues.append("served_character_identity_mismatch")
        messages = request.body.get("messages")
        if (
            not isinstance(messages, list)
            or not messages
            or any(not isinstance(item, dict) for item in messages)
        ):
            issues.append("malformed_generation_messages")
            continue
        if any(
            item.get("role") not in {"system", "developer", "user", "assistant", "tool"}
            for item in messages
        ):
            issues.append("unknown_generation_role")
        users = [item for item in messages if item.get("role") == "user"]
        if len(users) != 1 or users[0].get("content") != case.prompt:
            issues.append("current_prompt_or_local_history_mismatch")
        systems = [
            item.get("content", "")
            for item in messages
            if item.get("role") in {"system", "developer"}
        ]
        if any(not isinstance(content, str) for content in systems):
            issues.append("non_text_system_input")
            continue
        combined = "\n".join(systems)
        if (
            run.runtime.persona_text not in combined
            or run.runtime.system_prompt not in combined
        ):
            issues.append("bound_persona_or_prompt_not_delivered")
