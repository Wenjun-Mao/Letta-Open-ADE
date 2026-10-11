"""Offline contracts for ordered finalization and public restart readback."""

import asyncio
import hashlib
import json

import pytest

from workflows.evals.hindsight_memory_probe import (
    candidate_database,
    driver_support,
    finalization,
    restart_readback,
    restart_selection,
)
from workflows.evals.hindsight_memory_probe.receipts import ReceiptStore


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def test_finalization_failure_receipts_use_only_fixed_safe_diagnostic_codes():
    assert finalization.failure_code(RuntimeError("finalization_process_identity_changed")) == (
        "finalization_process_identity_changed")
    assert finalization.failure_code(RuntimeError("private text or argv")) == "finalization_stage_failed"
    assert finalization.failure_code(RuntimeError(["not", "a", "code"])) == "finalization_stage_failed"


def db_container():
    return {
        "Id": "candidate-db-id", "Image": "candidate-db-image",
        "Mounts": [{"Name": "ade-hindsight-probe_db-data", "Destination": "/var/lib/postgresql/data"}],
    }


def test_dump_keeps_binary_stdout_separate_from_stderr_and_publishes_hash(tmp_path, monkeypatch):
    state = tmp_path / "supervisor"
    store = ReceiptStore(state)
    token = "a" * 32
    admitted = {"token": token, "registry_sha256": "registry", "epoch_sha256": "epoch",
                "dump_timeout": 10, "restart_readback": {"status": "absent"}}
    root = state / "finalization" / token
    root.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(candidate_database, "db_container", lambda *_: db_container())
    monkeypatch.setattr(candidate_database, "psql_text", lambda *_: "hindsight_probe")
    monkeypatch.setattr(finalization.epochs, "active", lambda *_: {"sha256": "epoch", "index": 1})

    def monitored(_directory, _registry, _epoch, _admitted, command, _timeout, *, stdout, stderr, **kwargs):
        if "pg_dump" in command:
            stdout.write(b"PGDMP\x00ARCHIVE")
            stderr.write(b"diagnostic that must never enter the archive")
            return 0
        assert "pg_restore" in command
        return 0

    monkeypatch.setattr(finalization, "run_monitored", monitored)
    result = candidate_database.dump_database(tmp_path, {"release": "/release"}, admitted,
                                             {"volume": "ade-hindsight-probe_db-data", "database": "hindsight_probe"}, store, finalization.run_monitored)
    archive = root / result["archive"]
    assert archive.read_bytes() == b"PGDMP\x00ARCHIVE"
    assert result["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert result["toc_valid"] is True
    assert not list(root.glob("*.stderr.partial"))


@pytest.mark.parametrize("dump_status,toc_status,expected", [(1, 0, "candidate_dump_failed"), (0, 1, "candidate_dump_toc_invalid")])
def test_failed_dump_is_never_published(tmp_path, monkeypatch, dump_status, toc_status, expected):
    state = tmp_path / "supervisor"
    store = ReceiptStore(state)
    token = "b" * 32
    admitted = {"token": token, "registry_sha256": "registry", "epoch_sha256": "epoch",
                "dump_timeout": 10, "restart_readback": {"status": "absent"}}
    root = state / "finalization" / token
    root.mkdir(parents=True, mode=0o700)
    monkeypatch.setattr(candidate_database, "db_container", lambda *_: db_container())
    monkeypatch.setattr(candidate_database, "psql_text", lambda *_: "hindsight_probe")
    monkeypatch.setattr(finalization.epochs, "active", lambda *_: {"sha256": "epoch", "index": 1})

    def monitored(_directory, _registry, _epoch, _admitted, command, _timeout, *, stdout, stderr, **kwargs):
        if "pg_dump" in command:
            stdout.write(b"PGDMP partial")
            stderr.write(b"private diagnostic")
            return dump_status
        return toc_status

    monkeypatch.setattr(finalization, "run_monitored", monitored)
    with pytest.raises(RuntimeError, match=expected):
        candidate_database.dump_database(tmp_path, {"release": "/release"}, admitted,
                                         {"volume": "ade-hindsight-probe_db-data", "database": "hindsight_probe"}, store, finalization.run_monitored)
    assert not (root / "candidate.dump").exists()
    assert not (state / f"finalize-{token}-dump-result.json").exists()


def test_async_drain_counts_deferred_as_active_and_preserves_terminal_summary(monkeypatch):
    monkeypatch.setattr(candidate_database, "db_container", lambda *_: db_container())
    monkeypatch.setattr(candidate_database, "psql_text", lambda *_: json.dumps({
        "pending": 1, "processing": 2, "deferred": 3, "failed": 4, "cancelled": 5,
    }))
    counts = candidate_database.operation_status_counts(None, {}, {}, lambda *_: None)
    assert counts == {"pending": 1, "processing": 2, "deferred": 3, "failed": 4, "cancelled": 5}
    assert candidate_database.operation_count(None, {}, {}, lambda *_: None) == 6


def test_finalization_intent_cannot_authorize_an_unadmitted_container(tmp_path):
    epoch = {"index": 1}
    token = "c" * 32
    admitted = {"token": token, "containers": [{"id": "admitted-db", "service": "db"}]}
    (tmp_path / "epoch-0001.finalize-admission.json").write_text(json.dumps(admitted))
    (tmp_path / f"finalize-{token}-hindsight-stop.intent.json").write_text(json.dumps({
        "services": ["hindsight"], "container_ids": ["forged-container"],
    }))
    with pytest.raises(RuntimeError, match="identity_mismatch"):
        finalization.planned_ids(tmp_path, epoch)


def test_non_stop_stage_intents_do_not_become_planned_container_exits(tmp_path):
    token = "e" * 32
    epoch = {"index": 1}
    admitted = {"token": token, "containers": []}
    (tmp_path / "epoch-0001.finalize-admission.json").write_text(json.dumps(admitted))
    (tmp_path / f"finalize-{token}-canonical-snapshot.intent.json").write_text(json.dumps({
        "token": token, "started_at": 123,
    }))
    assert finalization.planned_ids(tmp_path, epoch) == set()


def test_runner_removal_requires_a_completed_registered_runner_run(tmp_path, monkeypatch):
    token = "f" * 32
    (tmp_path / f"job-{token}.result.json").write_text(json.dumps({"exit_code": 0}))
    monkeypatch.setattr(finalization.host, "tagged_processes", lambda _token: [])
    admitted = {"jobs": [{"token": token, "kind": "work", "operation": "run", "service": "runner"}]}
    row = {"service": "runner", "oneoff": True}
    assert finalization.runner_removal_proven(tmp_path, admitted, row)
    admitted["jobs"][0]["operation"] = "exec"
    assert not finalization.runner_removal_proven(tmp_path, admitted, row)


def test_emergency_stop_marker_preempts_a_pending_finalizer(tmp_path):
    from workflows.evals.hindsight_memory_probe import quiescence

    epoch = {"index": 7}
    store = ReceiptStore(tmp_path)
    store.write(quiescence.stop_path(tmp_path, epoch).name, {"reason": "safety"})
    with pytest.raises(RuntimeError, match="preempted"):
        finalization.monitor(tmp_path, {}, epoch, {})


def test_finalization_orders_worker_stop_snapshot_dump_then_router_database(tmp_path, monkeypatch):
    state = tmp_path / "supervisor"
    store = ReceiptStore(state)
    registry = {"registry_sha256": "registry", "release": "/release"}
    epoch = {"index": 1, "sha256": "epoch", "release": "/release", "allocations": {}}
    token = "d" * 32
    admitted = {"registry_sha256": "registry", "epoch_sha256": "epoch", "token": token,
                "jobs": [], "admitted_at": 1, "drain_timeout": 30, "deadline": 100,
                "restart_readback": {"status": "absent"}}
    store.write("epoch-0001.finalize-admission.json", admitted)
    actions = []
    monkeypatch.setattr(finalization, "wait_until", lambda *_args, **_kwargs: actions.append("drain-check"))
    monkeypatch.setattr(candidate_database, "operation_count", lambda *_args: 0)
    monkeypatch.setattr(candidate_database, "operation_status_counts", lambda *_args: {"completed": 2})
    monkeypatch.setattr(finalization, "stop_service", lambda _directory, _registry, _admitted, _epoch, _store, service: actions.append(f"stop-{service}"))
    monkeypatch.setattr(candidate_database, "snapshot_database", lambda *_args: actions.append("snapshot") or {"snapshot": True})
    monkeypatch.setattr(candidate_database, "dump_database", lambda *_args: actions.append("dump") or {"dump": True})
    finalization.execute(state, registry, epoch, store)
    assert actions == ["drain-check", "drain-check", "stop-runner", "stop-hindsight", "snapshot",
                       "dump", "stop-model-router", "stop-db"]


@pytest.mark.parametrize("planned,expected", [(True, None), (False, "candidate_service_exited")])
def test_only_exact_admitted_hindsight_exit_is_a_planned_lifecycle_exit(planned, expected):
    from workflows.evals.hindsight_memory_probe import host_guard as host

    item = {
        "Id": "hindsight-id", "Image": "image-id", "RestartCount": 0,
        "State": {"StartedAt": "start", "Status": "exited", "OOMKilled": False},
        "HostConfig": {"Memory": 1, "NanoCpus": 1},
        "Config": {"Labels": {
            "com.docker.compose.project": host.PROJECT,
            "com.docker.compose.service": "hindsight",
            "com.docker.compose.project.working_dir": "/release/workflows/evals/hindsight_memory_probe",
            "com.docker.compose.project.config_files": "/release/workflows/evals/hindsight_memory_probe/compose.yaml",
        }},
    }
    registry = {"baseline": [], "release": "/release"}
    lifecycle_view = {"containers": {"hindsight-id": "planned_stopped"} if planned else {}, "reason": None}
    reason, _ = host.guard_reason(
        registry, [item], 4 * host.GIB, 20 * host.GIB, None, 1,
        lifecycle_view=lifecycle_view,
    )
    assert reason == expected


def test_restart_readback_compares_independent_source_context_and_fact_states(tmp_path):
    context = "the frozen retain context"
    source_text = "The original retained source."
    fact_text = "The selected fact."
    memory_rows = [
        {"id": "profile-only", "text": "Profile fact.", "tags": ["kind:profile"], "fact_type": "world"},
        {"id": "character-fact", "text": fact_text, "tags": ["character:root-x"], "fact_type": "experience"},
        {"id": "local-observation", "text": "Local observation.", "tags": ["character:root-x"], "fact_type": "observation"},
        {"id": "other-root", "text": "Other root fact.", "tags": ["character:root-y"], "fact_type": "world"},
        {"id": "untagged", "text": "Untagged fact.", "tags": [], "fact_type": "world"},
        {"id": "other-observation", "text": "Other observation.", "tags": ["character:root-y"], "fact_type": "observation"},
        {"id": "mixed-observation", "text": "Cross-root observation.", "tags": ["character:root-x", "character:root-y"], "fact_type": "observation"},
    ]
    memory_rows = [dict(row, document_id="source-a", state="valid", context=context,
                        source_memory_ids=[]) for row in memory_rows]
    invalidated_row = {"id": "fact-invalid", "text": "Removed fact.", "document_id": "source-a",
                       "state": "invalidated", "tags": ["kind:profile"], "fact_type": "world",
                       "context": context, "source_memory_ids": []}
    cohort = [row["id"] for row in memory_rows] + [invalidated_row["id"]]
    positives = ["profile-only", "character-fact", "local-observation"]
    exclusions = sorted(set(cohort) - set(positives))
    subject_bank = driver_support.feature_scope("workspace-a", "subject-a", "root-x")["bank_id"]
    selection = {"schema": 1, "release_sha": "a" * 40, "registry_sha256": "b" * 64,
                 "before_epoch_sha256": "c" * 64, "banks": [{"bank_id": subject_bank,
        "workspace_id": "workspace-a", "subject_id": "subject-a", "scopes": [{
            "character_root_id": "root-x", "tags": ["character:root-x", "kind:profile"],
            "tags_match": "any_strict", "cohort_ids": cohort,
            "positive_ids": positives, "exclusion_ids": exclusions}], "sources": [{
        "source_id": "source-a", "original_text_sha256": digest(source_text),
        "context_sha256": digest(context), "content_hash": "source-content-hash",
        "curation_ids": ["fact-invalid"],
        "facts": {"valid": [{"id": row["id"], "text_sha256": digest(row["text"])} for row in memory_rows],
                  "invalidated": [{"id": "fact-invalid", "text_sha256": digest("Removed fact.")}]},
    }] }]}

    invalid_bank = json.loads(json.dumps(selection))
    invalid_bank["banks"][0]["bank_id"] = driver_support.feature_scope(
        "workspace-a", "subject-b", "root-x"
    )["bank_id"]
    invalid_bank_path = tmp_path / "wrong-subject-bank.json"
    invalid_bank_path.write_text(json.dumps(invalid_bank))
    with pytest.raises(RuntimeError, match="scope_contract_mismatch"):
        restart_readback.read_selection(invalid_bank_path)

    entity_names = {
        "profile-only": ["Alice, Jr.", "Bob", "Bob"],
        "character-fact": ["Xiaotang"],
        "local-observation": ["Greenhouse"],
        "other-root": ["Other root"],
        "untagged": ["No tag"],
        "other-observation": ["Other observation"],
        "mixed-observation": ["Mixed observation"],
        "fact-invalid": ["Removed, source"],
    }

    class FakeHTTP:
        calls = []

        def __init__(self, *, reverse_entities=False, changed_entities=None):
            self.reverse_entities = reverse_entities
            self.changed_entities = changed_entities or {}

        async def request(self, method, path, *, params=None, **_kwargs):
            self.calls.append(path)
            if path.endswith("/memories/list"):
                state = params["state"]
                items = memory_rows if state == "valid" else [invalidated_row]
                return {"items": items, "total": len(items), "limit": 100, "offset": 0}
            if "/memories/" in path:
                memory_id = path.rsplit("/", 1)[1]
                source = next((row for row in memory_rows + [invalidated_row]
                               if row["id"] == memory_id), None)
                names = self.changed_entities.get(memory_id, entity_names[memory_id])
                if self.reverse_entities:
                    names = list(reversed(names))
                return {"id": memory_id, "text": source["text"], "context": context,
                        "date": "", "type": source["fact_type"], "entities": names,
                        "document_id": source["document_id"], "state": source["state"]}
            return {"id": "source-a", "original_text": source_text, "content_hash": "source-content-hash",
                    "retain_params": {"context": context}}

    before = asyncio.run(restart_readback.capture(selection, FakeHTTP(), {
        "release_sha": selection["release_sha"], "registry_sha256": selection["registry_sha256"],
        "epoch_sha256": selection["before_epoch_sha256"],
    }))
    assert all(f"/banks/{subject_bank}/" in path for path in FakeHTTP.calls)
    assert any(path.endswith("/memories/profile-only") for path in FakeHTTP.calls)
    assert any(path.endswith("/memories/fact-invalid") for path in FakeHTTP.calls)
    after = asyncio.run(restart_readback.capture(selection, FakeHTTP(reverse_entities=True), {
        "release_sha": selection["release_sha"], "registry_sha256": selection["registry_sha256"],
        "epoch_sha256": "d" * 64,
    }))
    proof = restart_readback.compare(before, after, selection)
    assert proof["claim"] == "bounded_restart_persistence_readback"
    profile = next(row for row in after["banks"][0]["sources"][0]["facts"]["valid"]
                   if row["id"] == "profile-only")
    expected_entities = json.dumps(
        ["Alice, Jr.", "Bob", "Bob"], ensure_ascii=False, separators=(",", ":")
    )
    assert profile["entities_sha256"] == digest(expected_entities)
    membership_drift = asyncio.run(restart_readback.capture(selection, FakeHTTP(
        changed_entities={"fact-invalid": ["Removed, source", "New member"]}
    ), {
        "release_sha": selection["release_sha"], "registry_sha256": selection["registry_sha256"],
        "epoch_sha256": "e" * 64,
    }))
    with pytest.raises(RuntimeError, match="restart_persistence_readback_mismatch"):
        restart_readback.compare(before, membership_drift, selection)
    evidence_root = tmp_path / "p4" / selection["release_sha"]
    evidence_root.mkdir(parents=True)
    selection_path = evidence_root / "restart-selection.json"
    before_path = evidence_root / "restart-readback.before.json"
    after_path = evidence_root / "restart-readback.after.json"
    selection_path.write_text(json.dumps(selection))
    before_path.write_text(json.dumps(before))
    after_path.write_text(json.dumps(after))
    proof.update({
        "selection_file_sha256": restart_selection.sha256_file(selection_path),
        "before_file_sha256": restart_selection.sha256_file(before_path),
        "after_file_sha256": restart_selection.sha256_file(after_path),
    })
    (evidence_root / "restart-readback.completed.json").write_text(json.dumps(proof))
    state = tmp_path / "supervisor"
    state.mkdir()
    restart_reference = finalization.restart_reference(
        state, {"registry_sha256": selection["registry_sha256"]},
        {"release": f"/release/{selection['release_sha']}", "sha256": after["run_identity"]["epoch_sha256"]},
    )
    assert restart_reference["status"] == "completed"
    assert restart_reference["after"]["content_sha256"] == proof["after_sha256"]
    after_path.write_text(after_path.read_text() + " ")
    with pytest.raises(RuntimeError, match="restart_readback_proof_invalid"):
        finalization.restart_reference(
            state, {"registry_sha256": selection["registry_sha256"]},
            {"release": f"/release/{selection['release_sha']}",
             "sha256": after["run_identity"]["epoch_sha256"]},
        )
    after["banks"][0]["sources"][0]["facts"]["invalidated"] = []
    with pytest.raises(RuntimeError, match="fact_set_or_state_mismatch"):
        restart_readback.compare(before, after, selection)
    null_context_selection = json.loads(json.dumps(selection))
    null_context_selection["banks"][0]["sources"][0]["context_sha256"] = None
    context = None
    null_context = asyncio.run(restart_readback.capture(null_context_selection, FakeHTTP(), {
        "release_sha": selection["release_sha"], "registry_sha256": selection["registry_sha256"],
        "epoch_sha256": selection["before_epoch_sha256"],
    }))
    assert null_context["banks"][0]["sources"][0]["context_sha256"] is None
    assert null_context["banks"][0]["scope_eligibility"][0]["positive_ids"] == sorted(positives)


def test_restart_selection_rejects_missing_or_empty_frozen_scope(tmp_path):
    selection = tmp_path / "selection.json"
    selection.write_text(json.dumps({"schema": 1, "banks": []}))
    with pytest.raises(RuntimeError, match="selection_invalid"):
        restart_readback.read_selection(selection)


@pytest.mark.parametrize(
    "page,error",
    [
        ({"items": [], "total": True, "limit": 100, "offset": 0}, "pagination_invalid"),
        ({"items": [], "total": -1, "limit": 100, "offset": 0}, "pagination_invalid"),
        ({"items": [None], "total": 1, "limit": 100, "offset": 0}, "memory_identity_invalid"),
        ({"items": [{"id": ""}], "total": 1, "limit": 100, "offset": 0}, "memory_identity_invalid"),
        ({"items": [{"id": "x"}, {"id": "x"}], "total": 2, "limit": 100, "offset": 0}, "duplicate_memory_id"),
    ],
)
def test_restart_pages_reject_invalid_totals_memory_rows_and_duplicate_ids(page, error):
    class FakeHTTP:
        async def request(self, *_args, **_kwargs):
            return page

    with pytest.raises(RuntimeError, match=error):
        asyncio.run(restart_readback.pages(FakeHTTP(), "bank", "valid"))


def test_restart_pages_reject_duplicate_ids_across_pages():
    class FakeHTTP:
        async def request(self, _method, _path, *, params=None, **_kwargs):
            offset = params["offset"]
            if offset == 0:
                return {"items": [{"id": f"id-{index}"} for index in range(100)],
                        "total": 101, "limit": 100, "offset": 0}
            return {"items": [{"id": "id-0"}], "total": 101, "limit": 100, "offset": 100}

    with pytest.raises(RuntimeError, match="duplicate_memory_id"):
        asyncio.run(restart_readback.pages(FakeHTTP(), "bank", "valid"))


def test_restart_selection_rejects_duplicate_id_across_valid_and_invalidated_states():
    with pytest.raises(RuntimeError, match="memory_in_both_states"):
        restart_readback.index_memory_states([{"id": "same"}], [{"id": "same"}])


def test_fact_projection_preserves_pinned_empty_context_and_date_serialization():
    projection = restart_readback.fact_projection({
        "id": "fact", "context": "", "date": "", "tags": [],
        "source_memory_ids": [], "fact_type": "world", "metadata": {},
        "proof_count": 1,
    }, digest("fact text"), "valid", restart_readback.canonical_entities_sha256([]))
    assert projection["context_sha256"] == digest("")
    assert projection["date"] == ""


@pytest.mark.parametrize(
    "detail,error",
    [
        (None, "identity_source_state_mismatch"),
        ({"id": "other", "document_id": "source", "state": "valid",
          "text": "fact", "entities": ["Name"]}, "identity_source_state_mismatch"),
        ({"id": "fact", "document_id": "other-source", "state": "valid",
          "text": "fact", "entities": ["Name"]}, "identity_source_state_mismatch"),
        ({"id": "fact", "document_id": "source", "state": "invalidated",
          "text": "fact", "entities": ["Name"]}, "identity_source_state_mismatch"),
        ({"id": "fact", "document_id": "source", "state": "valid",
          "text": "different", "entities": ["Name"]}, "identity_source_state_mismatch"),
        ({"id": "fact", "document_id": "source", "state": "valid",
          "text": "fact", "entities": "Name, Other"}, "entities_invalid"),
        ({"id": "fact", "document_id": "source", "state": "valid",
          "text": "fact"}, "entities_invalid"),
        ({"id": "fact", "document_id": "source", "state": "valid",
          "text": "fact", "entities": ["", "Name"]}, "entities_invalid"),
        ({"id": "fact", "document_id": "source", "state": "valid",
          "text": "fact", "entities": ["Name", 1]}, "entities_invalid"),
    ],
)
def test_restart_fact_detail_rejects_malformed_or_mismatched_readback(detail, error):
    class FakeHTTP:
        async def request(self, *_args, **_kwargs):
            return detail

    with pytest.raises(RuntimeError, match=error):
        asyncio.run(restart_readback.fact_entities(
            FakeHTTP(), "bank", "source", "fact", "valid", digest("fact")
        ))
