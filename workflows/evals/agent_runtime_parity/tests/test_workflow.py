from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

import pytest

from workflows.evals.agent_runtime_parity.artifacts import verify_json_artifact
from workflows.evals.agent_runtime_parity.config import ConfigError, ParityConfig
from workflows.evals.agent_runtime_parity.provenance import (
    OPTION_IDENTITY_FIELDS,
    _catalog_identity_sha256,
)
from workflows.evals.agent_runtime_parity.workflow import _build_comparison, run_parity


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _round() -> dict[str, Any]:
    score = {"checks": {"timeout_retry_controls_exact": True}}
    return {
        "round": 1,
        "pass": True,
        "legacy": {"score": score},
        "native": {"score": score},
    }


def test_comparison_requires_both_cleanup_paths() -> None:
    comparison = _build_comparison(
        run_id="parity-test-run",
        parity_spec_sha256="a" * 64,
        provenance_sha256="b" * 64,
        normalized_turns_sha256="c" * 64,
        preflight_error=None,
        comparability={"pass": True},
        expected_rounds=3,
        rounds=[_round(), _round(), _round()],
        cleanup={"completed": False},
    )

    assert comparison["pass"] is False
    assert comparison["checks"]["cleanup_complete"] is False


def test_comparison_passes_only_with_complete_pairing_and_cleanup() -> None:
    comparison = _build_comparison(
        run_id="parity-test-run",
        parity_spec_sha256="a" * 64,
        provenance_sha256="b" * 64,
        normalized_turns_sha256="c" * 64,
        preflight_error=None,
        comparability={"pass": True},
        expected_rounds=3,
        rounds=[_round(), _round(), _round()],
        cleanup={"completed": True},
    )

    assert comparison["pass"] is True


def test_workflow_writes_a_passing_three_round_bundle_without_live_calls(
    monkeypatch, tmp_path: Path
) -> None:
    source_identity = {
        "revision": "r" * 40,
        "dirty": False,
        "fingerprint": "s" * 64,
    }
    monkeypatch.setattr(
        "workflows.evals.agent_runtime_parity.workflow.capture_source_identity",
        lambda: source_identity,
    )
    monkeypatch.setattr(
        "workflows.evals.agent_runtime_parity.workflow.LegacyV2Client", _FakeLegacy
    )
    monkeypatch.setattr(
        "workflows.evals.agent_runtime_parity.workflow.NativeV3Client", _FakeNative
    )
    cleanup_calls: list[dict[str, Any]] = []

    async def fake_cleanup(**kwargs: Any) -> dict[str, Any]:
        cleanup_calls.append(kwargs)
        return {
            "completed": True,
            "legacy": {"completed": True},
            "native": {"completed": True},
        }

    monkeypatch.setattr(
        "workflows.evals.agent_runtime_parity.workflow._cleanup_all", fake_cleanup
    )
    config = ParityConfig(
        legacy_api_key="legacy",
        native_api_key="native",
        database_url="postgresql://ade:password@localhost/ade",
        output_dir=tmp_path,
        fixture_path=PROJECT_ROOT
        / "workflows/evals/chat_memory_eval/fixtures/recent_user_chat_turns.json",
    )

    summary = asyncio.run(run_parity(config, run_id="parity-fake-e2e"))

    assert summary["pass"] is True
    assert summary["rounds_passed"] == 3
    assert cleanup_calls[0]["native_definition_keys"] == (
        "parity-fake-e2e-r01-definition",
        "parity-fake-e2e-r02-definition",
        "parity-fake-e2e-r03-definition",
    )
    for name in ("parity_spec", "provenance", "comparison", "summary"):
        assert verify_json_artifact(Path(summary["artifact_paths"][name]))
    assert Path(summary["artifact_paths"]["normalized_turns"]).is_file()


def test_direct_workflow_call_rejects_retries_before_live_resources(
    tmp_path: Path,
) -> None:
    config = ParityConfig(
        legacy_api_key="legacy",
        native_api_key="native",
        database_url="postgresql://ade:password@localhost/ade",
        output_dir=tmp_path,
        fixture_path=PROJECT_ROOT
        / "workflows/evals/chat_memory_eval/fixtures/recent_user_chat_turns.json",
        retry_count=1,
    )

    with pytest.raises(ConfigError, match="retry_count must be 0"):
        asyncio.run(run_parity(config, run_id="parity-retry-rejected"))


