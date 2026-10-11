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
