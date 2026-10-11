"""Offline fake-provider checks for the feature-owned CLI contract."""

import json
import stat
import pytest
from pydantic import ValidationError
from ade_api.features.agent_runtime import hindsight_evaluation as evaluation
from ade_api.features.agent_runtime.hindsight_eval_capture import EvaluationCapture
from ade_api.features.agent_runtime.hindsight_eval_contracts import (
    EvaluationError,
    RecallScope,
    fingerprint,
)
from ade_api.features.agent_runtime.hindsight_eval_recall import service_url
from .hindsight_eval_fakes import FakeProviders, inputs, memory, read, run


def test_three_arms_one_generation_frozen_inputs_and_actual_requests(
    monkeypatch, tmp_path
):
    fake = FakeProviders()
    result = run(monkeypatch, tmp_path, fake)
    assert result["status"] == "completed"
    assert len(fake.generations) == 3
    assert len(fake.recalls) == 1
    for arm, dispatched in zip(inputs().arms, fake.generations, strict=True):
        assert read(tmp_path, f"{arm}.request.json") == dispatched
        assert dispatched["model"] == inputs().model_key
        assert dispatched["messages"][1:] == [
            item.model_dump() for item in inputs().dialogue
        ]
        assert dispatched["messages"][0]["content"].startswith(inputs().persona)
        assert dispatched["max_tokens"] == inputs().max_output_tokens
        assert dispatched["stream"] is False
        assert "tools" not in dispatched and "tool_choice" not in dispatched
        receipt = read(tmp_path, f"{arm}.result.json")
        assert receipt["model_request_count"] == 1
        assert receipt["request_sha256"] == fingerprint(dispatched)
        assert receipt["usage"]["total_tokens"] == 133
        assert receipt["latency_seconds"] >= 0
    contents = "\n".join(path.read_text() for path in (tmp_path / "receipts").iterdir())
    assert "hindsight-secret" not in contents and "router-secret" not in contents
    assert "PRIVATE-REASONING" not in contents
    assert stat.S_IMODE((tmp_path / "receipts").stat().st_mode) == 0o700
    assert all(
        stat.S_IMODE(path.stat().st_mode) == 0o600
        for path in (tmp_path / "receipts").iterdir()
    )
    context = read(tmp_path, "hindsight.context.json")
    assert context["memories"][0]["metadata"]["speaker"] == "assistant"
    assert context["memories"][0]["mentioned_at"] == "2026-10-01T00:00:00Z"
    assert (
        read(tmp_path, "empty.context.json")["recall"]["status"]
        == "not_requested_control"
    )
    assert (
        read(tmp_path, "adequate.context.json")["recall"]["status"]
        == "supplied_adequate_control"
    )


def test_pinned_recall_path_nonempty_strict_or_and_no_source_supplements(
    monkeypatch, tmp_path
):
    fake = FakeProviders(recalled=[memory(type="world", tags=["kind:profile"])])
    run(monkeypatch, tmp_path, fake)
    url, payload = fake.recalls[0]
    assert (
        url
        == f"http://hindsight/v1/default/banks/{inputs().scope.bank_id}/memories/recall"
    )
    assert payload["tags"] == ["character:C", "kind:profile"]
    assert payload["tags_match"] == "any_strict"
    assert payload["query_timestamp"] == inputs().query_timestamp
    assert payload["include"] == {
        "entities": None,
        "chunks": None,
        "source_facts": None,
    }
    assert payload["types"] == ["world", "experience", "observation"]


@pytest.mark.parametrize(
    "scope",
    [
        None,
        {},
        {"workspace_id": "W", "subject_id": "S"},
        {"workspace_id": "", "subject_id": "S", "character_root_id": "C"},
        {"workspace_id": "W", "subject_id": "S", "character_root_id": "../C"},
        {"workspace_id": "W", "subject_id": "S", "character_root_id": "C", "tags": []},
        {
            "workspace_id": "W",
            "subject_id": "S",
            "character_root_id": "C",
            "bank_id": "other",
        },
    ],
)
def test_invalid_or_missing_scope_rejected(scope):
    with pytest.raises(ValidationError):
        inputs(scope=scope)


