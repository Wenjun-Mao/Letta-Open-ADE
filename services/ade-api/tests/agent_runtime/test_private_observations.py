"""Capture mechanics only, with no live Memory or Character inference."""

import asyncio
import base64
import json
from uuid import uuid4

import httpx
import pytest

from ade_api.features.agent_runtime.private_observations import (
    AttemptObservation,
    capture_root,
    read_attempts,
)
from ade_api.features.agent_runtime.provider_tracing import AttemptTrace
from ade_api.features.agent_runtime.router_transport import (
    RouterTransport,
    RouterRequestError,
)
from ade_api.features.agent_runtime import router_transport
from ade_api.platform.settings import AdeApiSettings
from scripts.source_fingerprint import is_governed_source_path, source_fingerprint
from ade_api.features.agent_runtime.release_policy import (
    POLICY_INPUT_FILES,
    POLICY_INPUT_ROOTS,
    production_policy_hashes,
)
from model_router.request_observations import visible_response


def identity():
    return {
        key: str(uuid4())
        for key in ("workspace_id", "run_id", "conversation_id", "attempt_id")
    }


def test_private_records_are_create_only_private_content_bound_and_scope_checked(
    tmp_path,
):
    ids = identity()
    sink = AttemptObservation(tmp_path, ids)
    assert sink.record(
        "memory_lookup.completed",
        {"response": {"results": [{"text": "原文", "id": "m1"}]}},
    )
    exported = read_attempts(tmp_path, ids["run_id"], ids["workspace_id"])
    assert (
        exported[0]["records"][0]["value"]["response"]["results"][0]["text"] == "原文"
    )
    path = sink.path / "000001.json"
    assert path.stat().st_mode & 0o777 == 0o600
    assert sink.path.stat().st_mode & 0o777 == 0o700
    assert tmp_path.stat().st_mode & 0o777 == 0o700
    with pytest.raises(ValueError):
        read_attempts(tmp_path, ids["run_id"], str(uuid4()))
    restarted = AttemptObservation(tmp_path, ids)
    assert restarted.record("replacement", {}) is False
    original = json.loads(path.read_bytes())
    original["record"]["value"]["response"]["results"][0]["text"] = "rewritten"
    path.write_text(json.dumps(original))
    with pytest.raises(ValueError):
        read_attempts(tmp_path, ids["run_id"], ids["workspace_id"])


def test_private_fields_leave_only_incomplete_capture_without_silently_redacting(
    tmp_path,
):
    ids = identity()
    sink = AttemptObservation(tmp_path, ids)
    assert not sink.record(
        "request", {"message": {"reasoning_content": "DO-NOT-CAPTURE"}}
    )
    raw = (sink.path / "000001.json").read_text()
    assert "DO-NOT-CAPTURE" not in raw
    record = read_attempts(tmp_path, ids["run_id"], ids["workspace_id"])[0]["records"][
        0
    ]
    assert record["input_complete"] is False
    assert record["value"] == {"limitation": "private_fields_excluded"}


@pytest.mark.parametrize(
    "mode,key,root",
    [
        ("release", "isolated", "/private"),
        ("development", "default", "/private"),
        ("development", "isolated", "relative"),
    ],
)
def test_capture_requires_explicit_development_scope(mode, key, root):
    settings = AdeApiSettings(
        _env_file=None,
        auth_enabled=True,
        agent_runtime_mode=mode,
        agent_runtime_workspace_key=key,
        agent_runtime_observation_root=root,
        operator_key="controlled",
    )
    with pytest.raises(ValueError):
        capture_root(settings)
    settings.agent_runtime_observation_root = ""
    assert capture_root(settings) is None


def test_capture_refuses_public_directory_without_changing_its_permissions(tmp_path):
    public = tmp_path / "not-private"
    public.mkdir(mode=0o755)
    with pytest.raises(ValueError, match="private"):
        AttemptObservation(public, identity())
    assert public.stat().st_mode & 0o777 == 0o755


def test_capture_requires_authentication_and_an_operator_key(tmp_path):
    settings = AdeApiSettings(
        _env_file=None,
        auth_enabled=True,
        admin_key="",
        operator_key="",
        agent_runtime_mode="development",
        agent_runtime_workspace_key="synthetic",
        agent_runtime_observation_root=str(tmp_path),
    )
    with pytest.raises(ValueError, match="authenticated"):
        capture_root(settings)
    settings.operator_key = "controlled"
    assert capture_root(settings) == tmp_path
    settings.auth_enabled = False
    with pytest.raises(ValueError, match="authenticated"):
        capture_root(settings)


