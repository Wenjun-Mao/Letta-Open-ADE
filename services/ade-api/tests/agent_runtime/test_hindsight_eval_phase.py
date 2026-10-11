import json

import pytest

from ade_api.features.agent_runtime.hindsight_eval_contracts import EvaluationError
from ade_api.features.agent_runtime.hindsight_eval_phase import annotate


def test_phase_annotations_are_durable_unique_and_atomic(monkeypatch, tmp_path):
    target = tmp_path / "phase.json"
    monkeypatch.setenv("ADE_EVAL_PHASE_FILE", str(target))
    annotate("recall", "q1:hindsight")
    first = json.loads(target.read_text())
    annotate("character", "q1:character")
    second = json.loads(target.read_text())
    assert first["phase"] == "recall"
    assert second["phase"] == "character"
    assert first["correlation_id"] == "q1:hindsight"
    assert first["operation_id"] != second["operation_id"]
    intents = list(tmp_path.glob("phase-*.intent.json"))
    assert len(intents) == 2
    assert all(json.loads(item.read_text()) for item in intents)


def test_phase_write_failure_is_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("ADE_EVAL_PHASE_FILE", str(tmp_path / "missing" / "phase.json"))
    monkeypatch.setattr("os.fsync", lambda _fd: (_ for _ in ()).throw(OSError()))
    with pytest.raises(EvaluationError, match="phase_capture_failed"):
        annotate("recall", "q1:hindsight")
