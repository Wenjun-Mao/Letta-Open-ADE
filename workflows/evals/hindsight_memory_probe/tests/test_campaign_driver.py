import asyncio
import json
import uuid
from types import SimpleNamespace

import httpx
import pytest

from workflows.evals.hindsight_memory_probe import freeze, replay
from workflows.evals.hindsight_memory_probe import driver_support
from workflows.evals.hindsight_memory_probe.driver_support import HindsightHTTP
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore


def test_reference_context_is_exact_prior_excerpt_and_excludes_private_origin():
    fixture = json.loads(freeze.FIXTURE.read_text(encoding="utf-8"))
    by_id = {source["id"]: source for source in fixture["sources"]}
    s02 = by_id["s02"]
    context = freeze._bind_context(s02, by_id)
    assert "我喜欢茉莉奶茶，冰的、半糖。" in context
    assert "纸船靠岸" not in context and "雨巷接龙" not in context
    assert "content" not in s02["reference_context"][0]
    bad = json.loads(json.dumps(s02, ensure_ascii=False))
    bad["reference_context"][0]["excerpt"] += "纸船靠岸"
    with pytest.raises(ValueError, match="reference_excerpt_mismatch|reference_context_too_broad"):
        freeze._bind_context(bad, by_id)


def test_frozen_json_loader_rejects_duplicate_keys():
    with pytest.raises(ValueError, match="duplicate_json_key"):
        freeze.strict_json('{"role":"user","role":"assistant"}')


def test_offline_freeze_binds_candidate_and_full_retry_payload(monkeypatch):
    monkeypatch.setattr(freeze, "_feature_scope", lambda workspace, subject, root: {
        "workspace_id": workspace, "subject_id": subject, "character_root_id": root,
        "bank_id": f"bank-{subject}", "tags": [f"character:{root}", "kind:profile"], "tags_match": "any_strict"})
    monkeypatch.setattr(freeze.subprocess, "check_output", lambda command, **kwargs: b"" if command[1] == "status" else "clean-sha")
    manifest = freeze.build_manifest("candidate_workspace_01")
    assert len(manifest["sources"]) == 12 and len(manifest["cases"]) == 8
    s02 = next(source for source in manifest["sources"] if source["id"] == "s02")
    reference = s02["reference_context"][0]
    assert len(reference["source_sha256"]) == len(reference["message_sha256"]) == 64
    assert reference["role"] == "user" and reference["timestamp"] == "2026-10-01T09:00:00Z"
    assert s02["rendered_context_sha256"] == freeze.sha(s02["rendered_context"].encode())
    s10 = next(source for source in manifest["sources"] if source["id"] == "s10")
    assert s10["retain_payload"]["operation_id"]
    assert s10["retain_payload_sha256"] == freeze.sha(s10["retain_payload_utf8"].encode())
    assert s10["workspace"] == manifest["workspace_id"]
    assert "q07" in {case["id"] for case in manifest["cases"]}


def test_real_offline_freeze_validates_and_tampering_fails_before_http(monkeypatch, tmp_path):
    source_sha = "a" * 40
    real_scope = freeze._feature_scope
    scope_calls = []

    def tracked_scope(workspace, subject, root):
        scope_calls.append((workspace, subject, root))
        return real_scope(workspace, subject, root)

    monkeypatch.setattr(freeze, "_feature_scope", tracked_scope)
    monkeypatch.setattr(
        freeze.subprocess,
        "check_output",
        lambda command, **kwargs: b"" if command[1] == "status" else source_sha,
    )
    manifest = freeze.build_manifest("offline_review_workspace")
    assert len(scope_calls) == 3
    freeze.validate_manifest(manifest, expected_source_sha=source_sha)
    assert len(scope_calls) == 6

    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setenv("ADE_EVAL_SOURCE_SHA", "b" * 40)
    monkeypatch.setattr(replay, "HindsightHTTP", lambda *args, **kwargs: pytest.fail("HTTP client constructed before source identity validation"))
    args = SimpleNamespace(manifest=manifest_path, output_directory=tmp_path / "wrong-source", stage="readiness")
    with pytest.raises(ValueError, match="campaign_source_revision_mismatch"):
        asyncio.run(replay.run(args))

    tampered = json.loads(json.dumps(manifest))
    tampered["sources"][0]["retain_payload_utf8"] += " "
    monkeypatch.setenv("ADE_EVAL_SOURCE_SHA", source_sha)
    manifest_path.write_text(json.dumps(tampered), encoding="utf-8")
    args = SimpleNamespace(manifest=manifest_path, output_directory=tmp_path / "tampered", stage="readiness")
    with pytest.raises(ValueError, match="campaign_frozen_source_mismatch"):
        asyncio.run(replay.run(args))


