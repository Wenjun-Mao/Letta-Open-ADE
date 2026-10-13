"""Exercise the documented entrypoint without live adapters or hidden services."""

import json
import subprocess
import sys

import pytest

from .__main__ import main
from .models import Capture, Observation, Review
from .offline import scripted_observation, scripted_runtime
from .records import model_from_json, read_json, seal, write_new
from .reviews import record_review, review_template
from .runs import prepare_run, record_capture, start_attempt


def invoke(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["assessment", *map(str, args)])
    return main()


def test_module_cli_rehearsal(tmp_path):
    output = tmp_path / "cli-rehearsal"
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "workflows.evals.hindsight_integration",
            "dry-run",
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(process.stdout)
    assert result["mode"] == "offline_scripted" and result["planned_attempts"] == 24
    assert (output / "report" / "report.md").exists()


def test_blank_review_schema_and_explicit_live_binding(monkeypatch, tmp_path, capsys):
    assert invoke(monkeypatch, "schema", "observation") == 0
    assert "requests" in json.loads(capsys.readouterr().out)["properties"]
    assert (
        invoke(
            monkeypatch,
            "prepare",
            "--out",
            tmp_path / "live",
            "--run-id",
            "test",
            "--mode",
            "live_capture",
        )
        == 2
    )
    assert not (tmp_path / "live").exists()


def test_cli_full_capture_and_review_path(monkeypatch, tmp_path, capsys):
    root = tmp_path / "run"
    assert (
        invoke(
            monkeypatch,
            "prepare",
            "--out",
            root,
            "--run-id",
            "test",
            "--case",
            "q01-relevant",
        )
        == 0
    )
    assert (
        invoke(
            monkeypatch,
            "actor-input",
            "--run",
            root,
            "--case",
            "q01-relevant",
            "--out",
            tmp_path / "actor.json",
        )
        == 0
    )
    assert "rubric" not in read_json(tmp_path / "actor.json")
    assert (
        invoke(
            monkeypatch,
            "start",
            "--run",
            root,
            "--case",
            "q01-relevant",
            "--repeat",
            "1",
        )
        == 0
    )
    path = root / "attempts" / "q01-relevant-r001"
    write_new(
        tmp_path / "observation.json", scripted_observation(path, "Synthetic response")
    )
    assert (
        invoke(
            monkeypatch,
            "capture",
            "--attempt",
            path,
            "--input",
            tmp_path / "observation.json",
        )
        == 0
    )
    assert (
        invoke(
            monkeypatch,
            "review-template",
            "--attempt",
            path,
            "--out",
            tmp_path / "template.json",
        )
        == 0
    )
    review = read_json(tmp_path / "template.json")
    assert review["judgments"]["grounding"]["result"] is None
    capsys.readouterr()
    assert (
        invoke(
            monkeypatch,
            "review",
            "--attempt",
            path,
            "--input",
            tmp_path / "template.json",
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["error"] == "Invalid evidence schema"
    review["reviewer"] = "test-human"
    for judgment in review["judgments"].values():
        judgment.update(
            result="cannot_assess",
            quote="Synthetic response",
            rationale="Not an empirical observation.",
        )
    write_new(tmp_path / "review.json", review)
    assert (
        invoke(
            monkeypatch,
            "review",
            "--attempt",
            path,
            "--input",
            tmp_path / "review.json",
        )
        == 0
    )
    assert (
        invoke(monkeypatch, "report", "--run", root, "--out", tmp_path / "report") == 0
    )


def test_validation_errors_do_not_print_input_values(monkeypatch, tmp_path, capsys):
    secret = "never-print-this-value"
    write_new(tmp_path / "input.json", {"mode": secret})
    assert (
        invoke(
            monkeypatch,
            "capture",
            "--attempt",
            tmp_path,
            "--input",
            tmp_path / "input.json",
        )
        == 2
    )
    assert secret not in capsys.readouterr().out


def test_failed_capture_exit_is_nonzero_and_artifact_kept(monkeypatch, tmp_path):
    root = tmp_path / "run"
    prepare_run(
        root,
        run_id="failure",
        mode="offline_scripted",
        runtime=scripted_runtime(),
        case_ids=["q01-relevant"],
    )
    path = start_attempt(root, "q01-relevant", 1)
    write_new(
        tmp_path / "failed.json",
        Observation(
            mode="offline_scripted",
            status="blocked",
            stage="setup",
            error="Scripted block",
            limitations=["Synthetic failure; no request exists."],
        ),
    )
    assert (
        invoke(
            monkeypatch,
            "capture",
            "--attempt",
            path,
            "--input",
            tmp_path / "failed.json",
        )
        == 1
    )
    assert (path / "capture.json").exists()


def test_scripted_review_cannot_qualify_live_capture(tmp_path):
    root = tmp_path / "run"
    runtime = scripted_runtime()
    runtime.memory_implementation = "hindsight"
    prepare_run(
        root,
        run_id="live-contract-test",
        mode="live_capture",
        runtime=runtime,
        case_ids=["q01-relevant"],
    )
    path = start_attempt(root, "q01-relevant", 1)
    record_capture(
        path,
        Observation(
            mode="live_capture",
            status="blocked",
            stage="setup",
            error="Synthetic test only; no real runtime",
            limitations=["No live request was made by this test."],
        ),
    )
    review = review_template(path)
    review.update(kind="scripted_example", reviewer="test")
    for judgment in review["judgments"].values():
        judgment.update(result="cannot_assess", rationale="No response")
    with pytest.raises(ValueError, match="Scripted judgments"):
        record_review(path, model_from_json(Review, review))


def test_read_rejects_mode_changed_after_capture(tmp_path):
    from .runs import load_capture

    root = tmp_path / "run"
    prepare_run(
        root,
        run_id="test",
        mode="offline_scripted",
        runtime=scripted_runtime(),
        case_ids=["q01-relevant"],
    )
    path = start_attempt(root, "q01-relevant", 1)
    record_capture(path, scripted_observation(path, "Synthetic"))
    raw = read_json(path / "capture.json")
    capture = model_from_json(Capture, raw["payload"])
    capture.observation.mode = "live_capture"
    (path / "capture.json").write_text(json.dumps(seal("assessment-capture", capture)))
    with pytest.raises(ValueError, match="evidence mode"):
        load_capture(path)
