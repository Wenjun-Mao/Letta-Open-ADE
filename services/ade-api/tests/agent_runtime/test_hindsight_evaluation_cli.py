"""CLI integration, trace separation and durable capture failure regressions."""

import json

import httpx
import pytest

from ade_api.features.agent_runtime import hindsight_evaluation as evaluation
from ade_api.features.agent_runtime.hindsight_eval_capture import EvaluationCapture
from ade_api.features.agent_runtime.hindsight_eval_contracts import EvaluationError

from .hindsight_eval_fakes import FakeProviders, inputs, read, run


def test_cli_runs_actual_boundary_with_environment_only_credentials(
    monkeypatch, tmp_path, capsys
):
    fake = FakeProviders()
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(fake.handle), **kwargs
        ),
    )
    for name, value in {
        "ADE_EVAL_ROUTER_BASE_URL": "http://router/v1",
        "ADE_EVAL_ROUTER_API_KEY": "router-secret",
        "ADE_EVAL_HINDSIGHT_BASE_URL": "http://hindsight",
        "ADE_EVAL_HINDSIGHT_API_KEY": "hindsight-secret",
    }.items():
        monkeypatch.setenv(name, value)
    path = tmp_path / "input.json"
    path.write_text(inputs().model_dump_json())
    args = [
        "run",
        "--input",
        str(path),
        "--output-directory",
        str(tmp_path / "receipts"),
    ]
    assert evaluation.main(args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"
    assert len(fake.generations) == 3
    assert evaluation.main(args) == 1
    assert "capture_directory_unavailable" in capsys.readouterr().err
    assert len(fake.generations) == 3


def test_trace_is_preserved_exactly_but_never_injected(monkeypatch, tmp_path):
    fake = FakeProviders()
    run(monkeypatch, tmp_path, fake)
    trace = read(tmp_path, "hindsight.recall-trace.json")
    assert trace["reranked"][0]["text"] == "TRACE-ONLY-CANDIDATE"
    assert trace["summary"]["phase_metrics"][0]["details"]["candidates_reranked"] == 1
    assert all(
        "TRACE-ONLY-CANDIDATE" not in json.dumps(request)
        for request in fake.generations
    )
    assert "trace" not in read(tmp_path, "hindsight.context.json")["recall"]


def test_missing_trace_stops_generation(monkeypatch, tmp_path):
    fake = FakeProviders()
    original = fake.handle

    def handle(request):
        response = original(request)
        if request.url.path.endswith("/memories/recall"):
            body = response.json()
            body.pop("trace")
            return httpx.Response(200, json=body)
        return response

    monkeypatch.setattr(fake, "handle", handle)
    with pytest.raises(EvaluationError, match="recall_trace_missing"):
        run(monkeypatch, tmp_path, fake)
    assert fake.generations == []


def test_invalid_result_type_is_captured_before_admission(monkeypatch, tmp_path):
    from .hindsight_eval_fakes import memory

    fake = FakeProviders(recalled=[memory(type="unsupported")])
    with pytest.raises(EvaluationError, match="recall_response_invalid"):
        run(monkeypatch, tmp_path, fake)
    assert (
        read(tmp_path, "hindsight.recall.json")["result_projection"][0]["type"]
        == "unsupported"
    )
    assert fake.generations == []


def test_recall_capture_failure_stops_before_admission_and_generation(
    monkeypatch, tmp_path
):
    fake = FakeProviders()
    capture = EvaluationCapture(tmp_path / "receipts")
    original = capture.write

    def fail(filename, value):
        if filename == "hindsight.recall.json":
            raise EvaluationError("capture_write_failed")
        return original(filename, value)

    monkeypatch.setattr(capture, "write", fail)
    with pytest.raises(EvaluationError, match="capture_write_failed"):
        run(monkeypatch, tmp_path, fake, capture=capture)
    assert len(fake.recalls) == 1
    assert fake.generations == []


def test_recall_timeout_is_one_attempt_and_never_empty(monkeypatch, tmp_path):
    fake = FakeProviders()
    original = fake.handle

    def handle(request):
        if request.url.path.endswith("/memories/recall"):
            fake.recalls.append(request)
            raise httpx.ReadTimeout("SECRET-DIAGNOSTIC", request=request)
        return original(request)

    monkeypatch.setattr(fake, "handle", handle)
    with pytest.raises(EvaluationError, match="recall_unavailable"):
        run(monkeypatch, tmp_path, fake)
    assert len(fake.recalls) == 1
    assert fake.generations == []
    assert "SECRET-DIAGNOSTIC" not in json.dumps(read(tmp_path, "failure.json"))
    request = read(tmp_path, "hindsight.recall-request.json")
    assert request["request"]["tags_match"] == "any_strict"
    failure = read(tmp_path, "hindsight.recall-failure.json")
    assert failure["error_type"] == "ReadTimeout"
    assert failure["http_status"] is None
    assert "SECRET-DIAGNOSTIC" not in json.dumps(failure)


def test_recall_request_capture_failure_prevents_recall(monkeypatch, tmp_path):
    fake = FakeProviders()
    capture = EvaluationCapture(tmp_path / "receipts")
    original = capture.write

    def fail(filename, value):
        if filename == "hindsight.recall-request.json":
            raise EvaluationError("capture_write_failed")
        return original(filename, value)

    monkeypatch.setattr(capture, "write", fail)
    with pytest.raises(EvaluationError, match="capture_write_failed"):
        run(monkeypatch, tmp_path, fake, capture=capture)
    assert fake.recalls == []
    assert fake.generations == []


def test_failed_fsync_leaves_no_completion_marker(monkeypatch, tmp_path):
    capture = EvaluationCapture(tmp_path / "receipts")

    def fail(_descriptor):
        raise OSError("disk failure")

    monkeypatch.setattr("os.fsync", fail)
    with pytest.raises(EvaluationError, match="capture_write_failed"):
        capture.write("completion.json", {"status": "completed"})
    assert not (tmp_path / "receipts" / "completion.json").exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"arms": ["adequate"], "adequate_memories": []},
        {"arms": ["empty"], "adequate_memories": [{"id": "a"}]},
        {"arms": ["empty", "empty"]},
        {"query_timestamp": "2026-10-11T12:00:00"},
        {"recall_max_tokens": 0},
        {"timeout_seconds": float("inf")},
        {"recall_types": []},
        {"dialogue": [{"role": "tool", "content": "bad"}]},
        {"synthetic": False},
    ],
)
def test_invalid_comparison_contract_rejected(changes):
    with pytest.raises(ValueError):
        inputs(**changes)
