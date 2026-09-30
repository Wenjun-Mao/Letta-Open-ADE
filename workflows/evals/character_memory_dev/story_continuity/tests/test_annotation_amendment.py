"""Explicit evaluator ownership changes cannot rebind the native baseline."""

from copy import deepcopy

import pytest

from ..annotation_amendment import (
    CONTRACT,
    PREFIX,
    validate_continuation,
    validate_record,
)
from ..native_artifacts import annotate, annotation_for, read, write_once
from .test_native_sequence import human, origin


def preparations():
    old = {
        "source_revision": "old",
        "source_fingerprint": "oldhash",
        "governed_source_fingerprint_v2": "runtime",
        "fixture_sha256": "prompts",
        "source_files": {PREFIX + "native_artifacts.py": "old", "runtime.py": "fixed"},
    }
    new = deepcopy(old)
    new.update(source_revision="new", source_fingerprint="newhash")
    new["source_files"][PREFIX + "native_artifacts.py"] = "new"
    new["source_files"][PREFIX + "annotation_amendment.py"] = "new"
    return old, new


def test_annotation_only_source_change_is_explicitly_bound():
    old, new = preparations()
    validate_continuation(old, new)
    record = {
        "contract": CONTRACT,
        "reviewer_kind": "agent",
        "effective_before_turn": 2,
        "original_preparation_sha256": "receipt",
        "continued_preparation": new,
        "user_approval": "approved",
    }
    validate_record(record, old, new, "receipt")
    with pytest.raises(ValueError, match="stale"):
        validate_record(record, old, new, "different-receipt")


@pytest.mark.parametrize(
    "change", ["runtime", "fixture", "validator", "delete", "newer_commit"]
)
def test_non_annotation_drift_is_rejected(change):
    old, new = preparations()
    if change == "runtime":
        new["governed_source_fingerprint_v2"] = "changed"
    elif change == "fixture":
        new["fixture_sha256"] = "changed"
    elif change == "validator":
        new["source_files"][PREFIX + "evidence.py"] = "changed"
    elif change == "delete":
        del new["source_files"]["runtime.py"]
    else:
        new["source_revision"] = old["source_revision"]
    with pytest.raises(ValueError):
        validate_continuation(old, new)


def test_agent_annotation_is_labeled_and_never_accepted_as_human(tmp_path):
    write_once(tmp_path / "turn-01.json", origin())
    write_once(
        tmp_path / "annotation-amendment.json",
        {"contract": CONTRACT, "reviewer_kind": "agent"},
    )
    with pytest.raises(ValueError, match="mislabel"):
        annotate(tmp_path, 1, human())
    supplied = {**human(), "reviewer_kind": "agent", "reviewer": "Codex scripted test"}
    annotate(tmp_path, 1, supplied)
    result = annotation_for(tmp_path, 1, read(tmp_path / "turn-01.json"))
    assert result["reviewer_kind"] == "agent"
