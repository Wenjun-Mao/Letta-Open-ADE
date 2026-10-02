"""Scripted public transport only: finite attempts, drift and interruption."""

import asyncio
import base64
import copy
import json

import httpx
import pytest

from .. import contracts, receipts, runner
from ..contracts import ROUTE, load_prepared, wire
from ..transport import Router


def raw(value, status=200):
    body = value if isinstance(value, bytes) else wire(value).encode()
    return {"status": status, "body_base64": base64.b64encode(body).decode()}


def answer(content="visible", finish="stop", **message):
    return raw(
        {
            "choices": [
                {
                    "finish_reason": finish,
                    "message": {
                        "role": "assistant",
                        "content": content,
                        "reasoning_content": "PRIVATE REASONING",
                        **message,
                    },
                }
            ]
        }
    )


def catalog():
    return raw(
        {
            "generated_at": 123,
            "items": [copy.deepcopy(ROUTE)],
            "sources": [
                {
                    "id": "deepseek",
                    "adapter": "deepseek_openai",
                    "status": "healthy",
                    "base_url": "https://api.deepseek.com",
                    "models": [{"provider_model_id": "deepseek-flash"}],
                }
            ],
        }
    )


class Scripted:
    def __init__(self, outputs=None, preflight=None):
        self.outputs = (
            outputs
            if outputs is not None
            else [answer("visible"), answer('{"decisions":[]}')] * 3
        )
        self.preflight = preflight or catalog()
        self.sent = []
        self.catalogs = 0

    async def catalog(self):
        self.catalogs += 1
        return self.preflight

    async def send(self, request):
        self.sent.append(copy.deepcopy(request))
        response = self.outputs[len(self.sent) - 1]
        if isinstance(response, BaseException):
            raise response
        return response


def test_exact_six_calls_and_reply_only_and_no_replay(launch):
    directory, execute, _ = launch
    scripted = Scripted()
    result = execute(scripted)
    assert len(scripted.sent) == 6 and list(result) == list(runner.STAGES)
    for index in (1, 3, 5):
        packet = json.loads(scripted.sent[index]["messages"][1]["content"])
        assert packet["candidate_visible_reply"] == "visible"
        assert "PRIVATE REASONING" not in wire(scripted.sent[index])
    assert execute(scripted) == result and len(scripted.sent) == 6
    assert scripted.catalogs == 1
    assert len(list(directory.glob("*.intent.json"))) == 7
    assert len(list(directory.glob("*.raw.json"))) == 7


@pytest.mark.parametrize(
    "response",
    [
        raw(b"not JSON"),
        raw({}),
        answer(""),
        answer(None),
        answer("partial", "length"),
        answer("tool", tool_calls=[{"type": "function"}]),
        answer("refused", refusal="no"),
        answer("done", "content_filter"),
    ],
)
def test_complete_invalid_generation_skips_only_dependent_review(launch, response):
    _, execute, _ = launch
    script = Scripted(
        [
            response,
            answer("second"),
            answer('{"decisions":[]}'),
            answer("third"),
            answer('{"decisions":[]}'),
        ]
    )
    result = execute(script)
    assert len(script.sent) == 5
    assert result["literal-four.generation"]["disposition"] == "complete_unusable"
    assert result["literal-four.reviewer"]["disposition"] == "skipped"
    assert result["whole-pool.reviewer"]["disposition"] == "captured"
    execute(script)
    assert len(script.sent) == 5


@pytest.mark.parametrize(
    "response", [answer("garbage"), answer("{}", "length"), answer(""), answer("[]")]
)
def test_complete_invalid_reviewer_continues_without_repair(launch, response):
    _, execute, _ = launch
    script = Scripted(
        [
            answer(),
            response,
            answer(),
            answer('{"decisions":[]}'),
            answer(),
            answer('{"decisions":[]}'),
        ]
    )
    result = execute(script)
    assert len(script.sent) == 6
    assert result["literal-four.reviewer"]["disposition"] == "complete_unusable"


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError("uncertain dispatch"),
        httpx.ConnectError("transport"),
        raw({"error": "auth"}, 401),
        raw({"error": "routing"}, 404),
    ],
)
def test_transport_auth_routing_stops_consume_and_refuse(launch, failure):
    directory, execute, _ = launch
    script = Scripted([failure])
    result = execute(script)
    assert len(script.sent) == 1
    assert result["literal-four.reviewer"]["disposition"] == "unrun"
    assert (directory / "literal-four.generation.intent.json").exists()
    with pytest.raises(ValueError, match="stop"):
        execute(script)
    assert len(script.sent) == 1


