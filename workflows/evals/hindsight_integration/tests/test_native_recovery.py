"""Recovery proofs require actual terminal failure and unchanged operation/source IDs."""

import asyncio
import json
import time

import pytest

from workflows.evals.hindsight_integration import native_recovery as recovery
from workflows.evals.hindsight_integration.operations import Lease


class NativeFake:
    instances = []
    partial = False
    corrupt_prefix = False
    early_success = False

    def __init__(self, **kwargs):
        self.polls = 0
        self.retried = False
        self.submitted = []
        self.instances.append(self)

    async def create_bank(self, *args, **kwargs):
        pass

    async def configure_bank(self, bank, config):
        self.config = config

    async def submit(self, bank, *, operation_id, payload):
        self.submitted.append((operation_id, payload))
        self.payload = json.loads(payload)

    async def operation(self, bank, operation):
        self.polls += 1
        status = (
            "completed"
            if self.retried or self.early_success
            else ("processing" if self.partial and self.polls == 1 else "failed")
        )
        return {"status": status, "operation_id": operation}

    async def memories(self, bank, *, offset=0):
        if self.retried:
            ids = ["prefix", "finished"] if not self.corrupt_prefix else ["finished"]
        elif self.polls and self.partial:
            ids = ["prefix"]
        else:
            ids = []
        return {"items": [{"id": identity} for identity in ids], "total": len(ids)}

    async def operations(self, bank):
        return {"operations": [{"id": "parent"}, {"id": "child"}], "total": 2}

    async def retry_operation(self, bank, operation):
        assert operation == self.submitted[0][0]
        self.retried = True

    async def document(self, bank, document):
        item = self.payload["items"][0]
        assert item["document_id"] == document
        return {
            "original_text": item["content"],
            "retain_params": {"context": item["context"]},
        }


@pytest.fixture
def native(monkeypatch):
    now = int(time.time())
    lease = Lease(
        "ade-hindsight-integration-test",
        "9f28b42c-cce1-40f1-9c64-41ecc22215d5",
        "a" * 40,
        now,
        now + 3600,
        now + 7200,
        "/mnt/projects",
        (),
    )
    monkeypatch.setattr(recovery.Lease, "load", lambda _: lease)
    monkeypatch.setenv("ADE_INTEGRATION_SOURCE_REVISION", lease.source_revision)
    monkeypatch.setenv("ADE_INTEGRATION_HINDSIGHT_URL", "http://never-called")
    monkeypatch.setenv("ADE_INTEGRATION_HINDSIGHT_KEY", "synthetic")
    monkeypatch.setattr(recovery, "HindsightClient", NativeFake)
    monkeypatch.setattr(NativeFake, "instances", [])
    monkeypatch.setattr(NativeFake, "partial", False)
    monkeypatch.setattr(NativeFake, "corrupt_prefix", False)
    monkeypatch.setattr(NativeFake, "early_success", False)

    async def restored(*args, **kwargs):
        return {"activation_id": lease.activation_id}

    monkeypatch.setattr(recovery, "wait_file", restored)
    return lease


@pytest.mark.parametrize("partial", [False, True])
def test_native_retry_reuses_operation_and_preserves_committed_prefix(
    tmp_path, monkeypatch, native, partial
):
    monkeypatch.setattr(NativeFake, "partial", partial)
    result = asyncio.run(recovery.run_recovery(tmp_path, partial=partial, timeout=30))
    assert result["mechanical_status"] == "passed"
    client = NativeFake.instances[0]
    assert len(client.submitted) == 1
    plan = json.loads((tmp_path / "plan.json").read_bytes())
    assert json.loads(client.submitted[0][1]) == plan["payload"]
    assert client.submitted[0][0] == plan["operation_id"]
    assert result["partial_memories_preserved"] == int(partial)
    assert client.config["enable_auto_consolidation"] is False
    assert (tmp_path / "fault-ready.json").exists() == partial


def test_a_successful_operation_is_not_failure_recovery(tmp_path, monkeypatch, native):
    monkeypatch.setattr(NativeFake, "early_success", True)
    result = asyncio.run(recovery.run_recovery(tmp_path, partial=False, timeout=30))
    assert result["mechanical_status"] == "failed"
    assert "genuine failed" in result["error"]
    assert NativeFake.instances[0].retried is False


def test_a_partial_retry_cannot_discard_previously_committed_ids(
    tmp_path, monkeypatch, native
):
    monkeypatch.setattr(NativeFake, "partial", True)
    monkeypatch.setattr(NativeFake, "corrupt_prefix", True)
    result = asyncio.run(recovery.run_recovery(tmp_path, partial=True, timeout=30))
    assert result["mechanical_status"] == "failed"
    assert "lost already committed" in result["error"]


def test_diagnostic_chunking_does_not_truncate_the_immutable_source():
    _, source = recovery.recovery_source(True)
    assert len(source.content) > 2500
    assert "AX-001" in source.content and "AX-040" in source.content
    assert source.status == "accepted"
