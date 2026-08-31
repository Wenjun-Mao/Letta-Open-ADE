from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from workflows.evals.chat_memory_eval.artifacts import ArtifactWriter, build_summary
from workflows.evals.chat_memory_eval.client import AdeApiClient, ApiRequestError
from workflows.evals.chat_memory_eval.config import (
    ADE_API_TRANSPORT_RETRIES,
    ConfigError,
    JUDGE_TRANSPORT_RETRIES,
    ade_api_timeout_seconds,
    apply_cli_overrides,
    effective_judge_model_key,
    load_config,
    router_model_key_from_agent_handle,
    router_v1_base_url,
    validate_config,
)
from workflows.evals.chat_memory_eval.fixtures import ExpectedFact, load_fixture
from workflows.evals.chat_memory_eval.judge import _parse_json_object
from workflows.evals.chat_memory_eval.provenance import (
    _OPTION_IDENTITY_FIELDS,
    _sha256,
    assert_created_agent_identities,
    capture_evaluation_provenance,
)
from workflows.evals.chat_memory_eval.scoring import (
    deterministic_round_score,
    score_expected_facts,
)
from workflows.evals.chat_memory_eval.workflow import _resolve_run_id, run_round


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_chat_memory_config_loads_defaults_and_cli_overrides(tmp_path) -> None:
    config = load_config(
        PROJECT_ROOT / "workflows" / "evals" / "chat_memory_eval" / "config.toml"
    )
    args = argparse.Namespace(
        api_base_url="",
        output_dir=str(tmp_path),
        model="openai-proxy/test::model",
        prompt_key="",
        persona_key="",
        embedding="",
        fixture_key="",
        judge_model_key="",
        rounds=1,
        timeout_seconds=60,
        retry_count=0,
        judge_enabled=False,
        keep_agents=False,
    )

    updated = apply_cli_overrides(config, args)

    assert config.prompt_key == "chat_v20260516"
    assert updated.output_dir == tmp_path
    assert updated.model == "openai-proxy/test::model"
    assert updated.rounds == 1
    assert updated.judge_enabled is False
    assert not hasattr(updated, "api_retry_count")


def test_chat_memory_config_rejects_non_idempotent_message_retries() -> None:
    config = load_config(
        PROJECT_ROOT / "workflows" / "evals" / "chat_memory_eval" / "config.toml"
    )

    with pytest.raises(ConfigError, match="server-owned idempotency"):
        validate_config(replace(config, retry_count=1))


def test_chat_memory_fixture_loads_restored_conversation() -> None:
    fixture = load_fixture(
        PROJECT_ROOT / "workflows" / "evals" / "chat_memory_eval" / "fixtures",
        "recent_user_chat_turns",
    )

    assert fixture.key == "recent_user_chat_turns"
    assert fixture.turns[0] == "你好，我叫张伟"
    assert [item.key for item in fixture.expected_facts] == [
        "user_name",
        "dog_name",
        "dog_breed",
    ]


def test_expected_fact_alias_matching_is_case_insensitive() -> None:
    scores = score_expected_facts(
        "姓名：张伟\n宠物：rocky 是一只 Husky",
        (
            ExpectedFact(key="name", label="Name", aliases=("张伟",)),
            ExpectedFact(key="dog", label="Dog", aliases=("Rocky",)),
            ExpectedFact(key="breed", label="Breed", aliases=("哈士奇", "husky")),
        ),
    )

    assert [score.passed for score in scores] == [True, True, True]


def test_deterministic_round_score_requires_memory_facts_and_no_forbidden_hits() -> (
    None
):
    score = deterministic_round_score(
        assistant_texts=["我是机器人，但是可以陪你聊天"],
        initial_human_memory="",
        final_human_memory="姓名：张伟\n宠物：Rocky",
        expected_facts=(
            ExpectedFact(key="name", label="Name", aliases=("张伟",)),
            ExpectedFact(key="breed", label="Breed", aliases=("哈士奇",)),
        ),
        forbidden_reply_substrings=("我是机器人",),
    )

    assert score["pass"] is False
    assert score["forbidden_hit_count"] == 1
    assert score["missing_expected_facts"] == ["breed"]


def test_router_model_key_derives_from_agent_studio_handle() -> None:
    assert (
        router_model_key_from_agent_handle("openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8")
        == "dgx_vllm::qwen3.6-35b-a3b-fp8"
    )


def test_eval_inherits_ade_api_router_location(monkeypatch) -> None:
    monkeypatch.setenv("ADE_API_MODEL_ROUTER_BASE_URL", "http://model-router:8010")

    config = load_config(
        PROJECT_ROOT / "workflows" / "evals" / "chat_memory_eval" / "config.toml"
    )

    assert router_v1_base_url(config) == "http://model-router:8010/v1"


