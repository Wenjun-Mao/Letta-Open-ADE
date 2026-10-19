"""A stopped or unsupervised activation cannot launch new candidate containers."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from workflows.evals.hindsight_integration.operations import Lease, create_record
from workflows.evals.hindsight_integration import startup


def candidate(tmp_path, monkeypatch):
    lease = Lease(
        "ade-hindsight-integration-new",
        "1831ee6d-4e95-45c3-a0bb-1bf3ad4bbacd",
        "a" * 40,
        100,
        3700,
        7300,
        "/mnt/projects",
        (),
    )
    root = tmp_path / "activation"
    lease.save(root)
    create_record(
        root / "checks" / "001.json",
        {
            "activation_id": lease.activation_id,
            "source_revision": lease.source_revision,
            "issues": [],
            "time": 101,
        },
    )
    environment = tmp_path / "private.env"
    environment.write_text("synthetic-only")
    create_record(
        root / "provisioned.json",
        {
            "activation_id": lease.activation_id,
            "environment_path": str(environment.resolve()),
            "environment_sha256": hashlib.sha256(environment.read_bytes()).hexdigest(),
        },
    )
    monkeypatch.setattr(
        startup,
        "DockerOperations",
        lambda: SimpleNamespace(
            snapshot=lambda identities=None: [],
            owned=lambda lease: [],
        ),
    )
    monkeypatch.setattr(
        startup,
        "resources",
        lambda _: {
            "available_ram": 20 * 1024**3,
            "free_disk": 50 * 1024**3,
        },
    )
    monkeypatch.setattr(startup.time, "time", lambda: 102)
    return root, environment


@pytest.mark.parametrize("fault", ["closed", "stale", "config", "wrong_source"])
def test_bad_activation_never_invokes_compose(tmp_path, monkeypatch, fault):
    root, environment = candidate(tmp_path, monkeypatch)
    if fault == "closed":
        create_record(root / "closed.json", {})
    elif fault == "stale":
        monkeypatch.setattr(startup.time, "time", lambda: 200)
    elif fault == "config":
        environment.write_text("changed")
    else:
        path = root / "checks" / "001.json"
        check = json.loads(path.read_bytes())
        check["source_revision"] = "b" * 40
        path.write_text(json.dumps(check))
    calls = []
    monkeypatch.setattr(startup.subprocess, "run", lambda *a, **kw: calls.append(a))
    with pytest.raises(ValueError):
        startup.start_native(root, environment)
    assert calls == []


def test_healthy_candidate_starts_exact_native_services(tmp_path, monkeypatch):
    root, environment = candidate(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(startup.subprocess, "run", lambda *a, **kw: calls.append(a))
    startup.start_native(root, environment)
    assert len(calls) == 1
    assert calls[0][0][-5:] == ["up", "-d", "db", "model-router", "hindsight"]


def test_closure_during_startup_stops_owned_new_containers(tmp_path, monkeypatch):
    root, environment = candidate(tmp_path, monkeypatch)

    def close(*args, **kwargs):
        create_record(root / "closed.json", {})

    stops = []
    monkeypatch.setattr(startup.subprocess, "run", close)
    monkeypatch.setattr(startup, "stop_owned", lambda *a, **kw: stops.append(kw))
    with pytest.raises(ValueError, match="closed during"):
        startup.start_native(root, environment)
    assert stops[0]["reason"] == "startup_failed"


def test_product_start_migrates_only_owned_ade_database_before_inference_services(
    tmp_path, monkeypatch
):
    root, environment = candidate(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(
        startup.subprocess, "run", lambda command, **kw: calls.append(command)
    )
    startup.start_product(root, environment)
    assert len(calls) == 3
    assert calls[0][-1] == "ade-db" and "--wait" in calls[0]
    assert calls[1][-4:] == ["run", "--rm", "--no-deps", "ade-migrate"]
    assert calls[2][-7:] == [
        "db",
        "model-router",
        "hindsight",
        "fault-proxy",
        "ade-api",
        "ade-worker",
        "ade-web",
    ]
    assert all("--profile" in command and "product" in command for command in calls)


def test_product_migration_failure_closes_owned_stack_without_starting_inference(
    tmp_path, monkeypatch
):
    root, environment = candidate(tmp_path, monkeypatch)
    calls, stops = [], []

    def run(command, **kw):
        calls.append(command)
        if command[-1] == "ade-migrate":
            raise RuntimeError("controlled migration failure")

    monkeypatch.setattr(startup.subprocess, "run", run)
    monkeypatch.setattr(startup, "stop_owned", lambda *a, **kw: stops.append(kw))
    with pytest.raises(RuntimeError, match="migration failure"):
        startup.start_product(root, environment)
    assert len(calls) == 2 and stops[0]["reason"] == "startup_failed"
