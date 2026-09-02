from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from ade_api.features.agent_runtime_v3.contracts import AcceptTurnRequest
from ade_api.features.agent_runtime_v3.database_boundary import DEFAULT_WORKSPACE_ID
from ade_api.features.agent_runtime_v3.errors import (
    IdempotencyConflict,
    RuntimeNotReady,
)
from ade_api.features.agent_runtime_v3.run_service import RunService
import ade_api.features.agent_runtime_v3.run_service as run_service_module
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


def test_agent_studio_turn_fails_at_release_gate_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Connection:
        pass

    class _Engine:
        @asynccontextmanager
        async def connect(self):
            yield _Connection()

    class _Database:
        engine = _Engine()

        async def ensure_ready(self) -> None:
            return None

        @asynccontextmanager
        async def translated_errors(self):
            yield

    class _Conversations:
        def __init__(self, _connection) -> None:
            pass

        async def get(self, _conversation_id: str) -> dict[str, object]:
            return {
                "id": "conversation-1",
                "workspace_id": DEFAULT_WORKSPACE_ID,
                "purpose": "agent_studio",
            }

    monkeypatch.setattr(run_service_module, "ConversationRepository", _Conversations)
    monkeypatch.setattr(
        run_service_module, "RunRepository", lambda _connection: object()
    )

    def _reject_release(_mode: str) -> None:
        raise RuntimeNotReady("cutover evidence missing")

    monkeypatch.setattr(
        run_service_module,
        "ensure_agent_studio_release_ready",
        _reject_release,
    )
    service = RunService(
        database=_Database(),
        settings=SimpleNamespace(agent_runtime_v3_mode="release"),
        router_transport=object(),
    )

    with pytest.raises(RuntimeNotReady, match="cutover evidence missing"):
        asyncio.run(
            service.accept_turn(
                "conversation-1",
                AcceptTurnRequest(content="hello", idempotency_key="turn-1"),
            )
        )
