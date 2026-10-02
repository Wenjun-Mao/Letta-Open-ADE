"""Stopped execution retains auditable evidence without replay authorization."""

import json

import pytest

from .. import receipts, runner
from .test_runner import Scripted, answer, raw


def snapshot(directory):
    return {p.name: p.read_bytes() for p in directory.glob("*.json")}


def audit_first_arm(directory, terminal):
    original = snapshot(directory)
    seen = []
    result = runner.audit(directory, lambda *args: seen.append(args))
    assert seen == [("literal-four", "first visible", {"decisions": []})]
    assert result["assessments"]["literal-four"].startswith(
        "schema_source_binding_valid"
    )
    assert result["assessments"]["repaired-four"] == "unrun_or_unusable"
    assert result["execution_state"] == terminal
    assert result["stages"]["repaired-four.generation"]["disposition"] == terminal
    assert result["stages"]["repaired-four.reviewer"]["disposition"] == "unrun"
    assert result["stages"]["whole-pool.generation"]["disposition"] == "unrun"
    assert snapshot(directory) == original
    return result


@pytest.mark.parametrize(
    "failure,terminal",
    [
        (TimeoutError("uncertain later dispatch"), "transport_stop"),
        (raw({"error": "routing"}, 404), "infrastructure_stop"),
        (raw({"error": "authentication"}, 401), "infrastructure_stop"),
    ],
)
def test_audit_captured_arm_after_later_failure_and_refuse_resume(
    launch, failure, terminal
):
    directory, execute, _ = launch
    script = Scripted([answer("first visible"), answer('{"decisions":[]}'), failure])
    execute(script)
    assert len(script.sent) == 3
    audit_first_arm(directory, terminal)
    with pytest.raises(ValueError, match="no continuation"):
        execute(script)
    assert len(script.sent) == 3 and script.catalogs == 1


@pytest.mark.parametrize(
    "interruption", ["dispatch", "raw_absent", "raw_partial", "outcome_absent"]
)
def test_audit_captured_arm_after_later_interruption_and_refuse_resume(
    launch, monkeypatch, interruption
):
    directory, execute, _ = launch
    script = Scripted(
        [
            answer("first visible"),
            answer('{"decisions":[]}'),
            KeyboardInterrupt()
            if interruption == "dispatch"
            else answer("second visible"),
        ]
    )
    original_write = runner.write_once

    def interrupted(path, value):
        raw_capture = path.name == "repaired-four.generation.raw.json"
        outcome_capture = path.name == "repaired-four.generation.outcome.json"
        if raw_capture and interruption in {"raw_absent", "raw_partial"}:
            if interruption == "raw_partial":
                path.write_text('{"status":')
            raise OSError("incomplete raw capture")
        if outcome_capture and interruption == "outcome_absent":
            raise OSError("interrupted before outcome creation")
        return original_write(path, value)

    monkeypatch.setattr(runner, "write_once", interrupted)
    with pytest.raises((KeyboardInterrupt, OSError)):
        execute(script)
    audit_first_arm(directory, "uncertain_consumed")
    with pytest.raises(ValueError, match="uncertain_consumed"):
        execute(script)
    assert len(script.sent) == 3 and script.catalogs == 1


@pytest.mark.parametrize(
    "tamper",
    [
        "prior_raw",
        "uncertain_intent",
        "post_stop_outcome",
        "post_stop_intent",
        "non_prefix",
    ],
)
def test_stopped_audit_rejects_tampered_or_out_of_order_evidence(launch, tamper):
    directory, execute, _ = launch
    script = Scripted(
        [answer("first visible"), answer('{"decisions":[]}'), KeyboardInterrupt()]
    )
    with pytest.raises(KeyboardInterrupt):
        execute(script)
    if tamper == "prior_raw":
        path = directory / "literal-four.generation.raw.json"
        receipt = receipts.read(path)
        receipt["status"] = 500
        path.write_text(json.dumps(receipt))
    elif tamper == "uncertain_intent":
        path = directory / "repaired-four.generation.intent.json"
        receipt = receipts.read(path)
        receipt["request"]["messages"][0]["content"] = "tampered"
        path.write_text(json.dumps(receipt))
    elif tamper.startswith("post_stop"):
        suffix = "outcome" if tamper.endswith("outcome") else "intent"
        (directory / f"whole-pool.generation.{suffix}.json").write_text("{}")
    else:
        for suffix in ("outcome", "intent", "raw"):
            (directory / f"literal-four.reviewer.{suffix}.json").unlink()
    seen = []
    with pytest.raises(ValueError):
        runner.audit(directory, lambda *args: seen.append(args))
    assert not seen
    with pytest.raises(ValueError):
        execute(script)
    assert len(script.sent) == 3 and script.catalogs == 1


def test_partial_complete_outcome_is_rejected_not_treated_as_missing(launch):
    directory, execute, _ = launch
    script = Scripted(
        [answer("first visible"), answer('{"decisions":[]}'), TimeoutError("later")]
    )
    execute(script)
    (directory / "repaired-four.generation.outcome.json").write_text(
        '{"classification":'
    )
    with pytest.raises(ValueError):
        runner.audit(directory, lambda *args: None)
    with pytest.raises(ValueError):
        execute(script)
    assert len(script.sent) == 3


@pytest.mark.parametrize(
    "failure", [TimeoutError("later"), raw({"error": "route"}, 404)]
)
def test_complete_stop_rejects_post_stop_outcome(launch, failure):
    directory, execute, _ = launch
    script = Scripted([answer("first visible"), answer('{"decisions":[]}'), failure])
    execute(script)
    (directory / "whole-pool.generation.outcome.json").write_text("{}")
    with pytest.raises(ValueError, match="post-stop"):
        runner.audit(directory, lambda *args: None)
    with pytest.raises(ValueError, match="post-stop"):
        execute(script)
    assert len(script.sent) == 3


def test_global_preflight_stop_preserves_audit_and_rejects_later_artifacts(launch):
    directory, execute, origin = launch
    count = 0

    def source():
        nonlocal count
        count += 1
        if count == 4:
            raise ValueError("source drift before second arm")
        return origin

    script = Scripted([answer("first visible"), answer('{"decisions":[]}')])
    with pytest.raises(ValueError, match="source drift"):
        execute(script, source)
    original = snapshot(directory)
    seen = []
    result = runner.audit(directory, lambda *args: seen.append(args))
    assert len(seen) == 1 and result["execution_state"] == "preflight_stop"
    assert result["stages"]["repaired-four.generation"]["disposition"] == "unrun"
    assert result["stop"]["reason"] == "source_preflight_failure"
    assert snapshot(directory) == original
    with pytest.raises(ValueError, match="stop"):
        execute(script)
    assert len(script.sent) == 2
    (directory / "whole-pool.generation.intent.json").write_text("{}")
    with pytest.raises(ValueError):
        runner.audit(directory, lambda *args: None)