def test_chat_memory_eval_uses_host_router_fallback_without_env(monkeypatch) -> None:
    monkeypatch.setenv("ADE_API_MODEL_ROUTER_BASE_URL", "")

    config = load_config(
        PROJECT_ROOT / "workflows" / "evals" / "chat_memory_eval" / "config.toml"
    )

    assert router_v1_base_url(config) == "http://127.0.0.1:8010/v1"


def test_judge_json_parser_recovers_object_from_text() -> None:
    assert _parse_json_object('notes\n{"pass": true, "score": 88}\nend') == {
        "pass": True,
        "score": 88,
    }


def test_chat_memory_artifact_writer_streams_csv_and_jsonl(tmp_path) -> None:
    csv_path = tmp_path / "run.csv"
    jsonl_path = tmp_path / "run.jsonl"
    row = {
        "run_id": "run-1",
        "round": 1,
        "status": "ok",
        "pass": True,
        "elapsed_seconds": 1.23,
    }

    with ArtifactWriter(csv_path=csv_path, jsonl_path=jsonl_path) as writer:
        writer.write_round(row, {"raw": row})

    assert "run_id" in csv_path.read_text(encoding="utf-8-sig")
    assert (
        json.loads(jsonl_path.read_text(encoding="utf-8"))["raw"]["run_id"] == "run-1"
    )
    summary = build_summary(
        run_id="run-1",
        csv_path=csv_path,
        jsonl_path=jsonl_path,
        summary_path=tmp_path / "s.json",
        rows=[row],
    )
    assert summary["rounds_passed"] == 1
    assert summary["run_id"] == "run-1"


def test_ade_api_client_never_retries_a_failed_post() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        assert request.method == "POST"
        return httpx.Response(503, json={"detail": "temporary failure"})

    with AdeApiClient(base_url="http://ade.test", timeout_seconds=1) as api:
        api._client.close()
        api._client = httpx.Client(
            base_url="http://ade.test", transport=httpx.MockTransport(handler)
        )
        with pytest.raises(ApiRequestError, match="503"):
            api.create_agent({"scenario": "chat"})

    assert attempts == 1


def test_run_id_is_preserved_or_generated_for_direct_cli_runs() -> None:
    assert _resolve_run_id("  test-center-run-id  ", "20260830_120000") == (
        "test-center-run-id"
    )
    generated = _resolve_run_id(None, "20260830_120000")
    assert generated.startswith("chat-memory-eval-20260830_120000-")


class _TemplateClient:
    def __init__(self, *, prompt: str = "System prompt", persona: str = "Persona"):
        self._contents = {"prompt": prompt, "persona": persona}

    def template(self, kind: str, key: str) -> dict[str, object]:
        content = self._contents[kind]
        return {
            "kind": kind,
            "scenario": "chat",
            "key": key,
            "label": key,
            "description": "",
            "content": content,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "updated_at": "2026-08-30T00:00:00Z",
        }


def _catalog_option(key: str, *, revision: str) -> dict[str, object]:
    option: dict[str, object] = {
        "key": key,
        "label": key,
        "source_id": "test",
        "source_label": "Test",
        "provider_model_id": key.split("/", 1)[-1],
        "upstream_provider_model_id": None,
        "sampling_defaults": {"temperature": 1.0},
        "scenario_sampling_defaults": {},
        "supports_top_k": True,
        "supports_thinking": False,
        "thinking_default_enabled": False,
        "profile_applied": True,
        "profile_source": "test",
        "agent_studio_candidate": True,
        "agent_studio_compatible": True,
        "deployment": {"fingerprint": {"artifact_revision": revision}},
    }
    option["identity_sha256"] = _sha256(
        {field: option.get(field) for field in _OPTION_IDENTITY_FIELDS}
    )
    return option


def _provenance_inputs() -> tuple[object, dict[str, object], object]:
    config = load_config(
        PROJECT_ROOT / "workflows" / "evals" / "chat_memory_eval" / "config.toml"
    )
    fixture = load_fixture(config.fixtures_dir, config.fixture_key)
    options = {
        "models": [_catalog_option(config.model, revision="model-r1")],
        "embeddings": [_catalog_option(config.embedding, revision="embed-r1")],
    }
    return config, options, fixture