class _FakeLegacy:
    def __init__(self, *_args: Any) -> None:
        self._agent_index = 0

    async def aclose(self) -> None:
        return None

    async def options(self) -> dict[str, Any]:
        return {
            "models": [_catalog_option("openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8")],
            "embeddings": [_catalog_option("letta/letta-free")],
        }

    async def template(self, kind: str, key: str) -> dict[str, Any]:
        content = "Prompt" if kind == "prompt" else "Persona"
        return {
            "kind": kind,
            "scenario": "chat",
            "key": key,
            "content": content,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }

    async def create_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._agent_index += 1
        return {"id": f"legacy-{self._agent_index}", **payload}

    async def send_message(self, **_kwargs: Any) -> dict[str, Any]:
        return {
            "sequence": [{"type": "assistant", "content": "当然可以。"}],
            "memory_diff": {},
        }

    async def persistent_state(self, _agent_id: str) -> dict[str, Any]:
        return {"memory_blocks": [{"label": "human", "value": "张伟 Rocky 哈士奇"}]}

    async def archive_agent(self, _agent_id: str) -> dict[str, Any]:
        return {"archived": True}

    async def purge_agent(self, _agent_id: str) -> dict[str, Any]:
        return {"ok": True}


class _FakeNative:
    def __init__(self, *_args: Any) -> None:
        self._turn = 0

    async def aclose(self) -> None:
        return None

    async def worker_health(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "database_ready": True,
            "worker_ready": True,
            "source_revision": "r" * 40,
            "source_dirty": False,
            "source_fingerprint": "s" * 64,
        }

    async def create_agent_studio_session(self, **kwargs: Any) -> dict[str, Any]:
        prompt_sha = hashlib.sha256("Prompt".encode("utf-8")).hexdigest()
        persona_sha = hashlib.sha256("Persona".encode("utf-8")).hexdigest()
        return {
            "session_id": "conversation-1",
            "idempotent_replay": False,
            "agent_definition": {
                "id": f"definition-{kwargs['definition_key']}",
                "definition_key": kwargs["definition_key"],
                "version": 1,
                "prompt_key": kwargs["prompt_key"],
                "prompt_sha256": prompt_sha,
                "persona_key": kwargs["persona_key"],
                "persona_sha256": persona_sha,
                "tool_names": ["search_memory"],
                "memory_policy_version": "typed-user-facts-v1",
                "qualification_state": "qualified",
                "deployments": [
                    _deployment("conversation", kwargs["model_key"]),
                    _deployment("reviewer", kwargs["reviewer_model_key"]),
                    _deployment("retriever", kwargs["embedding_model_key"]),
                ],
            },
            "memory_subject": {
                "id": "subject-1",
                "external_key": kwargs["subject_external_key"],
            },
            "conversation": {
                "id": "conversation-1",
                "agent_definition_id": f"definition-{kwargs['definition_key']}",
                "memory_subject_id": "subject-1",
                "archived_at": None,
            },
        }

    async def archive_agent_studio_session(self, _conversation_id: str):
        return {"conversation": {"id": "conversation-1", "archived_at": "now"}}

    async def restore_agent_studio_session(self, _conversation_id: str):
        return {"conversation": {"id": "conversation-1", "archived_at": None}}

    async def accept_turn(self, **_kwargs: Any) -> dict[str, Any]:
        self._turn += 1
        return {"run_id": f"run-{self._turn}", "events_url": "/events"}

    async def await_terminal(
        self, accepted: dict[str, Any], **_kwargs: Any
    ) -> tuple[dict[str, Any], tuple[Any, ...]]:
        return (
            {
                "id": accepted["run_id"],
                "status": "succeeded",
                "timeout_seconds": 180,
                "retry_count": 0,
                "attempt_count": 1,
            },
            (),
        )

    async def conversation_state(self, _conversation_id: str) -> dict[str, Any]:
        return {
            "messages": [
                {
                    "role": "assistant",
                    "run_id": f"run-{self._turn}",
                    "content": "当然可以。",
                }
            ]
        }

    async def subject_memories(self, _subject_id: str) -> dict[str, Any]:
        return {
            "facts": [
                {"status": "active", "value": "张伟"},
                {"status": "active", "value": "Rocky"},
                {"status": "active", "value": "哈士奇"},
            ]
        }


def _catalog_option(key: str) -> dict[str, Any]:
    option = {field: None for field in OPTION_IDENTITY_FIELDS}
    option["key"] = key
    option["identity_sha256"] = _catalog_identity_sha256(
        {field: option.get(field) for field in OPTION_IDENTITY_FIELDS}
    )
    return option


def _deployment(role: str, route_alias: str) -> dict[str, Any]:
    return {
        "deployment_id": f"{role}-deployment",
        "route_alias": route_alias,
        "fingerprint": f"{role}-fingerprint",
        "role": role,
        "lifecycle": "qualified",
        "qualification_state": "qualified",
    }