def test_scope_continuity_and_subject_workspace_isolation():
    scope = RecallScope(workspace_id="W", subject_id="S", character_root_id="C")
    assert scope.bank_id == "ade-probe-44c3cae52ae1985bc222da4433c70032"
    assert scope.bank_id == scope.model_copy(update={"character_root_id": "D"}).bank_id
    assert scope.bank_id != scope.model_copy(update={"subject_id": "T"}).bank_id
    assert scope.bank_id != scope.model_copy(update={"workspace_id": "X"}).bank_id


@pytest.mark.parametrize(
    "tags,type,code",
    [
        ([], "world", "recall_scope_violation"),
        (["character:D"], "experience", "recall_scope_violation"),
        (["kind:profile"], "observation", "recall_observation_scope_violation"),
        (
            ["character:C", "character:D"],
            "observation",
            "recall_observation_scope_violation",
        ),
    ],
)
def test_scope_violations_stop_generation(monkeypatch, tmp_path, tags, type, code):
    fake = FakeProviders(recalled=[memory(tags=tags, type=type)])
    with pytest.raises(EvaluationError, match=code):
        run(monkeypatch, tmp_path, fake)
    assert fake.generations == []
    assert read(tmp_path, "failure.json")["code"] == code
    rejected = read(tmp_path, "hindsight.recall.json")
    assert rejected["result_projection"][0]["tags"] == tags
    assert rejected["result_projection"][0]["type"] == type
    assert rejected["request"]["tags_match"] == "any_strict"
    assert read(tmp_path, "hindsight.recall-trace.json")["reranked"]
    assert not (tmp_path / "receipts" / "completion.json").exists()


def test_genuine_empty_recall_is_visible(monkeypatch, tmp_path):
    fake = FakeProviders(recalled=[])
    run(monkeypatch, tmp_path, fake)
    context = read(tmp_path, "hindsight.context.json")
    assert context["recall"]["status"] == "ok_empty"
    assert context["memories"] == []
    assert len(fake.generations) == 3


@pytest.mark.parametrize(
    "status,malformed,code",
    [
        (503, False, "recall_unavailable"),
        (401, False, "recall_unavailable"),
        (200, True, "recall_response_invalid"),
    ],
)
def test_unavailable_is_never_empty_or_a_control_fallback(
    monkeypatch, tmp_path, status, malformed, code
):
    fake = FakeProviders(recall_status=status, malformed=malformed)
    with pytest.raises(EvaluationError, match=code):
        run(monkeypatch, tmp_path, fake)
    assert len(fake.recalls) == 1
    assert fake.generations == []
    assert not (tmp_path / "receipts" / "hindsight.context.json").exists()
    assert read(tmp_path, "failure.json")["arm"] == "hindsight"


def test_oversized_first_fact_stops_serialized_request(monkeypatch, tmp_path):
    fake = FakeProviders(recalled=[memory(text="海" * 20000)])
    with pytest.raises(EvaluationError, match="natural_context_serialized_overflow"):
        run(monkeypatch, tmp_path, fake)
    assert fake.generations == []
    assert len(read(tmp_path, "hindsight.context.json")["memories"][0]["text"]) == 20000


@pytest.mark.parametrize(
    "filename,expected_calls",
    [
        ("hindsight.request.json", 0),
        ("hindsight.result.json", 1),
        ("completion.json", 3),
    ],
)
def test_capture_failure_cannot_qualify(
    monkeypatch, tmp_path, filename, expected_calls
):
    fake = FakeProviders()
    capture = EvaluationCapture(tmp_path / "receipts")
    original_write = capture.write

    def fail(selected, value):
        if selected == filename:
            raise EvaluationError("capture_write_failed")
        original_write(selected, value)

    monkeypatch.setattr(capture, "write", fail)
    with pytest.raises(EvaluationError, match="capture_write_failed"):
        run(monkeypatch, tmp_path, fake, capture=capture)
    assert len(fake.generations) == expected_calls
    assert read(tmp_path, "failure.json")["code"] == "capture_write_failed"
    assert not (tmp_path / "receipts" / "completion.json").exists()


