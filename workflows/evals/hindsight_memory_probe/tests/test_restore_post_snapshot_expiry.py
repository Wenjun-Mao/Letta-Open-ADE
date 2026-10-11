"""The detached failed-restore expiry guard is bound to one immutable attempt."""

import hashlib
import json
import os
import time
from types import SimpleNamespace

import pytest

from workflows.evals.hindsight_memory_probe import restore_post_snapshot_expiry as expiry
from workflows.evals.hindsight_memory_probe.restore_post_snapshot_contract import SCOPES


def _authority(state, *, container_id="c" * 64):
    token = "a" * 32
    operation = {"token": token, "compose": {"volume": "restore-volume", "project": "restore-project",
                                              "source_image_id": "image-id"}}
    operation_bytes = json.dumps(operation).encode()
    (state / "restore-operation.json").write_bytes(operation_bytes)
    (state / "restore-operation-seal.json").write_text(json.dumps({
        "sha256": hashlib.sha256(operation_bytes).hexdigest()
    }))
    (state / f"restore-{token}-failure.result.json").write_text('{"status":"failed"}')
    (state / f"restore-{token}-cleanup.result.json").write_text('{"status":"preserved_failed_state"}')
    (state / f"restore-{token}-create.result.json").write_text(json.dumps({"container_id": container_id}))
    failure = state / f"restore-{token}-failure.result.json"
    cleanup = state / f"restore-{token}-cleanup.result.json"
    authority = {
        "schema": 1, "kind": "failed_post_restore_snapshot_recovery",
        "admission_token": "b" * 32, "token": token,
        "operation_sha256": hashlib.sha256(operation_bytes).hexdigest(),
        "failure_sha256": hashlib.sha256(failure.read_bytes()).hexdigest(),
        "cleanup_sha256": hashlib.sha256(cleanup.read_bytes()).hexdigest(),
        "container_id": container_id, "volume": "restore-volume",
        "recovery_source_sha": "d" * 40, "issued_at": time.time(),
        "deadline": time.time() + 30, "scopes": SCOPES,
    }
    path = state / f"restore-{token}-post-restore-authority-{'b' * 32}.json"
    path.write_text(json.dumps(authority))
    path.chmod(0o400)
    return token, path, authority


def _container(*, status="exited", project="restore-project", started_at="new-start"):
    return {"Id": "c" * 64, "Image": "image-id", "RestartCount": 0,
            "Config": {"Labels": {"ade.hindsight.restore.token": "a" * 32,
                                    "com.docker.compose.project": project}},
            "Mounts": [{"Name": "restore-volume"}],
            "State": {"Status": status, "StartedAt": started_at, "OOMKilled": False}}


def test_expiry_authority_is_bound_to_original_create_container(tmp_path):
    token, authority_path, authority = _authority(tmp_path)
    value = expiry._read_authority(tmp_path, token, authority_path.name,
                                   hashlib.sha256(authority_path.read_bytes()).hexdigest())
    assert value["container_id"] == authority["container_id"]

    create_path = tmp_path / f"restore-{token}-create.result.json"
    create_path.write_text('{"container_id":"different-container"}')
    with pytest.raises(RuntimeError, match="authority_invalid"):
        expiry._read_authority(tmp_path, token, authority_path.name,
                               hashlib.sha256(authority_path.read_bytes()).hexdigest())


def test_expiry_stops_the_exact_id_even_if_configuration_drifted(tmp_path, monkeypatch):
    calls = []
    row = _container(status="running", project="unexpected")

    def run(command, **kwargs):
        calls.append(command)
        if command[1] == "stop":
            row["State"]["Status"] = "exited"
        return SimpleNamespace(stdout=json.dumps([row]).encode())

    monkeypatch.setattr(expiry.subprocess, "run", run)
    result = expiry._stop_exact("c" * 64, "b" * 32, {
        "operation_token": "a" * 32, "project": "restore-project", "image_id": "image-id",
        "volume": "restore-volume", "started_at": "original-start",
    })

    assert [command[1] for command in calls] == ["inspect", "stop", "inspect"]
    assert result["status"] == "drifted_container_stopped"
    assert result["container_id"] == "c" * 64
    assert result["container_status"] == "exited"


def test_expiry_cancellation_requires_exact_restarted_container_stopped(tmp_path, monkeypatch):
    token, authority_path, _authority_value = _authority(tmp_path)
    row = _container()
    monkeypatch.setattr(expiry, "_cancelled", True)
    monkeypatch.setattr(expiry.subprocess, "run", lambda *_args, **_kwargs:
                        SimpleNamespace(stdout=json.dumps([row]).encode()))
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"1")
    os.close(write_fd)
    try:
        assert expiry.run(tmp_path, token, authority_path.name, "c" * 64, "original-start",
                          _authority_value["deadline"],
                          hashlib.sha256(authority_path.read_bytes()).hexdigest(),
                          "b" * 32, read_fd) == 0
    finally:
        monkeypatch.setattr(expiry, "_cancelled", False)
    result = json.loads((tmp_path / f"restore-{token}-{'b' * 32}-expiry.result.json").read_text())
    assert result["status"] == "cancelled_after_database_stop"
    assert result["container_status"] == "exited"


def test_expiry_cancellation_does_not_claim_a_running_database_stopped(tmp_path, monkeypatch):
    token, authority_path, authority_value = _authority(tmp_path)
    row = _container(status="running")
    monkeypatch.setattr(expiry, "_cancelled", True)
    monkeypatch.setattr(expiry.subprocess, "run", lambda *_args, **_kwargs:
                        SimpleNamespace(stdout=json.dumps([row]).encode()))
    read_fd, write_fd = os.pipe()
    os.write(write_fd, b"1")
    os.close(write_fd)
    try:
        with pytest.raises(RuntimeError, match="cancel_stop_unproven"):
            expiry.run(tmp_path, token, authority_path.name, "c" * 64, "original-start",
                       authority_value["deadline"],
                       hashlib.sha256(authority_path.read_bytes()).hexdigest(),
                       "b" * 32, read_fd)
    finally:
        monkeypatch.setattr(expiry, "_cancelled", False)
