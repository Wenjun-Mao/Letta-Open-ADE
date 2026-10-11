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
    RecalledMemory,
    fingerprint,
)
from ade_api.features.agent_runtime.hindsight_eval_context import (
    character_context_projection,
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
        assert "Use their supported propositions to answer questions about" in dispatched[
            "messages"
        ][0]["content"]
        assert "do not establish that this character heard" in dispatched[
            "messages"
        ][0]["content"]
        assert "limit recollection claims" in dispatched["messages"][0]["content"]
        assert "clearly framed as current" in dispatched["messages"][0]["content"]
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
    history = context["character_context"]["same_character_history"]
    assert history[0]["metadata"]["speaker"] == "assistant"
    assert history[0]["mentioned_at"] == "2026-10-01T00:00:00Z"
    assert history[0]["context"] == memory()["context"]
    assert (
        read(tmp_path, "empty.context.json")["recall"]["status"]
        == "not_requested_control"
    )
    assert (
        read(tmp_path, "adequate.context.json")["recall"]["status"]
        == "supplied_adequate_control"
    )


def test_phase_enabled_comparison_uses_unique_arm_phase_receipts(
    monkeypatch, tmp_path
):
    baseline_fake = FakeProviders()
    baseline_path = tmp_path / "baseline"
    baseline_path.mkdir()
    with monkeypatch.context() as baseline_patch:
        baseline_patch.delenv("ADE_EVAL_PHASE_FILE", raising=False)
        run(baseline_patch, baseline_path, baseline_fake)
    fake = FakeProviders()
    target = tmp_path / "phase.json"
    monkeypatch.setenv("ADE_EVAL_PHASE_FILE", str(target))
    result = run(monkeypatch, tmp_path, fake)

    assert result["status"] == "completed"
    assert len(fake.generations) == 3
    assert len(fake.recalls) == 1
    assert fake.generations == baseline_fake.generations
    assert read(tmp_path, "binding.json")["router_model"] == read(
        baseline_path, "binding.json"
    )["router_model"]
    assert read(tmp_path, "binding.json")["frozen_input_sha256"] == read(
        baseline_path, "binding.json"
    )["frozen_input_sha256"]
    expected = {
        "hindsight.recall.phase.json": ("recall", "story-detail:hindsight:recall"),
        "hindsight.character.phase.json": (
            "character",
            "story-detail:hindsight:character",
        ),
        "empty.character.phase.json": ("character", "story-detail:empty:character"),
        "adequate.character.phase.json": (
            "character",
            "story-detail:adequate:character",
        ),
    }
    receipts = {name: read(tmp_path, name) for name in expected}
    for name, (phase, correlation_id) in expected.items():
        assert receipts[name]["phase"] == phase
        assert receipts[name]["correlation_id"] == correlation_id
        assert receipts[name]["operation_id"].startswith("eval-")
    assert len({item["operation_id"] for item in receipts.values()}) == 4
    assert len({item["correlation_id"] for item in receipts.values()}) == 4
    for arm in inputs().arms:
        assert read(tmp_path, f"{arm}.request.json") == fake.generations[
            inputs().arms.index(arm)
        ]
        assert read(tmp_path, f"{arm}.result.json")["assistant_text"] == read(
            baseline_path, f"{arm}.result.json"
        )["assistant_text"]
    assert json.loads(target.read_text())["phase"] == "character"
    all_receipts = "\n".join(
        path.read_text() for path in (tmp_path / "receipts").iterdir()
    )
    assert "hindsight-secret" not in all_receipts
    assert "router-secret" not in all_receipts
    assert "PRIVATE-REASONING" not in all_receipts


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
    assert context["character_context"] == {
        "shared_profile_facts": [],
        "same_character_history": [],
    }
    assert len(fake.generations) == 3


@pytest.mark.parametrize("field", ["text", "context"])
def test_private_origin_exclusion_checks_memory_text_and_context_before_generation(
    monkeypatch, tmp_path, field
):
    candidate = memory(**{field: "雨巷接龙"})
    fake = FakeProviders(recalled=[candidate])
    request = inputs(arms=["hindsight"], adequate_memories=[],
                     excluded_memory_terms=["雨巷接龙", "纸船靠岸"])
    with pytest.raises(EvaluationError, match="recall_content_exclusion"):
        run(monkeypatch, tmp_path, fake, request=request)
    assert fake.generations == []
    assert read(tmp_path, "failure.json")["code"] == "recall_content_exclusion"


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
    assert (
        len(
            read(tmp_path, "hindsight.context.json")["character_context"][
                "same_character_history"
            ][0]["text"]
        )
        == 20000
    )


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
    assert context["character_context"]["same_character_history"][0]["metadata"] == {
        "speaker": "assistant"
    }
    text = json.dumps(context)
    assert "RAW-SOURCE" not in text and "SECRET-REASONING" not in text


@pytest.mark.parametrize(
    "tags,metadata,expected_group",
    [
        (
            ["character:C", "kind:profile"],
            {"character_root_id": "C"},
            "same_character_history",
        ),
        (["character:C", "kind:profile"], {}, "same_character_history"),
        (["kind:profile"], {"character_root_id": "C"}, "same_character_history"),
        (
            ["character:A", "kind:profile"],
            {"character_root_id": "A"},
            "shared_profile_facts",
        ),
        (["kind:profile"], {}, "shared_profile_facts"),
        (
            ["character:C", "kind:profile"],
            {"character_root_id": "A"},
            "shared_profile_facts",
        ),
        (
            ["character:C", "character:A", "kind:profile"],
            {"character_root_id": "C"},
            "shared_profile_facts",
        ),
        (["character:", "kind:profile"], {}, "shared_profile_facts"),
    ],
)
def test_profile_facts_are_grouped_and_foreign_attribution_is_removed(
    monkeypatch, tmp_path, tags, metadata, expected_group
):
    candidate = memory(
        type="world",
        tags=tags,
        metadata={"source_id": "source-1", "speaker": "user", **metadata},
        context="source window",
        text="portable fact | When: 2026-10-01T09:00:00Z",
        mentioned_at="2026-10-01T00:00:00Z",
        document_id="source-document",
        source_fact_ids=["source-fact"],
        occurred_start="2026-10-01T09:00:00Z",
        occurred_end="2026-10-01T10:00:00Z",
    )
    fake = FakeProviders(recalled=[candidate])
    run(
        monkeypatch,
        tmp_path,
        fake,
        request=inputs(arms=["hindsight"], adequate_memories=[]),
    )

    diagnostic = read(tmp_path, "hindsight.recall.json")["result_projection"][0]
    context_receipt = read(tmp_path, "hindsight.context.json")
    context_groups = context_receipt["character_context"]
    assert context_groups[expected_group]
    character_capture = context_groups[expected_group][0]
    assert diagnostic["context"] == "source window"
    assert context_receipt["recall"]["status"] == "ok_nonempty"
    assert len(fake.generations) == 1
    assert character_capture["text"] == diagnostic["text"]
    assert character_capture["occurred_start"] == diagnostic["occurred_start"]
    assert character_capture["occurred_end"] == diagnostic["occurred_end"]
    if expected_group == "same_character_history":
        assert character_capture["context"] == diagnostic["context"]
        for key in (
            "id",
            "type",
            "tags",
            "mentioned_at",
            "document_id",
            "source_fact_ids",
            "metadata",
        ):
            assert character_capture[key] == diagnostic[key]
    else:
        assert "context" not in character_capture
        assert character_capture["tags"] == ["kind:profile"]
        assert "mentioned_at" not in character_capture
        assert "document_id" not in character_capture
        assert "source_fact_ids" not in character_capture
        assert "metadata" not in character_capture
    dispatched = fake.generations[0]
    suffix = dispatched["messages"][0]["content"].split(
        evaluation.CONTEXT_INSTRUCTIONS, 1
    )[1]
    assert json.loads(suffix)[expected_group] == [character_capture]
    assert (
        json.loads(suffix)["same_character_history"]
        == context_groups["same_character_history"]
    )
    assert (
        json.loads(suffix)["shared_profile_facts"]
        == context_groups["shared_profile_facts"]
    )


def test_matching_root_tag_authorizes_adequate_context_without_metadata(
    monkeypatch, tmp_path
):
    adequate = memory(
        type="world",
        tags=["character:C"],
        metadata={"source_id": "source-1"},
        context="source window",
    )
    fake = FakeProviders()
    request = inputs(
        arms=["adequate"],
        adequate_memories=[adequate],
    )
    run(monkeypatch, tmp_path, fake, request=request)

    captured = read(tmp_path, "adequate.context.json")["character_context"][
        "same_character_history"
    ][0]
    assert captured["context"] == "source window"
    dispatched = fake.generations[0]
    suffix = dispatched["messages"][0]["content"].split(
        evaluation.CONTEXT_INSTRUCTIONS, 1
    )[1]
    assert json.loads(suffix)["same_character_history"] == [captured]
    assert json.loads(suffix)["shared_profile_facts"] == []


@pytest.mark.parametrize(
    "tags,metadata",
    [
        (["character:A"], {}),
        (["character:C", "character:A"], {}),
        (["character:C", "character:"], {}),
        (["character:C"], {"character_root_id": "A"}),
        ([], {"character_root_id": "A"}),
        ([], {}),
    ],
)
def test_nonprofile_context_requires_one_valid_active_owner(tags, metadata):
    candidates = [
        RecalledMemory.model_validate(
            memory(type="experience", tags=tags, metadata=metadata)
        )
    ]
    projected = character_context_projection(candidates, character_root_id="C")
    assert projected == {
        "shared_profile_facts": [],
        "same_character_history": [],
    }


def test_profile_fact_and_present_fiction_boundary_is_in_character_request():
    messages = evaluation.character_messages(
        inputs(arms=["empty"], adequate_memories=[]), {}
    )
    system = messages[0]["content"]
    assert "limit recollection claims" in system
    assert "supported by these lists" in system
    assert "present interpretation or new" in system
    assert "clearly framed as current" in system
    assert "previously said or" in system
    assert "shared" in system


def test_empty_and_adequate_controls_do_not_require_hindsight(monkeypatch, tmp_path):
    fake = FakeProviders()
    run(monkeypatch, tmp_path, fake, inputs(arms=["empty", "adequate"]))
    assert fake.recalls == []
    assert len(fake.generations) == 2
