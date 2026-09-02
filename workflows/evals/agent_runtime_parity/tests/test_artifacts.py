from __future__ import annotations

import json

import pytest

from workflows.evals.agent_runtime_parity.artifacts import (
    ArtifactError,
    ArtifactWriter,
    verify_json_artifact,
)


def test_artifacts_are_content_addressed_and_immutable(tmp_path) -> None:
    writer = ArtifactWriter(tmp_path, "parity-test")
    artifact = writer.write_json("parity-spec", {"kind": "spec", "value": 1})
    turns = writer.write_jsonl("normalized-turns", [{"turn": 1}, {"turn": 2}])

    payload = json.loads(artifact.path.read_text(encoding="utf-8"))
    assert payload["artifact_sha256"] == artifact.sha256
    assert verify_json_artifact(artifact.path)
    assert len(turns.sha256) == 64
    with pytest.raises(ArtifactError, match="already exists"):
        writer.write_json("parity-spec", {"kind": "different"})


def test_json_artifact_verification_detects_mutation(tmp_path) -> None:
    writer = ArtifactWriter(tmp_path, "parity-mutation")
    artifact = writer.write_json("summary", {"pass": True})
    artifact.path.write_text(
        '{"artifact_sha256":"bad","pass":false}\n', encoding="utf-8"
    )

    assert not verify_json_artifact(artifact.path)
