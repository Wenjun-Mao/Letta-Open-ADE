from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from ade_api.features.agent_runtime import resource_service
from ade_api.features.agent_runtime.database_boundary import DEFAULT_WORKSPACE_ID
from ade_api.features.agent_runtime.presenters import run_response
from ade_api.features.agent_runtime.resource_service import ResourceService


NOW = datetime(2026, 8, 30, tzinfo=UTC)


class _ConnectionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *_: object) -> None:
        return None


class _Database:
    class _Engine:
        def connect(self) -> _ConnectionContext:
            return _ConnectionContext()

    engine = _Engine()

    async def ensure_ready(self) -> None:
        return None

    def require_workspace(self, row):
        assert row["workspace_id"] == DEFAULT_WORKSPACE_ID

    @asynccontextmanager
    async def translated_errors(self):
        yield


class _ConversationRepository:
    async def get(self, conversation_id: str) -> dict[str, Any]:
        return {
            "id": conversation_id,
            "workspace_id": DEFAULT_WORKSPACE_ID,
            "agent_definition_version_id": "definition-1",
            "memory_subject_id": "subject-1",
            "version": 3,
            "archived_at": NOW,
            "created_at": NOW,
        }

    async def list_message_page(
        self,
        conversation_id: str,
        *,
        limit: int,
        before_sequence: int | None,
    ) -> tuple[int, list[dict[str, Any]]]:
        assert conversation_id == "conversation-1"
        assert limit == 200
        assert before_sequence is None
        return (
            1,
            [
                {
                    "id": "message-1",
                    "sequence": 1,
                    "role": "user",
                    "content": "My dog is Rocky.",
                    "run_id": None,
                    "created_at": NOW,
                }
            ],
        )

    async def latest_summary(self, conversation_id: str) -> dict[str, Any]:
        assert conversation_id == "conversation-1"
        return {
            "id": "summary-1",
            "version": 1,
            "previous_summary_id": None,
            "through_sequence": 1,
            "content": "The user has a dog named Rocky.",
            "run_id": "run-1",
            "model_key": "dgx_vllm::qwen",
            "model_fingerprint": "b" * 64,
            "provider_request_id": "provider-1",
            "content_sha256": "c" * 64,
            "prompt_sha256": "d" * 64,
            "input_sha256": "e" * 64,
            "policy_sha256": "f" * 64,
            "created_at": NOW,
        }

    async def list_summary_source_message_ids(self, summary_id: str) -> list[str]:
        assert summary_id == "summary-1"
        return ["message-1"]


def test_product_resource_service_cannot_restore_native_fact_inspection() -> None:
    assert not hasattr(ResourceService, "get_subject_memories")


def test_conversation_state_exposes_latest_summary_with_boundary_and_provenance(
    monkeypatch,
) -> None:
    repository = _ConversationRepository()
    monkeypatch.setattr(
        resource_service, "ConversationRepository", lambda _: repository
    )

    response = asyncio.run(
        ResourceService(_Database()).get_conversation_state("conversation-1")
    )

    assert response["archived_at"] == NOW
    assert response["messages"][0]["id"] == "message-1"

    assert response["summary"] == {
        "id": "summary-1",
        "version": 1,
        "previous_summary_id": None,
        "content": "The user has a dog named Rocky.",
        "source_boundary": {"through_sequence": 1, "message_ids": ["message-1"]},
        "provenance": {
            "run_id": "run-1",
            "model_key": "dgx_vllm::qwen",
            "model_fingerprint": "b" * 64,
            "provider_request_id": "provider-1",
            "content_sha256": "c" * 64,
            "prompt_sha256": "d" * 64,
            "input_sha256": "e" * 64,
            "policy_sha256": "f" * 64,
        },
        "created_at": NOW,
    }


def test_run_presenter_returns_the_controls_accepted_for_execution() -> None:
    response = run_response(
        {
            "id": "run-1",
            "conversation_id": "conversation-1",
            "status": "succeeded",
            "qualification_state": "unqualified",
            "attempt_count": 2,
            "timeout_seconds": 45,
            "retry_count": 1,
            "cancellation_requested_at": None,
            "error_code": None,
            "error_message": None,
            "created_at": NOW,
            "started_at": NOW,
            "finished_at": NOW,
        }
    )

    assert response["timeout_seconds"] == 45.0
    assert response["retry_count"] == 1
