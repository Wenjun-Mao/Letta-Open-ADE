"""Portable mechanics tests; none of these assert real model quality."""

import json
import shutil
import socket
from datetime import timedelta

import pytest
from pydantic import ValidationError

from .casebook import FIXTURES, actor_material, load_suite
from .models import LENSES, Observation, Review
from .offline import dry_run, scripted_observation, scripted_runtime
from .records import model_from_json, read_json
from .report import build_report, write_report
from .reviews import load_reviews, record_review, review_template
from .runs import load_capture, prepare_run, record_capture, start_attempt


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Assessment mechanics must not use the network")

    monkeypatch.setattr(socket, "create_connection", fail)
    monkeypatch.setattr(socket.socket, "connect", fail)


@pytest.fixture
def run(tmp_path):
    root = tmp_path / "run"
    prepare_run(
        root,
        run_id="test-run",
        mode="offline_scripted",
        runtime=scripted_runtime(),
        repeats=2,
    )
    return root


def captured(run, case_id="q01-relevant", repeat=1):
    path = start_attempt(run, case_id, repeat)
    observation = scripted_observation(path, "A scripted reply, not model evidence.")
    assert record_capture(path, observation) == []
    return path


def filled_review(path, *, result="meets"):
    template = review_template(path)
    template.update(
        reviewer="test-human-reviewer",
        judgments={
            lens: {
                "result": result,
                "quote": "scripted reply",
                "rationale": "Synthetic test judgment.",
            }
            for lens in LENSES
        },
    )
    return model_from_json(Review, template)


def test_frozen_casebook_and_actor_separation():
    suite = load_suite()
    assert len(suite["cases"]) == 12
    assert len(suite["calibration"]) == 15
    for case in suite["cases"].values():
        actor = actor_material(case)
        assert "rubric" not in actor and "judgments" not in actor
        assert actor["prompt"] == case.prompt
    assert (
        suite["cases"]["q02-correction"].history != suite["cases"]["q02-change"].history
    )


def test_fixture_drift_fails(tmp_path):
    copy = tmp_path / "fixtures"
    shutil.copytree(FIXTURES, copy)
    with (copy / "q01.json").open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="Frozen fixture"):
        load_suite(copy)


@pytest.mark.parametrize("content", ['{"a":1,"a":2}', '{"a":NaN}', "[]"])
def test_ambiguous_json_rejected(tmp_path, content):
    path = tmp_path / "invalid.json"
    path.write_text(content)
    with pytest.raises(ValueError):
        read_json(path)


def test_create_only_records_and_planned_slots(run):
    path = captured(run)
    with pytest.raises(FileExistsError):
        start_attempt(run, "q01-relevant", 1)
    with pytest.raises(FileExistsError):
        record_capture(path, scripted_observation(path, "A replacement is forbidden."))
    with pytest.raises(ValueError):
        start_attempt(run, "q01-relevant", 3)
    with pytest.raises(ValueError):
        start_attempt(run, "q01-unknown", 1)


def test_capture_hash_and_attempt_binding(run):
    first = captured(run)
    second = start_attempt(run, "q01-relevant", 2)
    shutil.copyfile(first / "capture.json", second / "capture.json")
    with pytest.raises(ValueError, match="different attempt"):
        load_capture(second)
    value = read_json(first / "capture.json")
    value["payload"]["observation"]["reply"] = "Edited after capture"
    (first / "capture.json").write_text(json.dumps(value))
    with pytest.raises(ValueError, match="Changed/corrupt"):
        load_capture(first)


@pytest.mark.parametrize("case_id", list(load_suite()["cases"]))
def test_scripted_shape_covers_every_case(run, case_id):
    captured(run, case_id)


@pytest.mark.parametrize(
    ("mutation", "issue"),
    [
        ("scope", "relationship_subject_mismatch"),
        ("leak", "cross_relationship_recall"),
        ("runtime", "runtime_binding_mismatch_or_missing"),
        ("prompt", "current_prompt_or_local_history_mismatch"),
        ("persona", "bound_persona_or_prompt_not_delivered"),
        ("timestamp", "generation_request_outside_attempt"),
        ("source", "source_fixture_content_mismatch"),
        ("source_id", "source_attribution_mismatch"),
        ("uncommitted", "source_message_not_accepted_or_committed"),
        ("freshness", "probe_is_not_a_fresh_conversation"),
        ("retention", "source_retention_not_complete"),
        ("reply", "missing_committed_reply"),
        ("input", "incomplete_generation_input"),
        ("provenance", "history_provenance_mismatch_or_missing"),
    ],
)
def test_bad_evidence_is_kept_but_not_qualified(run, mutation, issue):
    path = start_attempt(run, "q03-shared-joke", 1)
    observation = scripted_observation(path, "A scripted reply, not model evidence.")
    match mutation:
        case "scope":
            observation.target_scope = observation.target_scope.model_copy(
                update={"subject": "someone-else"}
            )
        case "leak":
            observation.recalled_scopes = [
                observation.target_scope.model_copy(update={"subject": "someone-else"})
            ]
        case "runtime":
            observation.observed_runtime.prompt_version = "different-version"
        case "prompt":
            observation.requests[0].body["messages"][-1]["content"] = (
                "A different question"
            )
        case "persona":
            observation.requests[0].body["messages"][0]["content"] = "Different persona"
        case "timestamp":
            observation.requests[0].sent_at += timedelta(days=1)
        case "source":
            observation.source_messages[0].content = "Not the frozen source"
        case "source_id":
            observation.source_messages[0].conversation_id = "other-conversation"
        case "uncommitted":
            observation.source_messages[1].status = "uncommitted"
        case "freshness":
            observation.probe_conversation_id = observation.source_conversation_id
        case "retention":
            observation.retention = "pending"
        case "reply":
            observation.reply_committed = False
        case "input":
            observation.input_complete = False
        case "provenance":
            observation.history_provenance = "product_dialogue"
    assert issue in record_capture(path, observation)
    assert (path / "capture.json").exists()
    with pytest.raises(ValueError, match="limitations"):
        record_review(path, filled_review(path))
    record_review(path, filled_review(path, result="cannot_assess"))
    report = build_report(run)
    row = next(item for item in report["attempts"] if item["attempt"] == path.name)
    assert not row["assessable"] and issue in row["mechanical_issues"]
    assert report["families"]["Q03"]["lenses"]["grounding"]["denominator"] == 0