def test_runner_wires_release_sha_to_manifest_runtime_identity():
    compose = (replay.WORKFLOW / "compose.yaml").read_text()
    assert "ADE_EVAL_SOURCE_SHA: ${PROBE_RELEASE_SHA:?clean release SHA required}" in compose
    assert "PROBE_RELEASE_SHA: ${PROBE_RELEASE_SHA:?clean release SHA required}" in compose
    assert "ADE_PROBE_REGISTRY_SHA256: ${ADE_PROBE_REGISTRY_SHA256:?guard registry identity required}" in compose
    assert "ADE_PROBE_EPOCH_SHA256: ${ADE_PROBE_EPOCH_SHA256:?guard epoch identity required}" in compose


def test_documented_restart_readback_entrypoint_has_cli_dispatch():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "workflows.evals.hindsight_memory_probe.restart_readback_cli", "--help"],
        cwd=replay.ROOT, capture_output=True, text=True, check=True,
    )
    assert "{capture,verify}" in result.stdout
    recipe = (replay.WORKFLOW / "README.md").read_text()
    assert "-m workflows.evals.hindsight_memory_probe.restart_readback_cli" in recipe


def test_frozen_retain_and_exact_retry_send_identical_payload_and_uuid(monkeypatch, tmp_path):
    payload = {
        "async": True, "operation_id": str(uuid.uuid4()),
        "items": [{"content": "用户：原文", "timestamp": "2026-10-01T18:00:00Z",
                   "document_id": "s10", "context": None,
                   "tags": ["character:root_xiaotang"],
                   "observation_scopes": [["character:root_xiaotang"]]}],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source = {"id": "s10", "subject": "subject_a", "root": "root_xiaotang",
              "document_content": "用户：原文", "rendered_context": None,
              "retain_payload": payload, "retain_payload_utf8": encoded,
              "retain_payload_sha256": freeze.sha(encoded.encode())}
    manifest = {"workspace_id": "candidate_1", "model_key": "deepseek::deepseek-flash",
                "persona": "你是林小棠。", "sources": [source], "cases": [],
                "adequate_memories": {}, "readiness": {}, "pins": {}}
    monkeypatch.setattr(replay, "feature_scope", lambda w, s, r: {
        "bank_id": "bank-one", "tags": [f"character:{r}", "kind:profile"], "tags_match": "any_strict"})
    post_bodies = []

    def handler(request):
        path = request.url.path
        if request.method == "POST" and path.endswith("/memories"):
            captured = [json.loads(file.read_text()) for file in (tmp_path / "campaign").glob("*-request.json")]
            assert any(item.get("body_utf8") == request.content.decode("utf-8") for item in captured)
            post_bodies.append(request.content)
            return httpx.Response(200, json={"success": True, "bank_id": "bank-one", "items_count": 1,
                                             "async": True, "operation_id": payload["operation_id"]})
        if request.method == "GET" and path.endswith("/operations/" + payload["operation_id"]):
            return httpx.Response(200, json={"operation_id": payload["operation_id"], "status": "completed",
                                             "error_message": "must not be captured"})
        if path.endswith("/config") and request.method == "GET":
            labels = [{"key":"kind","type":"value","tag":True,
                       "values":[{"value":"profile","description":"Standalone subject profile fact with no private origin."}]}]
            return httpx.Response(200, json={"config": {"enable_auto_consolidation": False,
                                                         "enable_observations": True,
                                                         "retain_mission": "Extract only source-grounded user profile facts and relationship-local experiences. Preserve speaker, time, correction versus change, hypothetical versus completed event, and whether an event was shared. A kind:profile tag is allowed only for a standalone profile fact safe without private origin. Never profile-tag a whole source or copy private origin.",
                                                         "observations_mission": "Summarize only source-supported facts in the supplied character-root observation scope. Preserve user versus assistant attribution, temporal correction versus preference change, solo versus shared experience, and explicit uncertainty. Never turn hypotheses into events.",
                                                         "entity_labels": labels}})
        if path.endswith("/config") and request.method == "PATCH":
            assert set(json.loads(request.content)) == {"updates"}
            return httpx.Response(200, json={"ok": True})
        if path.endswith("/banks/bank-one") and request.method == "PUT":
            return httpx.Response(200, json={"ok": True})
        if path.endswith("/documents/s10"):
            return httpx.Response(200, json={"id": "s10", "original_text": "用户：原文",
                                             "content_hash": "not-the-raw-sha",
                                             "retain_params": {"context": None}, "tags": ["character:root_xiaotang"],
                                             "observation_scopes": [["character:root_xiaotang"]],
                                             "memory_unit_count": 1})
        if path.endswith("/memories/list"):
            return httpx.Response(200, json={"items": [{"id": "fact-s10", "fact_type": "world"}],
                                             "total": 1, "limit": 100, "offset": 0})
        raise AssertionError((request.method, path))

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            campaign = replay.Campaign(manifest, tmp_path / "campaign", api)
            await campaign.retain("s10")
            await campaign.retain("s10", exact_retry=True)

    asyncio.run(exercise())
    assert len(post_bodies) == 2 and post_bodies[0] == post_bodies[1]
    assert json.loads(post_bodies[0])["operation_id"] == payload["operation_id"]
    receipts = list((tmp_path / "campaign").glob("*.json"))
    assert receipts
    assert all("must not be captured" not in file.read_text() for file in receipts)


def test_operation_failure_and_unavailable_http_are_safe(tmp_path):
    async def exercise():
        async def failing(request):
            return httpx.Response(200, json={"operation_id": "op", "status": "failed",
                                             "error_message": "provider secret/body"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(failing)) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            store = ReceiptStore(tmp_path / "failure")
            receipt = replay.NamedReceipt(store, "op")
            with pytest.raises(RuntimeError, match="operation_failed"):
                await api.operation("bank", "op", receipt)
            assert all("provider secret/body" not in p.read_text() for p in store.directory.glob("*.json"))

        async def unavailable(request):
            return httpx.Response(503, json={"detail": "sensitive response body"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(unavailable)) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            with pytest.raises(RuntimeError, match="hindsight_http_503"):
                await api.request("GET", "/v1/default/banks")

    asyncio.run(exercise())


def test_completed_parent_and_child_still_surface_nested_child_failure(tmp_path):
    async def exercise():
        def handler(request):
            operation_id = request.url.path.rsplit("/", 1)[-1]
            operations = {
                "parent": {"operation_id": "parent", "status": "completed",
                           "child_operations": [{"operation_id": "child", "status": "completed"}]},
                "child": {"operation_id": "child", "status": "completed",
                          "child_operations": [{"operation_id": "grandchild", "status": "failed"}]},
                "grandchild": {"operation_id": "grandchild", "status": "failed",
                               "error_message": "private provider detail"},
            }
            return httpx.Response(200, json=operations[operation_id])

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            store = ReceiptStore(tmp_path / "nested-failure")
            with pytest.raises(RuntimeError, match="operation_failed"):
                await api.operation("bank", "parent", replay.NamedReceipt(store, "nested"))
            assert all("private provider detail" not in path.read_text()
                       for path in store.directory.glob("*.json"))

    asyncio.run(exercise())


def test_completed_parent_and_child_wait_for_pending_grandchild(monkeypatch, tmp_path):
    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(driver_support.asyncio, "sleep", no_sleep)
    async def exercise():
        grandchild_reads = 0

        def handler(request):
            nonlocal grandchild_reads
            operation_id = request.url.path.rsplit("/", 1)[-1]
            if operation_id == "parent":
                body = {"operation_id": "parent", "status": "completed",
                        "child_operations": [{"operation_id": "child", "status": "completed"}]}
            elif operation_id == "child":
                body = {"operation_id": "child", "status": "completed",
                        "child_operations": [{"operation_id": "grandchild", "status": "pending"}]}
            else:
                grandchild_reads += 1
                status = "pending" if grandchild_reads == 1 else "completed"
                body = {"operation_id": "grandchild", "status": status,
                        "next_retry_at": "2026-10-11T00:00:00Z"}
            return httpx.Response(200, json=body)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            store = ReceiptStore(tmp_path / "nested-pending")
            await api.operation("bank", "parent", replay.NamedReceipt(store, "nested"))
        assert grandchild_reads == 2
        assert any('"next_retry_at": "2026-10-11T00:00:00Z"' in path.read_text()
                   for path in store.directory.glob("*.json"))

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("child_operations", "expected_error"),
    [
        ({"not": "a list"}, "operation_children_invalid"),
        ([{"operation_id": "child", "status": "completed"},
          {"operation_id": "child", "status": "completed"}], "operation_child_duplicate"),
        ([{"operation_id": "parent", "status": "completed"}], "operation_child_cycle"),
        ([{"operation_id": "child", "status": "failed"}], "operation_failed"),
    ],
)
def test_operation_child_shapes_cycles_duplicates_and_reported_failures(
    tmp_path, child_operations, expected_error
):
    async def exercise():
        seen = []

        def handler(request):
            operation_id = request.url.path.rsplit("/", 1)[-1]
            seen.append(operation_id)
            if operation_id == "parent":
                return httpx.Response(200, json={"operation_id": "parent", "status": "completed",
                                                "child_operations": child_operations})
            return httpx.Response(200, json={"operation_id": operation_id, "status": "completed"})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            with pytest.raises(RuntimeError, match=expected_error):
                await api.operation("bank", "parent", replay.NamedReceipt(ReceiptStore(tmp_path / expected_error), "op"))
        assert seen == ["parent"]

    asyncio.run(exercise())


def test_operation_deadline_bounds_each_request_and_rejects_late_completion(monkeypatch, tmp_path):
    ticks = iter((0.0, 0.25, 1.01))
    monkeypatch.setattr(driver_support, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    monkeypatch.setenv("ADE_EVAL_OPERATION_TIMEOUT_SECONDS", "1")

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            observed_timeouts = []

            async def late_request(method, path, **kwargs):
                observed_timeouts.append(kwargs["timeout"])
                return {"operation_id": "op", "status": "completed"}

            api.request = late_request
            with pytest.raises(RuntimeError, match="operation_timeout"):
                await api.operation("bank", "op", replay.NamedReceipt(ReceiptStore(tmp_path / "late"), "op"))
            assert observed_timeouts == [0.75]

    asyncio.run(exercise())


def test_operation_deadline_reduces_timeout_for_each_descendant(monkeypatch, tmp_path):
    ticks = iter((0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9))
    monkeypatch.setattr(driver_support, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    monkeypatch.setenv("ADE_EVAL_OPERATION_TIMEOUT_SECONDS", "1")

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            request_timeouts = []
            operations = {
                "parent": {"operation_id": "parent", "status": "completed",
                           "child_operations": [{"operation_id": "child", "status": "completed"}]},
                "child": {"operation_id": "child", "status": "completed",
                          "child_operations": [{"operation_id": "grandchild", "status": "completed"}]},
                "grandchild": {"operation_id": "grandchild", "status": "completed"},
            }

            async def request(_method, path, **kwargs):
                request_timeouts.append(kwargs["timeout"])
                return operations[path.rsplit("/", 1)[-1]]

            api.request = request
            await api.operation("bank", "parent", replay.NamedReceipt(ReceiptStore(tmp_path / "bounded"), "op"))
            assert request_timeouts == [0.9, 0.7, 0.5]

    asyncio.run(exercise())


def test_pagination_honors_total_limit_offset_and_detects_unavailable_page(tmp_path):
    async def exercise():
        seen = []
        def handler(request):
            offset = int(request.url.params["offset"])
            seen.append(offset)
            if offset == 0:
                return httpx.Response(200, json={"items": [{"id": str(i)} for i in range(100)], "total": 101, "limit": 100, "offset": 0})
            return httpx.Response(200, json={"items": [{"id": "100"}], "total": 101, "limit": 100, "offset": 100})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            api = HindsightHTTP(client, "http://hindsight", "synthetic-key")
            campaign = replay.Campaign({"workspace_id":"w","sources":[]}, tmp_path / "pages", api)
            rows = await campaign.pages("bank", "/v1/default/banks/bank/memories/list", "items")
        assert len(rows) == 101 and rows[-1]["id"] == "100" and seen == [0, 100]

    asyncio.run(exercise())


def test_runner_packages_public_driver_inputs_and_preserves_default_entrypoint():
    dockerfile = (replay.WORKFLOW / "docker/python.Dockerfile").read_text()
    compose = (replay.WORKFLOW / "compose.yaml").read_text()
    assert "workflows/evals/hindsight_memory_probe/*.py" in dockerfile
    assert "fixtures/campaign.json" in dockerfile and "content/personas/personas.jsonl" in dockerfile
    assert 'ENTRYPOINT ["python", "-m", "ade_api.features.agent_runtime.hindsight_evaluation"]' in dockerfile
    assert "ADE_EVAL_PHASE_FILE: /receipts/phase.json" in compose


def test_workflow_phase_targets_shared_router_pointer_and_keeps_stage_receipt(monkeypatch, tmp_path):
    from workflows.evals.hindsight_memory_probe import driver_support

    shared = tmp_path / "private-shared"
    shared.mkdir(mode=0o700)
    stage = tmp_path / "private-shared" / "stages" / "initial"
    stage.mkdir(mode=0o700, parents=True)
    target = shared / "phase.json"
    monkeypatch.setenv("ADE_EVAL_PHASE_FILE", str(target))
    marker = driver_support.set_phase(stage, "retain", "operation-1")
    router_read = json.loads(target.read_text())
    assert marker == router_read
    assert router_read["phase"] == "retain" and router_read["operation_id"] == "operation-1"
    assert target.parent == shared and target.parent != stage
