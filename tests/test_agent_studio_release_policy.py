from __future__ import annotations

from pathlib import Path

import pytest

from ade_api.features.agent_runtime import release_policy
from ade_api.features.agent_runtime.errors import RuntimeNotReady
from ade_api.features.agent_runtime.release_evidence import (
    AgentStudioAgentBundle,
    AgentStudioReleaseEvidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_policy_hashes_cover_each_steady_state_policy() -> None:
    hashes = release_policy.production_policy_hashes(PROJECT_ROOT)

    assert set(hashes) == {"prompt", "tool", "schema", "retrieval"}
    assert all(len(digest) == 64 for digest in hashes.values())
    assert (
        "config/model-router/deployment-manifest.json"
        not in (release_policy.POLICY_INPUT_FILES["tool"])
    )


def test_policy_hash_includes_new_files_under_governed_roots(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    (runtime / "existing.py").write_text("existing\n", encoding="utf-8")

    before = release_policy._policy_bundle_hash(tmp_path, roots=("runtime",), files=())
    (runtime / "new_contract.py").write_text("new\n", encoding="utf-8")
    after = release_policy._policy_bundle_hash(tmp_path, roots=("runtime",), files=())

    assert before != after


def test_release_mode_fails_closed_without_validated_release_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ade_api.platform.project_paths as project_paths

    monkeypatch.setattr(project_paths, "PROJECT_ROOT", tmp_path)

    release_policy.ensure_agent_studio_release_ready("development")
    with pytest.raises(RuntimeNotReady, match="reviewed release evidence"):
        release_policy.ensure_agent_studio_release_ready("release")


def test_release_validation_kwargs_bind_validated_routes_bundle_and_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = AgentStudioReleaseEvidence(
        evidence_sha256="a" * 64,
        qualification_run_id="native-qualification",
        evaluated_source_revision="b" * 40,
        evaluated_source_fingerprint="c" * 64,
        route_aliases={
            "conversation": "router::chat",
            "reviewer": "router::chat",
            "retriever": "router::embedding",
        },
        agent_bundle=AgentStudioAgentBundle(
            prompt_key="chat_v20260516",
            persona_key="chat_linxiaotang",
            tool_names=("search_memory",),
        ),
    )
    monkeypatch.setattr(
        release_policy, "load_validated_agent_studio_release", lambda: release
    )
    monkeypatch.setattr(
        release_policy,
        "current_production_policy_hashes",
        lambda: {"prompt": "1" * 64},
    )
    monkeypatch.setattr(release_policy, "source_tree_is_clean", lambda: True)

    assert release_policy.release_validation_kwargs("release") == {
        "expected_policy_hashes": {"prompt": "1" * 64},
        "expected_route_aliases": release.route_aliases,
        "expected_agent_bundle": {
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "tool_names": ["search_memory"],
        },
        "source_clean": True,
    }