def test_filesystem_fsync_failure_is_fatal(monkeypatch, tmp_path):
    capture = EvaluationCapture(tmp_path / "receipts")
    monkeypatch.setattr(
        "os.fsync", lambda _descriptor: (_ for _ in ()).throw(OSError("disk failure"))
    )
    with pytest.raises(EvaluationError, match="capture_write_failed"):
        capture.write("request.json", {"model": "fake"})


@pytest.mark.parametrize("drift_at,calls", [(2, 0), (3, 1), (4, 1)])
def test_router_profile_drift_stops_comparison(monkeypatch, tmp_path, drift_at, calls):
    fake = FakeProviders(drift_at=drift_at)
    with pytest.raises(EvaluationError, match="router_model_binding_changed"):
        run(monkeypatch, tmp_path, fake)
    assert len(fake.generations) == calls


def test_tool_call_is_rejected_without_followup_generation(monkeypatch, tmp_path):
    fake = FakeProviders(tool_call=True)
    with pytest.raises(EvaluationError, match="conversation_tool_unexpected"):
        run(monkeypatch, tmp_path, fake)
    assert len(fake.generations) == 1


def test_truncated_reply_preserves_usage_but_cannot_complete(monkeypatch, tmp_path):
    fake = FakeProviders(finish="length")
    with pytest.raises(EvaluationError, match="character_output_incomplete"):
        run(monkeypatch, tmp_path, fake)
    assert len(fake.generations) == 1
    assert read(tmp_path, "hindsight.result.json")["usage"]["total_tokens"] == 133


def test_capture_existing_directory_and_file_are_never_overwritten(tmp_path):
    directory = tmp_path / "receipts"
    capture = EvaluationCapture(directory)
    capture.write("input.json", {"first": True})
    with pytest.raises(EvaluationError, match="capture_directory_unavailable"):
        EvaluationCapture(directory)
    with pytest.raises(EvaluationError, match="capture_write_failed"):
        capture.write("input.json", {"first": False})
    assert read(tmp_path, "input.json") == {"first": True}


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://user:secret@router/v1",
        "http://router?key=secret",
        "http://router/#secret",
        "file:///tmp/socket",
    ],
)
def test_service_urls_cannot_embed_credentials(url):
    with pytest.raises(EvaluationError, match="invalid_service_url"):
        service_url(url)


def test_cli_scope_and_invalid_input_need_no_services(tmp_path, capsys):
    assert (
        evaluation.main(
            [
                "scope",
                "--workspace-id",
                "W",
                "--subject-id",
                "S",
                "--character-root-id",
                "C",
            ]
        )
        == 0
    )
    scope = json.loads(capsys.readouterr().out)
    assert scope["tags"] == ["character:C", "kind:profile"]
    path = tmp_path / "invalid.json"
    path.write_text('{"scope": {}}')
    assert (
        evaluation.main(
            ["run", "--input", str(path), "--output-directory", str(tmp_path / "bad")]
        )
        == 1
    )
    assert "evaluation_input_invalid" in capsys.readouterr().err
    assert not (tmp_path / "bad").exists()


def test_projected_recall_excludes_diagnostics_and_arbitrary_metadata(
    monkeypatch, tmp_path
):
    raw = memory(
        metadata={"speaker": "assistant", "api_key": "NOT-A-CONTEXT-FIELD"},
        attachments=[{"text": "RAW-SOURCE"}],
        reasoning_content="SECRET-REASONING",
    )
    fake = FakeProviders(recalled=[raw])
    run(monkeypatch, tmp_path, fake)
    context = read(tmp_path, "hindsight.context.json")
    assert context["memories"][0]["metadata"] == {"speaker": "assistant"}
    text = json.dumps(context)
    assert "RAW-SOURCE" not in text and "SECRET-REASONING" not in text


def test_empty_and_adequate_controls_do_not_require_hindsight(monkeypatch, tmp_path):
    fake = FakeProviders()
    run(monkeypatch, tmp_path, fake, inputs(arms=["empty", "adequate"]))
    assert fake.recalls == []
    assert len(fake.generations) == 2
