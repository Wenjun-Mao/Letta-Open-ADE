from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.review_agent_studio_cutover as cutover_review
from ade_api.features.agent_runtime_v3.release_evidence import (
    REQUIRED_CAPABILITY_EVIDENCE,
    REQUIRED_CONFORMANCE_TESTS,
    canonical_sha256,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_receipt(
    path: Path,
    *,
    kind: str,
    digest_field: str,
    source_revision: str = "a" * 40,
) -> None:
    material: dict[str, object] = {
        "schema_version": 1,
        "kind": kind,
        "source_revision": source_revision,
        "source_dirty": False,
        "source_fingerprint": "b" * 64,
    }
    if kind == "ade-agent-studio-conformance-receipt":
        material.update(
            {
                "passed": True,
                "test_paths": list(REQUIRED_CONFORMANCE_TESTS),
            }
        )
    else:
        material.update(
            {
                "legacy_revision": "c" * 40,
                "rehearsed_at": "2026-09-03T00:00:00+00:00",
                "rehearsed": True,
                "legacy_source_verified": True,
                "legacy_web_image_built": True,
                "legacy_web_smoke_passed": True,
                "legacy_health_passed": True,
                "native_state_preserved": True,
            }
        )
    _write_json(path, {**material, digest_field: canonical_sha256(material)})


def _parity_artifacts() -> tuple[dict[str, object], dict[str, object]]:
    digests = {
        "parity_spec_sha256": "1" * 64,
        "provenance_sha256": "2" * 64,
        "normalized_turns_sha256": "3" * 64,
        "comparison_sha256": "4" * 64,
        "summary_sha256": "5" * 64,
        "evidence_sha256": "6" * 64,
    }
    detail: dict[str, object] = {
        "run_id": "test-center-run",
        "passed": True,
        "inputs_comparable": True,
        "cleanup_complete": True,
        "rounds_requested": 3,
        "rounds_completed": 3,
        "rounds_passed": 3,
        "artifact_digests": digests,
        "provenance": {
            "source_revision": "a" * 40,
            "source_dirty": False,
            "source_fingerprint": "b" * 64,
        },
    }
    spec = {
        "shared_product_contract": {
            "native_product_api": "/api/v3/agent-studio/sessions"
        }
    }
    return detail, spec


def _inputs(tmp_path: Path) -> dict[str, Path]:
    qualification_root = tmp_path / "qualification"
    proposal_path = qualification_root / "promotion-proposal.json"
    _write_json(
        proposal_path,
        {
            "run_id": "qualification-run",
            "source_revision": "d" * 40,
            "proposal_sha256": "e" * 64,
            "round_artifact_sha256s": ["7" * 64, "8" * 64, "9" * 64],
        },
    )
    _write_json(
        qualification_root / "provenance.json",
        {
            "canonical_case_keys_sha256": "f" * 64,
            "llama_compatibility": {
                "passed": True,
                "artifact_sha256": "0" * 64,
            },
        },
    )
    conformance_path = tmp_path / "conformance.json"
    rollback_path = tmp_path / "rollback.json"
    _write_receipt(
        conformance_path,
        kind="ade-agent-studio-conformance-receipt",
        digest_field="artifact_sha256",
    )
    _write_receipt(
        rollback_path,
        kind="ade-agent-studio-rollback-rehearsal",
        digest_field="receipt_sha256",
    )
    parity_root = tmp_path / "parity-test-center-run"
    parity_root.mkdir()
    return {
        "qualification_proposal_path": proposal_path,
        "parity_root": parity_root,
        "conformance_receipt_path": conformance_path,
        "rollback_receipt_path": rollback_path,
        "manifest_path": PROJECT_ROOT / "config/model-router/deployment-manifest.json",
        "project_root": PROJECT_ROOT,
    }


def test_cutover_review_composes_one_content_addressed_release_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cutover_review, "review_promotion", lambda **_kwargs: None)
    monkeypatch.setattr(
        cutover_review, "_read_parity", lambda _root: _parity_artifacts()
    )

    payload = cutover_review.review_cutover(
        **_inputs(tmp_path),
        reviewer="release-reviewer",
    )

    assert payload["decision"] == "approved"
    assert payload["conformance"] == {
        "passed": True,
        "receipt_sha256": payload["capability_evidence"]["cancellation"][
            "artifact_sha256"
        ],
        "test_paths": list(REQUIRED_CONFORMANCE_TESTS),
    }
    assert payload["rollback_rehearsal"]["legacy_source_verified"] is True
    assert payload["rollback_rehearsal"]["legacy_web_smoke_passed"] is True
    assert set(payload["capability_evidence"]) == set(REQUIRED_CAPABILITY_EVIDENCE)
    assert payload["evidence_sha256"] == canonical_sha256(
        {key: value for key, value in payload.items() if key != "evidence_sha256"}
    )


def test_cutover_review_rejects_receipts_from_a_different_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _inputs(tmp_path)
    _write_receipt(
        paths["conformance_receipt_path"],
        kind="ade-agent-studio-conformance-receipt",
        digest_field="artifact_sha256",
        source_revision="0" * 40,
    )
    monkeypatch.setattr(cutover_review, "review_promotion", lambda **_kwargs: None)
    monkeypatch.setattr(
        cutover_review, "_read_parity", lambda _root: _parity_artifacts()
    )

    with pytest.raises(cutover_review.CutoverReviewError, match="different source"):
        cutover_review.review_cutover(
            **paths,
            reviewer="release-reviewer",
        )
