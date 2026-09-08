from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from workflows.evals.agent_runtime_acceptance.artifacts import RoundArtifactWriter
from workflows.evals.agent_runtime_acceptance.proposal import (
    build_promotion_proposal,
)


def test_round_artifacts_are_atomic_and_content_addressed(tmp_path: Path) -> None:
    writer = RoundArtifactWriter(tmp_path, "run-a")
    preflight = writer.write_preflight(
        {"kind": "agent-runtime-preflight", "passed": True}
    )
    preflight_payload = json.loads(preflight.path.read_text(encoding="utf-8"))
    assert preflight_payload["preflight_sha256"] == preflight.sha256
    assert preflight.path.parent == writer.root
    artifact = writer.write_round(
        1,
        {"kind": "primary", "case_keys": ["a"], "passed": True},
        [{"run_id": "run-1", "sequence": 1}],
    )

    payload = json.loads(artifact.round_path.read_text(encoding="utf-8"))
    assert payload["artifact_sha256"] == artifact.sha256
    assert artifact.events_path.is_file()
    compatibility = writer.write_round(
        1,
        {"kind": "llama-compatibility", "case_keys": ["a"], "passed": True},
        [],
    )
    assert compatibility.round_path.parent != artifact.round_path.parent


def test_promotion_proposal_requires_complete_live_primary_matrix(
    tmp_path: Path,
) -> None:
    snapshots = (
        {
            "role": "conversation",
            "deployment_id": "chat",
            "route_alias": "router::chat",
            "fingerprint": "a" * 64,
        },
        {
            "role": "reviewer",
            "deployment_id": "chat",
            "route_alias": "router::chat",
            "fingerprint": "a" * 64,
        },
        {
            "role": "retriever",
            "deployment_id": "embedding",
            "route_alias": "router::embedding",
            "fingerprint": "b" * 64,
        },
    )
    rounds = tuple(
        SimpleNamespace(
            index=index,
            kind="primary",
            execution_mode="live-api",
            complete_matrix=True,
            passed=True,
            case_keys=("a", "b"),
            artifact_sha256=f"{'a' * 63}{index}",
            deployment_fingerprints={
                "conversation": "a" * 64,
                "reviewer": "a" * 64,
                "retriever": "b" * 64,
            },
            cases=(
                SimpleNamespace(
                    resources=SimpleNamespace(deployment_snapshots=snapshots)
                ),
            ),
        )
        for index in range(1, 4)
    )
    proposal = build_promotion_proposal(
        output_dir=tmp_path,
        run_id="run-a",
        rounds=rounds,
        canonical_case_keys=("a", "b"),
        required_rounds=3,
        provenance_sha256="b" * 64,
        preflight_sha256="2" * 64,
        source_revision="c" * 40,
        source_dirty=False,
        source_fingerprint="9" * 64,
        policy_hashes={
            "prompt": "d" * 64,
            "tool": "e" * 64,
            "schema": "f" * 64,
            "retrieval": "1" * 64,
        },
        qualification_config={
            "conversation_model_key": "router::chat",
            "reviewer_model_key": "router::chat",
            "embedding_model_key": "router::embedding",
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "rounds": 3,
            "timeout_seconds": 180,
            "retry_count": 0,
            "case_keys": [],
        },
        agent_bundle={
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "tool_names": ["search_memory"],
        },
    )

    assert proposal is not None
    assert proposal.payload["apply_owner"] == "coordinator"
    assert proposal.payload["agent_bundle"] == {
        "prompt_key": "chat_v20260516",
        "persona_key": "chat_linxiaotang",
        "tool_names": ["search_memory"],
    }
    assert set(proposal.payload["deployment_bindings"]) == {
        "conversation",
        "reviewer",
        "retriever",
    }
    assert proposal.path.is_file()
    assert not (tmp_path / "deployment-manifest.json").exists()

    filtered = build_promotion_proposal(
        output_dir=tmp_path,
        run_id="run-filtered",
        rounds=rounds,
        canonical_case_keys=("a", "b"),
        required_rounds=3,
        provenance_sha256="b" * 64,
        preflight_sha256="2" * 64,
        source_revision="c" * 40,
        source_dirty=False,
        source_fingerprint="9" * 64,
        policy_hashes={
            "prompt": "d" * 64,
            "tool": "e" * 64,
            "schema": "f" * 64,
            "retrieval": "1" * 64,
        },
        qualification_config={
            "conversation_model_key": "router::chat",
            "reviewer_model_key": "router::chat",
            "embedding_model_key": "router::embedding",
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "rounds": 3,
            "timeout_seconds": 180,
            "retry_count": 0,
            "case_keys": ["a"],
        },
        agent_bundle={
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "tool_names": ["search_memory"],
        },
    )
    assert filtered is None