def test_sensitive_field_rejection_keeps_started_slot(run):
    path = start_attempt(run, "q01-relevant", 1)
    observation = scripted_observation(path, "A scripted reply")
    observation.requests[0].body["api_key"] = "do-not-store"
    with pytest.raises(ValueError, match="Credential"):
        record_capture(path, observation)
    assert not (path / "capture.json").exists()
    assert build_report(run)["attempts"][0]["state"] == "incomplete"


@pytest.mark.parametrize(
    "mutation", ["quote", "capture", "lens", "rating", "blank", "unknown", "type"]
)
def test_review_schema_and_evidence_rejections(run, mutation):
    path = captured(run)
    review = filled_review(path).model_dump(mode="json")
    match mutation:
        case "quote":
            review["judgments"]["grounding"]["quote"] = "not in the response"
        case "capture":
            review["capture_sha256"] = "0" * 64
        case "lens":
            del review["judgments"]["grounding"]
        case "rating":
            review["judgments"]["grounding"]["result"] = "perfect"
        case "blank":
            review["reviewer"] = " "
        case "unknown":
            review["overall_score"] = 100
        case "type":
            review["revision"] = "1"
    with pytest.raises((ValidationError, ValueError)):
        record_review(path, model_from_json(Review, review))


def test_review_corrections_are_linked_and_visible(run):
    path = captured(run)
    first = filled_review(path)
    record_review(path, first)
    original_bytes = (path / "review-0001.json").read_bytes()
    correction = review_template(path)
    correction.update(
        reviewer="second-human",
        change_reason="Corrected an overconfident interpretation.",
        judgments={
            lens: {**item.model_dump(), "result": "partly_meets"}
            for lens, item in first.judgments.items()
        },
    )
    record_review(path, model_from_json(Review, correction))
    assert len(load_reviews(path)) == 2
    assert (path / "review-0001.json").read_bytes() == original_bytes
    row = build_report(run)["attempts"][0]
    assert len(row["review_history"]) == 2
    assert row["judgments"]["grounding"]["result"] == "partly_meets"
    (path / "review-0001.json").unlink()
    with pytest.raises(ValueError, match="Non-contiguous"):
        load_reviews(path)


def test_offline_rehearsal_keeps_all_denominators(tmp_path):
    root = tmp_path / "rehearsal"
    report = dry_run(root)
    assert len(report["attempts"]) == 24
    states = [row["state"] for row in report["attempts"]]
    assert states.count("not_run") == 18
    assert states.count("incomplete") == 1
    assert states.count("captured_unreviewed") == 1
    assert states.count("reviewed") == 4
    q01 = report["families"]["Q01"]
    assert q01["independent_cases"] == 2 and q01["planned_attempts"] == 4
    assert q01["lenses"]["conversational_judgment"]["result_counts"]["fails"] == 1
    assert report["repeat_consistency"]["q01-relevant"]["conversational_judgment"] == [
        "meets",
        "fails",
    ]
    assert "overall_score" not in json.dumps(report)
    assert (
        "SCRIPTED OFFLINE MECHANICS ONLY" in (root / "report" / "report.md").read_text()
    )
    assert (
        "| Q01 | conversational_judgment | 1 | 0 | 1 | 0 | 2 |"
        in (root / "report" / "report.md").read_text()
    )
    assert build_report(root) == report
    failure = next(
        row for row in report["attempts"] if row["attempt"] == "q05-listen-r001"
    )
    assert (
        failure["stage"] == "recall"
        and failure["error"] == "Deliberate scripted lookup failure"
    )
    with pytest.raises(FileExistsError):
        write_report(root, root / "report")


def test_scope_reuse_excludes_both_attempts(run):
    first = captured(run)
    _, _, _, old, _, _ = load_capture(first)
    path = start_attempt(run, "q01-relevant", 2)
    observation = scripted_observation(path, "A scripted reply")
    observation.source_scope = old.observation.source_scope
    observation.target_scope = old.observation.target_scope
    observation.recalled_scopes = [observation.target_scope]
    for message in observation.source_messages:
        message.scope = observation.source_scope
    record_capture(path, observation)
    record_review(first, filled_review(first))
    report = build_report(run)
    for row in report["attempts"][:2]:
        assert "relationship_scope_reused_between_attempts" in row["mechanical_issues"]
        assert not row["assessable"]


def test_unplanned_artifacts_fail_closed(run):
    (run / "attempts" / "extra").mkdir(parents=True)
    with pytest.raises(ValueError, match="Unexpected attempt"):
        build_report(run)


def test_live_and_scripted_modes_cannot_mix(run):
    path = start_attempt(run, "q01-relevant", 1)
    observation = scripted_observation(path, "A scripted reply")
    observation.mode = "live_capture"
    with pytest.raises(ValueError, match="mixed"):
        record_capture(path, observation)


def test_incomplete_observation_requires_reason():
    with pytest.raises(ValidationError):
        Observation(mode="offline_scripted", status="failed", stage="setup")
