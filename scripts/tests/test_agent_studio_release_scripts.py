from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from model_catalog_contracts.deployment_manifest import (
    DeploymentFingerprint,
    load_deployment_manifest,
)

from ade_api.features.agent_runtime.release_evidence import (
    REQUIRED_CONFORMANCE_TESTS,
    canonical_sha256,
)
from scripts import check_agent_studio_release_gate as release_gate
from scripts import record_agent_studio_conformance as conformance
from scripts import rebind_agent_runtime_policy as rebind
from scripts import promote_agent_studio_release as promote


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_governed_lineage_includes_new_runtime_files_but_not_unrelated_areas() -> None:
    assert release_gate.is_governed_source_path(
        "services/ade-api/src/ade_api/features/agent_runtime/new_contract.py"
    )
    assert release_gate.is_governed_source_path(
        "scripts/rebind_agent_runtime_policy.py"
    )
    assert not release_gate.is_governed_source_path("docs/release-notes.md")
    assert not release_gate.is_governed_source_path("apps/ade-web/src/app/page.tsx")
    assert not release_gate.is_governed_source_path(
        "workflows/evals/completed_evaluator/result.py"
    )


def test_rebind_invalidates_qualified_deployments_when_policy_changes() -> None:
    payload = json.loads(
        (PROJECT_ROOT / "config/model-router/deployment-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    updated = rebind.rebind_manifest(
        payload,
        {
            "prompt": "1" * 64,
            "tool": "2" * 64,
            "schema": "3" * 64,
            "retrieval": "4" * 64,
        },
    )

    assert all(
        updated_item["lifecycle"] == "candidate"
        for original_item, updated_item in zip(
            payload["deployments"], updated["deployments"], strict=True
        )
        if original_item["lifecycle"] == "qualified"
    )
    assert all(
        not item["qualification"]["qualified"] for item in updated["deployments"]
    )


def test_checked_in_deepseek_and_retriever_candidates_are_not_qualified() -> None:
    manifest = load_deployment_manifest(
        PROJECT_ROOT / "config/model-router/deployment-manifest.json",
        project_root=PROJECT_ROOT,
    )
    for alias in (
        "deepseek::deepseek-flash",
        "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
    ):
        deployment = manifest.for_route_alias(alias)
        assert deployment is not None
        assert deployment.lifecycle == "candidate"
        assert deployment.qualification.qualified is False


def test_relocated_retriever_requires_a_vector_compatibility_receipt() -> None:
    payload = json.loads(
        (PROJECT_ROOT / "config/model-router/deployment-manifest.json").read_text()
    )
    retriever = payload["deployments"][2]
    retriever["fingerprint"]["context_settings"]["route_base_url"] = (
        "https://embedding.example/v1"
    )
    retriever["fingerprint"]["endpoint_identity"] = "embedding.example:443"
    retriever["qualification"]["fingerprint_sha256"] = (
        DeploymentFingerprint.from_payload(retriever["fingerprint"]).sha256
    )
    from model_catalog_contracts.deployment_manifest import DeploymentManifest

    manifest = DeploymentManifest.from_payload(payload)
    with pytest.raises(promote.ReleasePromotionError, match="compatibility receipt"):
        promote._embedding_space_evidence(
            manifest=manifest,
            retriever_alias="dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
            source_revision="a" * 40,
            source_fingerprint="b" * 64,
            receipt_path=None,
        )


def test_checked_in_retriever_is_its_original_vector_runtime() -> None:
    manifest = load_deployment_manifest(
        PROJECT_ROOT / "config/model-router/deployment-manifest.json",
        project_root=PROJECT_ROOT,
    )
    evidence = promote._embedding_space_evidence(
        manifest=manifest,
        retriever_alias="dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
        source_revision="a" * 40,
        source_fingerprint="b" * 64,
        receipt_path=None,
    )
    assert evidence["mode"] == "origin"


def test_record_conformance_writes_a_deterministic_receipt(
    tmp_path: Path, monkeypatch
) -> None:
    source_revision = "a" * 40
    source_fingerprint = "b" * 64
    monkeypatch.setattr(
        conformance,
        "_git",
        lambda _root, *args: source_revision if args[0] == "rev-parse" else "",
    )
    monkeypatch.setattr(
        conformance, "source_fingerprint", lambda _root: source_fingerprint
    )

    receipt = conformance.record_conformance(
        project_root=tmp_path,
        output_path=tmp_path / "receipt.json",
        run=lambda *args, **kwargs: subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="passed", stderr=""
        ),
        now=lambda: datetime(2026, 9, 7, tzinfo=UTC),
    )

    assert receipt["passed"] is True
    assert receipt["test_paths"] == list(REQUIRED_CONFORMANCE_TESTS)
    assert (
        canonical_sha256(
            {key: value for key, value in receipt.items() if key != "artifact_sha256"}
        )
        == receipt["artifact_sha256"]
    )


