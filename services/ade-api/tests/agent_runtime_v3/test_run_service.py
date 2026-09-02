from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.contracts import AcceptTurnRequest
from ade_api.features.agent_runtime_v3.errors import IdempotencyConflict
from ade_api.features.agent_runtime_v3.run_service import (
    _turn_request_hash,
    _validate_idempotent_replay,
)


def _conversation(*, version: int) -> dict[str, object]:
    return {
        "id": "conversation-1",
        "version": version,
    }


def _definition() -> dict[str, object]:
    return {
        "id": "definition-1",
        "version": 1,
        "deployment_snapshot": [{"role": "conversation", "fingerprint": "abc"}],
        "tool_names": ["search_memory"],
        "memory_policy_version": "typed-user-facts-v1",
    }


def test_exact_idempotent_replay_uses_the_original_conversation_version() -> None:
    request = AcceptTurnRequest(
        content="Remember Rocky",
        idempotency_key="turn-1",
        timeout_seconds=180,
        retry_count=0,
    )
    accepted_conversation = _conversation(version=3)
    definition = _definition()
    prior = {
        "accepted_conversation_version": 3,
        "request_hash": _turn_request_hash(request, accepted_conversation, definition),
    }

    _validate_idempotent_replay(
        prior,
        request=request,
        conversation=_conversation(version=4),
        definition=definition,
    )


def test_idempotent_replay_rejects_a_changed_request_after_completion() -> None:
    original = AcceptTurnRequest(content="Remember Rocky", idempotency_key="turn-1")
    definition = _definition()
    prior = {
        "accepted_conversation_version": 3,
        "request_hash": _turn_request_hash(
            original, _conversation(version=3), definition
        ),
    }
    changed = AcceptTurnRequest(content="Forget Rocky", idempotency_key="turn-1")

    with pytest.raises(IdempotencyConflict):
        _validate_idempotent_replay(
            prior,
            request=changed,
            conversation=_conversation(version=4),
            definition=definition,
        )
