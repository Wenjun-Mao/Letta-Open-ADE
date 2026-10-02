"""Durable capture, clean-source gate and bounded inspection."""

import json

import pytest

from .. import receipts, runner
from .test_runner import Scripted


def test_write_once_never_overwrites(tmp_path):
    path = tmp_path / "intent.json"
    receipts.write_once(path, {"attempt": 1})
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        receipts.write_once(path, {"attempt": 2})
    assert path.read_bytes() == original


def test_clean_source_gate(monkeypatch):
    monkeypatch.setattr(
        receipts.subprocess, "check_output", lambda *a, **kw: b" M dirty"
    )
    with pytest.raises(ValueError, match="Clean committed"):
        receipts.source_receipt()


def test_audit_uses_actual_arm_reply_only(launch):
    directory, execute, _ = launch
    execute(Scripted())
    seen = []

    def validate(arm, reply, payload):
        seen.append((arm, reply, payload))

    result = runner.audit(directory, validate)
    assert len(result["assessments"]) == len(seen) == 3
    assert [r[0] for r in seen] == ["literal-four", "repaired-four", "whole-pool"]
    assert all(r[1:] == ("visible", {"decisions": []}) for r in seen)


def test_raw_capture_drift_fails_before_resume(launch):
    directory, execute, _ = launch
    script = Scripted()
    execute(script)
    path = directory / "literal-four.generation.raw.json"
    capture = receipts.read(path)
    capture["status"] = 500
    path.write_text(json.dumps(capture))
    with pytest.raises(ValueError, match="raw capture drift"):
        execute(script)
    assert len(script.sent) == 6


def test_configuration_attestation_mismatch_sends_nothing(launch):
    _, execute, origin = launch
    script = Scripted()
    with pytest.raises(ValueError, match="configuration"):
        execute(script, lambda: {**origin, "head": "different"})
    assert not script.sent and script.catalogs == 0


def test_fixed_directory_rejects_alternative_or_symlink(tmp_path, monkeypatch):
    monkeypatch.setattr(receipts, "OUTPUTS", tmp_path)
    with pytest.raises(ValueError):
        receipts.require_private(tmp_path / "reroll")
    (tmp_path / "d04-comparison").symlink_to(tmp_path / "other")
    with pytest.raises(ValueError):
        receipts.require_private(tmp_path / "d04-comparison")


def test_source_preflight_exception_records_terminal_stop(launch):
    directory, execute, origin = launch
    count = 0

    def source():
        nonlocal count
        count += 1
        if count == 3:
            raise ValueError("dirty source")
        return origin

    scripted = Scripted()
    with pytest.raises(ValueError, match="dirty source"):
        execute(scripted, source)
    assert len(scripted.sent) == 1
    assert (
        receipts.read(directory / "stop.json")["reason"] == "source_preflight_failure"
    )
    with pytest.raises(ValueError, match="stop"):
        execute(scripted)
