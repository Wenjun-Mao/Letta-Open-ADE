from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from workflows.evals.agent_runtime_v3_acceptance.artifacts import RoundArtifactWriter
from workflows.evals.agent_runtime_v3_acceptance.cleanup import (
    CLEANUP_OWNER,
    CleanupError,
    CleanupScope,
    ScopedPostgresCleanup,
)
from workflows.evals.agent_runtime_v3_acceptance.proposal import (
    build_promotion_proposal,
)


def test_round_artifacts_are_atomic_and_content_addressed(tmp_path: Path) -> None:
    writer = RoundArtifactWriter(tmp_path, "run-a")
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
    rounds = tuple(
        SimpleNamespace(
            index=index,
            kind="primary",
            execution_mode="live-api",
            complete_matrix=True,
            passed=True,
            case_keys=("a", "b"),
            artifact_sha256=f"{'a' * 63}{index}",
            deployment_fingerprints={"conversation": "fingerprint-a"},
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
    )

    assert proposal is not None
    assert proposal.payload["apply_owner"] == "coordinator"
    assert proposal.path.is_file()
    assert not (tmp_path / "deployment-manifest.json").exists()


def test_cleanup_refuses_wrong_owner_or_unscoped_queries(tmp_path: Path) -> None:
    scope = CleanupScope(
        run_id="acceptance-20260829",
        definition_keys=("acceptance-20260829-agent",),
        subject_external_keys=("acceptance-20260829-subject",),
    )
    executed: list[tuple[str, tuple[tuple[str, ...], ...]]] = []

    def execute(sql: str, params: tuple[tuple[str, ...], ...]) -> dict[str, int]:
        executed.append((sql, params))
        return {"deleted": 1}

    cleaner = ScopedPostgresCleanup(
        database_url="postgresql://example",
        output_dir=tmp_path,
        cleanup_owner=CLEANUP_OWNER,
        execute=execute,
    )

    manifest = cleaner.cleanup(scope)
    assert manifest.path.is_file()
    assert manifest.payload["scope"]["run_id"] == scope.run_id
    assert executed
    assert all("WHERE" in sql for sql, _params in executed)
    assert all(params for _sql, params in executed)

    with pytest.raises(CleanupError, match="owner"):
        ScopedPostgresCleanup(
            database_url="postgresql://example",
            output_dir=tmp_path,
            cleanup_owner="not-the-owner",
            execute=lambda _sql, _params: {},
        ).cleanup(scope)

    with pytest.raises(CleanupError, match="scope"):
        cleaner.cleanup(
            CleanupScope(run_id="", definition_keys=(), subject_external_keys=())
        )