@pytest.mark.parametrize("status", [200, 502])
def test_actual_transport_correlates_success_and_failure_without_payload_or_auth_leak(
    monkeypatch, tmp_path, status
):
    ids = identity()
    router_id = str(uuid4())
    sent = []
    original_client = httpx.AsyncClient

    def handle(request):
        sent.append(request)
        assert request.headers["X-ADE-Run-Id"] == ids["run_id"]
        assert request.headers["X-ADE-Attempt-Id"] == ids["attempt_id"]
        assert request.headers["X-ADE-Observation-Role"] == "conversation"
        assert request.headers["X-ADE-Observation-Phase"] == "reply"
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(
            status,
            headers={"X-Model-Router-Request-Id": router_id},
            json={"id": "provider-1", "choices": []},
        )

    monkeypatch.setattr(
        router_transport.httpx,
        "AsyncClient",
        lambda **kw: original_client(transport=httpx.MockTransport(handle), **kw),
    )
    settings = AdeApiSettings(
        _env_file=None,
        auth_enabled=True,
        agent_runtime_mode="development",
        agent_runtime_workspace_key="synthetic",
        agent_runtime_observation_root=str(tmp_path),
        operator_key="controlled",
    )
    trace = AttemptTrace(attempt=1)
    trace.bind_attempt(
        settings=settings,
        run={
            "id": ids["run_id"],
            "workspace_id": ids["workspace_id"],
            "conversation_id": ids["conversation_id"],
        },
        attempt_id=ids["attempt_id"],
    )
    transport = trace.transport(
        RouterTransport("http://router/v1", "secret"), stage="conversation"
    )
    payload = {
        "model": "fake::character",
        "messages": [{"role": "user", "content": "原始输入"}],
    }
    if status == 200:
        asyncio.run(transport.chat_completion(payload, timeout_seconds=1))
    else:
        with pytest.raises(RouterRequestError):
            asyncio.run(transport.chat_completion(payload, timeout_seconds=1))
    assert len(sent) == 1
    assert json.loads(sent[0].content) == payload
    terminal = trace.normalized_events()[-1]
    assert terminal.payload["router_request_id"] == router_id
    assert terminal.payload["request_id"] == sent[0].headers["X-ADE-Request-Id"]
    raw = "".join(path.read_text() for path in tmp_path.rglob("*.json"))
    assert "secret" not in raw and "Authorization" not in raw
    records = read_attempts(tmp_path, ids["run_id"], ids["workspace_id"])[0]["records"]
    assert records[-1]["value"]["router_request_id"] == router_id


def test_native_base64_float32_dimensions_are_observed_without_vectors():
    encoded = base64.b64encode(b"\x00\x00\x80\x3f" * 1024).decode()
    value = visible_response(
        {
            "data": [
                {"embedding": encoded},
                {"embedding": [1, 2]},
                {"embedding": "!"},
                {"embedding": "eA=="},
            ]
        }
    )
    assert value == {"embedding_dimensions": [1024, 2, None, None]}
    assert encoded not in json.dumps(value)


@pytest.mark.parametrize(
    "name", ["hindsight.py", "hindsight_bank.py", "hindsight_sources.py"]
)
def test_hindsight_owning_sources_are_governed_and_policy_drift_is_detected(
    tmp_path, name
):
    paths = set(path for roots in POLICY_INPUT_ROOTS.values() for path in roots)
    for root in paths:
        (tmp_path / root).mkdir(parents=True, exist_ok=True)
    files = set(path for group in POLICY_INPUT_FILES.values() for path in group)
    for relative in files:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("before")
    relative = f"services/ade-api/src/ade_api/integrations/{name}"
    assert is_governed_source_path(relative)
    before = production_policy_hashes(tmp_path)
    source_before = source_fingerprint(tmp_path, [relative.encode()])
    (tmp_path / relative).write_text("after")
    after = production_policy_hashes(tmp_path)
    assert before["retrieval"] != after["retrieval"]
    assert source_before != source_fingerprint(tmp_path, [relative.encode()])
