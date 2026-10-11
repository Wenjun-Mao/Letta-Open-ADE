"""Exact registration filename selectors for main and restore-owned jobs."""

import json

import pytest

from workflows.evals.hindsight_memory_probe import restore, restore_process


def test_main_job_selector_ignores_terminal_result_and_still_blocks_live_registration(
    tmp_path, monkeypatch
):
    token = "a" * 32
    (tmp_path / f"job-{token}.json").write_text(json.dumps({"token": token}))
    (tmp_path / f"job-{token}.result.json").write_text(json.dumps({"exit_code": 1}))
    monkeypatch.setattr(restore.host, "containers", lambda: [])
    monkeypatch.setattr(restore.host, "candidate_containers", lambda *_: [])
    monkeypatch.setattr(
        restore.epochs, "effective_registry", lambda _directory, registry: registry
    )
    monkeypatch.setattr(
        restore.host,
        "host_sample",
        lambda *_: {
            "memory_available": 20 * restore.host.GIB,
            "cpus": 4,
            "disk_free": 50 * restore.host.GIB,
        },
    )
    monkeypatch.setattr(
        restore.host,
        "tagged_processes",
        lambda found: [{"pid": 1}] if found == token else [],
    )

    with pytest.raises(RuntimeError, match="restore_main_registered_process_active"):
        restore._verify_host(
            tmp_path, {"baseline": []}, {"containers": []}, prospective=False
        )


def test_main_job_selector_fails_closed_on_malformed_registration(
    tmp_path, monkeypatch
):
    token = "b" * 32
    (tmp_path / f"job-{token}.json").write_text("{")
    monkeypatch.setattr(restore.host, "containers", lambda: [])
    monkeypatch.setattr(restore.host, "candidate_containers", lambda *_: [])
    monkeypatch.setattr(
        restore.epochs, "effective_registry", lambda _directory, registry: registry
    )
    with pytest.raises(json.JSONDecodeError):
        restore._verify_host(
            tmp_path, {"baseline": []}, {"containers": []}, prospective=False
        )


def test_restore_job_selector_ignores_tokenless_result_files_and_keeps_owned_jobs(
    tmp_path,
):
    operation_token = "c" * 32
    process_token = "d" * 32
    registration = {
        "schema": 1,
        "token": process_token,
        "operation_token": operation_token,
    }
    (tmp_path / f"restore-{operation_token}-{process_token}-job.json").write_text(
        json.dumps(registration)
    )
    (tmp_path / f"job-{process_token}.result.json").write_text(
        json.dumps({"exit_code": 1})
    )

    assert restore_process.registered_jobs(tmp_path, operation_token) == [registration]

    (tmp_path / f"restore-{operation_token}-{process_token}-job.json").write_text("{}")
    with pytest.raises(RuntimeError, match="registration_invalid"):
        restore_process.registered_jobs(tmp_path, operation_token)


def test_restore_container_uses_the_host_ownership_inventory_during_create(tmp_path, monkeypatch):
    from workflows.evals.hindsight_memory_probe import restore_database as db

    token = "e" * 32
    project = db.project_for(token)
    volume = db.volume_for(project)
    operation = {"token": token, "state_directory": str(tmp_path), "compose": {
        "project": project, "volume": volume, "path": str(tmp_path / "compose.yaml"),
        "source_image": "ade-hindsight-probe-db:test", "source_image_id": "sha256:" + "a" * 64}}
    (tmp_path / "restore-operation.json").write_text(json.dumps(operation))
    row = {"Id": "f" * 64, "Image": "sha256:" + "a" * 64,
        "Config": {"Image": operation["compose"]["source_image"], "Env": [], "Labels": {
            "ade.hindsight.restore.token": token, "com.docker.compose.project": project,
            "com.docker.compose.service": "db", "com.docker.compose.project.config_files": operation["compose"]["path"],
            "com.docker.compose.project.working_dir": str(tmp_path)}},
        "State": {"StartedAt": "2026-10-11T12:51:11Z", "Status": "running"},
        "HostConfig": {"NetworkMode": "none", "Memory": db.RESTORE_MEMORY,
                       "NanoCpus": int(db.RESTORE_CPU * 1_000_000_000)},
        "NetworkSettings": {"Ports": {}}, "Mounts": [{"Name": volume, "Destination": db.DATA_PATH, "RW": True}]}
    monkeypatch.setattr(db, "docker_text", lambda *_args, **_kwargs: pytest.fail("must not resample Docker"))
    monkeypatch.setattr(db, "docker_json", lambda *_args, **_kwargs: pytest.fail("must not resample Docker"))

    assert db.restore_container(operation, allow_unregistered=True, inventory=[row]) == row