def test_evaluation_provenance_records_effective_controls_and_source_identity(
    monkeypatch,
) -> None:
    config, options, fixture = _provenance_inputs()
    monkeypatch.setenv("ADE_SOURCE_REVISION", "a" * 40)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "b" * 64)
    first = capture_evaluation_provenance(
        run_id="run-1",
        api=_TemplateClient(),
        options=options,
        config=config,
        fixture=fixture,
        captured_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
    )
    second = capture_evaluation_provenance(
        run_id="run-2",
        api=_TemplateClient(),
        options=options,
        config=config,
        fixture=fixture,
        captured_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )

    assert first["configuration_sha256"] == second["configuration_sha256"]
    assert first["provenance_sha256"] != second["provenance_sha256"]
    assert first["controls"] == {
        "rounds": config.rounds,
        "timeout_seconds": config.timeout_seconds,
        "retry_count": config.retry_count,
        "ade_api_timeout_seconds": ade_api_timeout_seconds(config),
        "ade_api_transport_retries": ADE_API_TRANSPORT_RETRIES,
        "judge_transport_retries": JUDGE_TRANSPORT_RETRIES,
        "stop_on_error": config.stop_on_error,
        "keep_agents": config.keep_agents,
        "judge_enabled": config.judge_enabled,
        "effective_judge_model_key": effective_judge_model_key(config),
        "judge_timeout_seconds": config.judge_timeout_seconds,
        "evaluator_source_revision": "a" * 40,
        "evaluator_source_dirty": "false",
        "evaluator_source_fingerprint": "b" * 64,
    }
    assert first["prompt"]["content"] == "System prompt"
    assert first["model"]["deployment"]["fingerprint"]["artifact_revision"] == (
        "model-r1"
    )


def test_evaluation_configuration_identity_changes_with_content_model_or_source(
    monkeypatch,
) -> None:
    config, options, fixture = _provenance_inputs()
    baseline = capture_evaluation_provenance(
        run_id="run-1",
        api=_TemplateClient(),
        options=options,
        config=config,
        fixture=fixture,
    )
    changed_prompt = capture_evaluation_provenance(
        run_id="run-1",
        api=_TemplateClient(prompt="Changed system prompt"),
        options=options,
        config=config,
        fixture=fixture,
    )
    changed_options = {
        **options,
        "models": [_catalog_option(config.model, revision="model-r2")],
    }
    changed_model = capture_evaluation_provenance(
        run_id="run-1",
        api=_TemplateClient(),
        options=changed_options,
        config=config,
        fixture=fixture,
    )
    changed_control = capture_evaluation_provenance(
        run_id="run-1",
        api=_TemplateClient(),
        options=options,
        config=replace(config, stop_on_error=True),
        fixture=fixture,
    )
    monkeypatch.setenv("ADE_SOURCE_REVISION", "c" * 40)
    changed_evaluator = capture_evaluation_provenance(
        run_id="run-1",
        api=_TemplateClient(),
        options=options,
        config=config,
        fixture=fixture,
    )

    assert baseline["configuration_sha256"] != changed_prompt["configuration_sha256"]
    assert baseline["configuration_sha256"] != changed_model["configuration_sha256"]
    assert baseline["configuration_sha256"] != changed_control["configuration_sha256"]
    assert baseline["configuration_sha256"] != changed_evaluator["configuration_sha256"]


def test_created_agent_must_confirm_captured_provenance() -> None:
    config, options, fixture = _provenance_inputs()
    provenance = capture_evaluation_provenance(
        run_id="run-1",
        api=_TemplateClient(),
        options=options,
        config=config,
        fixture=fixture,
    )
    created = {
        "model_identity_sha256": provenance["model"]["identity_sha256"],
        "embedding_identity_sha256": provenance["embedding"]["identity_sha256"],
        "prompt_content_sha256": provenance["prompt"]["content_sha256"],
        "persona_content_sha256": provenance["persona"]["content_sha256"],
    }

    assert_created_agent_identities(created, provenance)
    created["prompt_content_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="prompt_content_sha256"):
        assert_created_agent_identities(created, provenance)


def test_identity_mismatched_created_agent_is_still_archived_and_purged() -> None:
    config, options, fixture = _provenance_inputs()
    provenance = capture_evaluation_provenance(
        run_id="run-1",
        api=_TemplateClient(),
        options=options,
        config=config,
        fixture=fixture,
    )

    class _MismatchedAgentApi:
        def __init__(self) -> None:
            self.archived: list[str] = []
            self.purged: list[str] = []

        def create_agent(self, _payload: dict[str, object]) -> dict[str, object]:
            return {
                "id": "agent-mismatch",
                "model_identity_sha256": "0" * 64,
                "embedding_identity_sha256": "0" * 64,
                "prompt_content_sha256": "0" * 64,
                "persona_content_sha256": "0" * 64,
            }

        def archive_agent(self, agent_id: str) -> dict[str, object]:
            self.archived.append(agent_id)
            return {}

        def purge_agent(self, agent_id: str) -> dict[str, object]:
            self.purged.append(agent_id)
            return {}

    api = _MismatchedAgentApi()

    row, raw = run_round(
        api=api,  # type: ignore[arg-type]
        config=replace(config, keep_agents=False),
        fixture=fixture,
        run_id="run-1",
        round_index=1,
        provenance=provenance,
    )

    assert row["status"] == "error"
    assert row["agent_id"] == "agent-mismatch"
    assert row["archived"] is True
    assert row["purged"] is True
    assert raw["deterministic_score"]["pass"] is False
    assert api.archived == ["agent-mismatch"]
    assert api.purged == ["agent-mismatch"]
