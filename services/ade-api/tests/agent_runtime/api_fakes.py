"""Controlled public API response fixtures, not runtime or native semantics."""

from datetime import UTC, datetime


NOW = datetime(2026, 8, 29, tzinfo=UTC)


class _FakeService:
    health_ready = True

    async def get_health(self):
        return {
            "status": "ready" if self.health_ready else "not_ready",
            "database_ready": True,
            "worker_ready": self.health_ready,
            "compatible_worker_count": 1 if self.health_ready else 0,
            "matching_build_worker_count": 1 if self.health_ready else 0,
            "freshness_seconds": 45,
            "checked_at": NOW,
            "compatibility_fingerprint": "f" * 64,
            "source_revision": "test-revision",
            "source_dirty": False,
            "source_fingerprint": "s" * 64,
            "latest_heartbeat_at": NOW if self.health_ready else None,
        }

    async def get_agent_studio_options(self):
        return {
            "runtime": "ade_native",
            "default_bundle_key": "ade_native_dgx_v1",
            "bundles": [
                {
                    "key": "ade_native_dgx_v1",
                    "name": "ADE Native DGX",
                    "model_key": "dgx_vllm::qwen",
                    "compaction_model_key": "dgx_vllm::qwen",
                    "prompt_key": "chat_v20260516",
                    "persona_key": "chat_linxiaotang",
                    "tool_names": ["search_memory"],
                    "memory_policy_version": "hindsight-message-v1",
                    "qualification_state": "qualified",
                    "deployments": [],
                }
            ],
            "default_timeout_seconds": 180,
            "default_retry_count": 0,
            "max_retry_count": 5,
        }

    async def create_agent_studio_session(self, request):
        assert request.idempotency_key == "studio-session-1"
        return _agent_studio_session()

    async def create_evaluation_session(self, request):
        assert request.idempotency_key == "evaluation-session-1"
        assert request.tool_names == ["search_memory", "get_weather"]
        return _evaluation_session()

    async def list_agent_studio_sessions(self, **kwargs):
        assert kwargs == {"include_archived": False, "limit": 100, "offset": 0}
        return {"total": 1, "items": [_agent_studio_session()]}

    async def get_agent_studio_conversation_state(self, conversation_id, **kwargs):
        assert conversation_id == "00000000-0000-0000-0000-000000000014"
        assert kwargs == {"message_limit": 50, "before_sequence": None}
        return {
            **_agent_studio_session()["conversation"],
            "messages": [],
            "message_total": 0,
            "messages_truncated": False,
            "next_before_sequence": None,
            "summary": None,
        }

    async def get_evaluation_session_state(self, conversation_id, **kwargs):
        assert conversation_id == "00000000-0000-0000-0000-000000000024"
        assert kwargs == {"message_limit": 50, "before_sequence": None}
        session = _evaluation_session()
        return {
            "conversation": {
                **session["conversation"],
                "messages": [],
                "message_total": 0,
                "messages_truncated": False,
                "next_before_sequence": None,
                "summary": None,
            },
            "memory_subject": session["memory_subject"],
            "latest_run": None,
        }

    async def accept_turn(self, conversation_id, request):
        assert request.timeout_seconds == 180
        assert request.retry_count == 0
        return {
            "run_id": "00000000-0000-0000-0000-000000000004",
            "status": "pending",
            "events_url": "/api/v3/runs/00000000-0000-0000-0000-000000000004/events",
            "idempotent_replay": False,
        }

    async def get_run(self, run_id):
        return {
            "id": run_id,
            "conversation_id": "00000000-0000-0000-0000-000000000003",
            "status": "pending",
            "qualification_state": "unqualified",
            "attempt_count": 0,
            "timeout_seconds": 180,
            "retry_count": 0,
            "created_at": NOW,
        }


def _agent_studio_session():
    return {
        "session_id": "00000000-0000-0000-0000-000000000014",
        "idempotent_replay": False,
        "agent_definition": {
            "id": "00000000-0000-0000-0000-000000000012",
            "agent_definition_id": "00000000-0000-0000-0000-000000000011",
            "definition_key": "default_companion",
            "version": 1,
            "name": "Default companion",
            "prompt_key": "chat_v20260516",
            "prompt_sha256": "a" * 64,
            "persona_key": "chat_linxiaotang",
            "persona_sha256": "b" * 64,
            "tool_names": ["search_memory"],
            "memory_policy_version": "typed-user-facts-v1",
            "qualification_state": "qualified",
            "deployments": [],
            "archived_at": None,
            "created_at": NOW,
        },
        "memory_subject": {
            "id": "00000000-0000-0000-0000-000000000013",
            "external_key": "local-user",
            "display_name": "Local user",
            "version": 1,
            "archived_at": None,
            "created_at": NOW,
            "updated_at": NOW,
        },
        "conversation": {
            "id": "00000000-0000-0000-0000-000000000014",
            "agent_definition_id": "00000000-0000-0000-0000-000000000012",
            "memory_subject_id": "00000000-0000-0000-0000-000000000013",
            "title": "First conversation",
            "purpose": "agent_studio",
            "version": 1,
            "archived_at": None,
            "created_at": NOW,
        },
        "latest_run": None,
    }


def _evaluation_session():
    session = _agent_studio_session()
    session["session_id"] = "00000000-0000-0000-0000-000000000024"
    session["agent_definition"] = {
        **session["agent_definition"],
        "id": "00000000-0000-0000-0000-000000000022",
        "agent_definition_id": "00000000-0000-0000-0000-000000000021",
        "definition_key": "evaluation_fixture",
        "tool_names": ["search_memory", "get_weather"],
    }
    session["memory_subject"] = {
        **session["memory_subject"],
        "id": "00000000-0000-0000-0000-000000000023",
        "external_key": "evaluation:fixture",
    }
    session["conversation"] = {
        **session["conversation"],
        "id": "00000000-0000-0000-0000-000000000024",
        "agent_definition_id": "00000000-0000-0000-0000-000000000022",
        "memory_subject_id": "00000000-0000-0000-0000-000000000023",
        "purpose": "evaluation",
    }
    return session
