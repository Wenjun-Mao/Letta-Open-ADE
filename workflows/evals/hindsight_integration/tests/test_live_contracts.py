"""Source declarations and sidecar boundaries, not real model qualification."""

import asyncio
import json

import pytest

from ..live_artifacts import reference, referenced_file
from ..live_bindings import declared_runtime
from ..live_capture_contracts import FileReference
from ..offline import scripted_runtime
from ..records import read_json
from ..runs import prepare_run
from ..live_runner import capture_traffic


def test_staged_evaluator_revision_is_explicit_not_a_missing_git_fallback(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "workflows.evals.hindsight_integration.runs.subprocess.check_output",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("Staged source has no Git")
        ),
    )
    result = prepare_run(
        tmp_path / "run",
        run_id="staged",
        mode="offline_scripted",
        runtime=scripted_runtime(),
        case_ids=["q01-relevant"],
        evaluator_revision="a" * 40,
    )
    assert result.evaluator_revision == "a" * 40
    assert (
        read_json(tmp_path / "run/run.json")["payload"]["evaluator_revision"]
        == "a" * 40
    )
    with pytest.raises(ValueError, match="exact evaluator"):
        prepare_run(
            tmp_path / "invalid",
            run_id="invalid",
            mode="offline_scripted",
            runtime=scripted_runtime(),
            evaluator_revision="unknown",
        )


def test_live_declarations_keep_memory_character_and_compaction_identities_separate():
    runtime, binding = declared_runtime("a" * 40)
    assert runtime.memory_implementation == "hindsight"
    assert (
        runtime.context_compaction_identity_sha256 == runtime.character_identity_sha256
    )
    assert (
        runtime.memory_config_sha256 == binding["memory"]["bank_configuration_sha256"]
    )
    assert binding["embedding"]["dimensions"] == 1024
    assert "rubric" not in json.dumps(binding)
    assert runtime.character_settings.get("controlled") is None


def test_sidecar_files_are_physical_hash_bound_and_cannot_escape_the_attempt(tmp_path):
    root = tmp_path / "attempt"
    root.mkdir()
    path = root / "body.json"
    path.write_text('{"actual":true}')
    ref = reference(root, path)
    assert referenced_file(root, ref) == path
    with pytest.raises(ValueError, match="unsafe_sidecar"):
        referenced_file(
            root, FileReference(path="../outside.json", file_sha256=ref.file_sha256)
        )
    path.write_text('{"actual":false}')
    with pytest.raises(ValueError, match="file_hash"):
        referenced_file(root, ref)


@pytest.mark.parametrize("failed", [False, True])
def test_traffic_snapshot_preserves_pending_outcomes_and_collection_failures(
    tmp_path, monkeypatch, failed
):
    async def records(router):
        if failed:
            raise ValueError("observation_unavailable")
        return [{"request": {"request_id": "in-flight"}, "outcome": None}]

    monkeypatch.setattr(
        "workflows.evals.hindsight_integration.live_runner.wire_records", records
    )
    asyncio.run(capture_traffic(tmp_path, "http://router.invalid", "private-key"))
    if failed:
        assert read_json(tmp_path / "traffic/failure.json")["error"] == (
            "ValueError:observation_unavailable"
        )
        assert not (tmp_path / "traffic/snapshot.json").exists()
    else:
        value = read_json(tmp_path / "traffic/snapshot.json")["payload"]
        assert value["missing_outcome_request_ids"] == ["in-flight"]
        assert "Not a quiescent closeout" in value["limitation"]
