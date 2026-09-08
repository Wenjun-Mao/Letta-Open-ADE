from __future__ import annotations

from pathlib import Path

from ade_api.features.agent_runtime import release_policy
from ade_api.features.agent_runtime.release_evidence import (
    AgentStudioAgentBundle,
    AgentStudioReleaseEvidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_current_policy_roots_and_singletons_are_resolvable() -> None:
    assert set(release_policy.production_policy_hashes(PROJECT_ROOT)) == {
        "prompt",
        "tool",
        "schema",
        "retrieval",
    }


def test_mutable_deployment_manifest_is_validated_separately_from_policy() -> None:
    tool_roots = release_policy.POLICY_INPUT_ROOTS["tool"]
    tool_files = release_policy.POLICY_INPUT_FILES["tool"]

    assert "config/model-router" not in tool_roots
    assert "config/model-router/model-profiles.json" in tool_files
    assert "config/model-router/sources.json" in tool_files
    assert "config/model-router/deployment-manifest.json" not in tool_files


def test_policy_hash_includes_files_added_under_a_governed_root(tmp_path: Path) -> None:
    governed_root = tmp_path / "runtime"
    governed_root.mkdir()
    (governed_root / "existing.py").write_text("existing\n", encoding="utf-8")

    before = release_policy._policy_bundle_hash(
        tmp_path,
        roots=("runtime",),
        files=(),
    )
    (governed_root / "new_runtime_contract.py").write_text(
        "new contract\n", encoding="utf-8"
    )
    after = release_policy._policy_bundle_hash(
        tmp_path,
        roots=("runtime",),
        files=(),
    )

    assert after != before


def test_policy_hash_ignores_generated_python_bytecode(tmp_path: Path) -> None:
    governed_root = tmp_path / "runtime"
    cache = governed_root / "__pycache__"
    cache.mkdir(parents=True)
    (governed_root / "contract.py").write_text("contract\n", encoding="utf-8")

    before = release_policy._policy_bundle_hash(
        tmp_path,
        roots=("runtime",),
        files=(),
    )
    (cache / "contract.cpython-312.pyc").write_bytes(b"bytecode")
    after = release_policy._policy_bundle_hash(
        tmp_path,
        roots=("runtime",),
        files=(),
    )

    assert after == before


def test_release_validation_kwargs_uses_the_validated_evidence_contract(
    monkeypatch,
) -> None:
    release = AgentStudioReleaseEvidence(
        evidence_sha256="a" * 64,
        qualification_run_id="native-run",
        evaluated_source_revision="b" * 40,
        evaluated_source_fingerprint="c" * 64,
        route_aliases={
            "conversation": "router::conversation",
            "reviewer": "router::reviewer",
            "retriever": "router::retriever",
        },
        agent_bundle=AgentStudioAgentBundle(
            prompt_key="reviewed_prompt",
            persona_key="reviewed_persona",
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
            "prompt_key": "reviewed_prompt",
            "persona_key": "reviewed_persona",
            "tool_names": ["search_memory"],
        },
        "source_clean": True,
    }