def test_dispatch_interruption_refuses_even_without_outcome(launch):
    directory, execute, _ = launch
    script = Scripted([KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        execute(script)
    assert (
        runner.status(directory)["literal-four.generation"]["disposition"]
        == "uncertain_consumed"
    )
    with pytest.raises(ValueError, match="uncertain"):
        execute(script)
    assert len(script.sent) == 1


def test_capture_interruption_consumes_intent(launch, monkeypatch):
    directory, execute, _ = launch
    original = runner.write_once

    def interrupt(path, value):
        if path.name == "literal-four.generation.raw.json":
            raise OSError("capture interrupted")
        original(path, value)

    monkeypatch.setattr(runner, "write_once", interrupt)
    script = Scripted()
    with pytest.raises(OSError):
        execute(script)
    with pytest.raises(ValueError, match="uncertain"):
        execute(script)
    assert len(script.sent) == 1
    assert (
        runner.status(directory)["literal-four.generation"]["disposition"]
        == "uncertain_consumed"
    )


def test_fully_captured_prefix_resume_never_resends(launch, monkeypatch):
    directory, execute, _ = launch
    original = runner.source_receipt
    calls = 0
    origin = launch[2]

    def pause_source():
        nonlocal calls
        calls += 1
        if calls == 3:
            raise KeyboardInterrupt()
        return origin

    script = Scripted()
    with pytest.raises(KeyboardInterrupt):
        execute(script, source=pause_source)
    assert len(script.sent) == 1
    assert (directory / "literal-four.generation.outcome.json").exists()
    result = execute(script)
    assert len(script.sent) == 6 and script.catalogs == 2
    assert all(v["disposition"] == "captured" for v in result.values())
    assert runner.source_receipt is original


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_adapter", "generic_openai"),
        ("thinking_default_enabled", False),
        ("reasoning_effort_default", "low"),
        ("provider_model_id", "other"),
        ("source_base_url", "https://other.invalid"),
    ],
)
def test_route_profile_mismatch_no_chat(launch, field, value):
    directory, execute, _ = launch
    body = runner.response_object(catalog())
    body["items"][0][field] = value
    script = Scripted(preflight=raw(body))
    execute(script)
    assert not script.sent and (directory / "stop.json").exists()
    with pytest.raises(ValueError, match="stop"):
        execute(script)


def test_capacity_real_reply_global_stop_without_truncation(launch):
    directory, execute, _ = launch
    script = Scripted([answer("木" * 16384)])
    result = execute(script)
    assert len(script.sent) == 1
    assert result["literal-four.reviewer"]["disposition"] == "unrun"
    assert (
        receipts.read(directory / "stop.json")["reason"] == "actual_reviewer_capacity"
    )
    with pytest.raises(ValueError):
        execute(script)


def test_request_receipt_drift_resume_rejected(launch):
    directory, execute, _ = launch
    script = Scripted()
    execute(script)
    path = directory / "literal-four.generation.intent.json"
    intent = receipts.read(path)
    intent["request"]["messages"][0]["content"] = "drift"
    path.write_text(json.dumps(intent))
    with pytest.raises(ValueError, match="drift"):
        execute(script)
    assert len(script.sent) == 6


def test_source_drift_before_next_send_stops(launch):
    directory, execute, origin = launch
    count = 0

    def source():
        nonlocal count
        count += 1
        return origin if count < 3 else {**origin, "head": "drift"}

    script = Scripted()
    with pytest.raises(ValueError, match="Source drift"):
        execute(script, source)
    assert len(script.sent) == 1 and (directory / "stop.json").exists()


@pytest.mark.parametrize("kind", ["source", "request"])
def test_frozen_source_and_request_drift(tmp_path, monkeypatch, kind):
    original = contracts.DIRECTORY
    (tmp_path / "preparation.json").write_bytes(
        (original / "preparation.json").read_bytes()
    )
    (tmp_path / "requests.json").write_bytes((original / "requests.json").read_bytes())
    if kind == "request":
        (tmp_path / "requests.json").write_text("[]")
    else:
        preparation = json.loads((tmp_path / "preparation.json").read_bytes())
        preparation["source_sha256"]["pyproject.toml"] = "incorrect"
        (tmp_path / "preparation.json").write_text(json.dumps(preparation))
    monkeypatch.setattr(contracts, "DIRECTORY", tmp_path)
    with pytest.raises(ValueError, match="drift"):
        load_prepared()


def test_public_http_exact_bytes_no_retry_or_redirect():
    observed = []

    def handler(request):
        observed.append(request)
        return httpx.Response(
            307, content=b"raw redirect", headers={"Location": "https://other.invalid"}
        )

    async def exercise():
        router = Router(
            "http://127.0.0.1:9999",
            "synthetic-token",
            transport=httpx.MockTransport(handler),
        )
        try:
            result = await router.send({"model": "synthetic", "messages": []})
            assert result == raw(b"raw redirect", 307)
        finally:
            await router.close()

    asyncio.run(exercise())
    assert len(observed) == 1
    assert observed[0].url.path == "/v1/chat/completions"
    assert observed[0].content == wire({"model": "synthetic", "messages": []}).encode()


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:1",
        "http://localhost:1",
        "http://127.0.0.1:1/path",
        "http://user@127.0.0.1:1",
    ],
)
def test_nonisolated_transport_rejected(url):
    with pytest.raises(ValueError):
        Router(url, "synthetic-token")