@pytest.mark.parametrize("require_compatibility", [False, True])
def test_prepare_release_builds_selected_route_evidence(
    tmp_path: Path, monkeypatch, require_compatibility: bool
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_payload = json.loads(
        (PROJECT_ROOT / "config/model-router/deployment-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    policy_hashes = {
        policy: manifest_payload["deployments"][0]["fingerprint"][
            f"{policy}_policy_sha256"
        ]
        for policy in ("prompt", "tool", "schema", "retrieval")
    }
    for deployment in manifest_payload["deployments"]:
        # This synthetic promotion fixture must use one policy cohort. The
        # checked-in manifest deliberately retains stale qualified entries.
        for policy, digest in policy_hashes.items():
            deployment["fingerprint"][f"{policy}_policy_sha256"] = digest
        deployment["qualification"]["fingerprint_sha256"] = (
            DeploymentFingerprint.from_payload(deployment["fingerprint"]).sha256
        )
        deployment["lifecycle"] = "qualified"
        deployment["qualification"]["qualified"] = True
        deployment["qualification"]["stale_round_count"] = 0
        for role_result in deployment["qualification"]["role_results"]:
            role_result["observed_rounds"] = 3
            role_result["consecutive_passing_rounds"] = 3
            role_result["qualified"] = True
    manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")
    manifest = load_deployment_manifest(manifest_path, project_root=tmp_path)
    bindings = {
        role: {
            "route_alias": deployment.route_aliases[0],
            "deployment_id": deployment.deployment_id,
            "fingerprint_sha256": deployment.fingerprint.sha256,
        }
        for role in ("conversation", "reviewer", "retriever")
        for deployment in manifest.deployments
        if role in deployment.roles and deployment.lifecycle == "qualified"
    }
    source_revision = "a" * 40
    source_fingerprint = "b" * 64
    proposal = {
        "run_id": "native-run",
        "source_revision": source_revision,
        "source_dirty": False,
        "source_fingerprint": source_fingerprint,
        "proposal_sha256": "c" * 64,
        "round_artifact_sha256s": ["d" * 64, "e" * 64, "f" * 64],
        "deployment_bindings": bindings,
        "agent_bundle": {
            "prompt_key": "reviewed_prompt",
            "persona_key": "reviewed_persona",
            "tool_names": ["search_memory"],
        },
    }
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
    (tmp_path / "provenance.json").write_text(
        json.dumps(
            {
                "canonical_case_keys_sha256": "0" * 64,
                "effective_config": {
                    "include_llama_compatibility": require_compatibility,
                    "llama_compatibility_model_key": "local_llama_server::qwen3527b",
                },
                "llama_compatibility": (
                    {
                        "passed": True,
                        "artifact_sha256": "1" * 64,
                        "deployment_snapshots": [
                            {
                                "role": "conversation",
                                "route_alias": "local_llama_server::qwen3527b",
                            }
                        ],
                    }
                    if require_compatibility
                    else None
                ),
            }
        ),
        encoding="utf-8",
    )
    receipt = {
        "schema_version": 1,
        "kind": "ade-agent-studio-conformance-receipt",
        "source_revision": source_revision,
        "source_dirty": False,
        "source_fingerprint": source_fingerprint,
        "passed": True,
        "test_paths": list(REQUIRED_CONFORMANCE_TESTS),
    }
    receipt["artifact_sha256"] = canonical_sha256(receipt)
    receipt_path = tmp_path / "conformance.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(
        promote,
        "review_promotion",
        lambda **_kwargs: SimpleNamespace(manifest_payload=manifest_payload),
    )
    monkeypatch.setattr(
        promote, "production_policy_hashes", lambda _root: policy_hashes
    )

    promoted_manifest, evidence = promote.prepare_release_promotion(
        qualification_proposal_path=proposal_path,
        conformance_receipt_path=receipt_path,
        manifest_path=manifest_path,
        project_root=tmp_path,
        reviewer="release-reviewer",
        reviewed_at=datetime(2026, 9, 7, tzinfo=UTC),
    )

    assert promoted_manifest == manifest_payload
    assert evidence["kind"] == "ade-agent-studio-release-evidence"
    assert evidence["schema_version"] == 4
    assert evidence["qualification"]["compatibility_checks"] == (
        [
            {
                "route_alias": "local_llama_server::qwen3527b",
                "passed": True,
                "artifact_sha256": "1" * 64,
            }
        ]
        if require_compatibility
        else []
    )
    assert "paired_parity" not in evidence
    assert "rollback_rehearsal" not in evidence


def test_apply_release_promotion_replaces_manifest_and_evidence(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    evidence_path = tmp_path / "evidence.json"
    manifest_path.write_text('{"old": true}\n', encoding="utf-8")
    evidence_path.write_text('{"old": true}\n', encoding="utf-8")

    promote.apply_release_promotion(
        manifest_path=manifest_path,
        evidence_path=evidence_path,
        manifest_payload={"manifest": "qualified"},
        evidence_payload={"decision": "approved"},
    )

    assert json.loads(manifest_path.read_text(encoding="utf-8")) == {
        "manifest": "qualified"
    }
    assert json.loads(evidence_path.read_text(encoding="utf-8")) == {
        "decision": "approved"
    }
