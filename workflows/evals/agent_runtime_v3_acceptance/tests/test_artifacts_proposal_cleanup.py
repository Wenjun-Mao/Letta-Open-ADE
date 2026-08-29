from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from workflows.evals.agent_runtime_v3_acceptance.artifacts import RoundArtifactWriter
from workflows.evals.agent_runtime_v3_acceptance.cleanup import (
    CleanupError,
    CleanupScope,
    ScopedPostgresCleanup,
    _psycopg_params,
    _psycopg_url,
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
        source_revision="c" * 40,
        source_dirty=False,
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
            "rounds": 3,
            "timeout_seconds": 180,
            "retry_count": 0,
        },
    )

    assert proposal is not None
    assert proposal.payload["apply_owner"] == "coordinator"
    assert set(proposal.payload["deployment_bindings"]) == {
        "conversation",
        "reviewer",
        "retriever",
    }
    assert proposal.path.is_file()
    assert not (tmp_path / "deployment-manifest.json").exists()


def test_cleanup_refuses_unsupported_database_or_unscoped_queries(
    tmp_path: Path,
) -> None:
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
        execute=execute,
    )

    manifest = cleaner.cleanup(scope)
    assert manifest.path.is_file()
    assert manifest.payload["scope"]["run_id"] == scope.run_id
    assert executed
    assert all("WHERE" in sql for sql, _params in executed)
    assert all(params for _sql, params in executed)
    sql_order = [sql.rsplit("\n", maxsplit=1)[-1] for sql, _params in executed]
    assert next(
        index for index, sql in enumerate(sql_order) if "UPDATE ade.memory_facts" in sql
    ) < next(index for index, sql in enumerate(sql_order) if "memory_revisions" in sql)
    assert next(
        index
        for index, sql in enumerate(sql_order)
        if "memory_revision_sources" in sql
    ) < next(index for index, sql in enumerate(sql_order) if "ade.messages" in sql)
    assert next(
        index for index, sql in enumerate(sql_order) if "memory_revisions" in sql
    ) < next(index for index, sql in enumerate(sql_order) if "ade.runs" in sql)
    assert next(
        index for index, sql in enumerate(sql_order) if "ade.runs" in sql
    ) < next(index for index, sql in enumerate(sql_order) if "ade.conversations" in sql)
    assert (
        _psycopg_url("postgresql+psycopg://ade_app:secret@postgres:5432/ade")
        == "postgresql://ade_app:secret@postgres:5432/ade"
    )
    assert _psycopg_params((("a", "b"), ("c",))) == (["a", "b"], ["c"])

    with pytest.raises(CleanupError, match="PostgreSQL"):
        ScopedPostgresCleanup(
            database_url="sqlite:///unsafe.db",
            output_dir=tmp_path,
            execute=lambda _sql, _params: {},
        ).cleanup(scope)

    with pytest.raises(CleanupError, match="scope"):
        cleaner.cleanup(
            CleanupScope(run_id="", definition_keys=(), subject_external_keys=())
        )
