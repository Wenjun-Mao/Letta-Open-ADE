"""The fault controller never interrupts baseline or differently bound services."""

import hashlib
from types import SimpleNamespace

import pytest

from workflows.evals.hindsight_integration import native_faults as faults
from workflows.evals.hindsight_integration.operations import (
    Lease,
    OWNER_LABEL,
    PROJECT_LABEL,
    SOURCE_LABEL,
    create_record,
)


@pytest.fixture
def host(tmp_path, monkeypatch):
    root = tmp_path / "activation"
    lease = Lease(
        "ade-hindsight-integration-test",
        "34a2cb5e-bf36-4b94-9650-0ac35d0336fd",
        "a" * 40,
        100,
        3700,
        7300,
        "/mnt/projects",
        (),
    )
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
    environment.write_text("synthetic")
    create_record(
        root / "provisioned.json",
        {
            "activation_id": lease.activation_id,
            "environment_path": str(environment),
            "environment_sha256": hashlib.sha256(environment.read_bytes()).hexdigest(),
        },
    )
    router = {
        "id": "owned-router",
        "state": "running",
        "labels": {
            OWNER_LABEL: lease.activation_id,
            PROJECT_LABEL: lease.project,
            SOURCE_LABEL: lease.source_revision,
            "com.docker.compose.service": "model-router",
        },
    }
    actions = []
    docker = SimpleNamespace(
        snapshot=lambda identities=None: [],
        owned=lambda _: [router],
        stop=lambda identity: actions.append(("stop", identity)),
        _run=lambda arguments: actions.append(tuple(arguments)),
    )
    monkeypatch.setattr(faults, "DockerOperations", lambda: docker)
    monkeypatch.setattr(
        faults,
        "resources",
        lambda _: {
            "available_ram": 20 * 1024**3,
            "free_disk": 50 * 1024**3,
        },
    )
    monkeypatch.setattr(faults.time, "time", lambda: 102)
    return root, environment, router, actions


@pytest.mark.parametrize("invalid", ["source", "config", "closed", "window"])
def test_invalid_fault_scope_never_stops_any_container(host, invalid):
    root, environment, router, actions = host
    if invalid == "source":
        router["labels"][SOURCE_LABEL] = "b" * 40
    elif invalid == "config":
        environment.write_text("changed")
    elif invalid == "closed":
        create_record(root / "closed.json", {})
    with pytest.raises(ValueError):
        faults.run_fault(
            root,
            environment,
            root / "evidence" / "new",
            partial=True,
            timeout=4000 if invalid == "window" else 30,
        )
    assert actions == []


@pytest.mark.parametrize("partial", [False, True])
def test_interruption_and_restore_select_only_the_inspected_owned_router(
    host, monkeypatch, partial
):
    root, environment, router, actions = host
    output = root / "evidence" / "new"
    process = SimpleNamespace(
        returncode=0,
        poll=lambda: 0,
        communicate=lambda **kwargs: ("runner completed", None),
    )
    monkeypatch.setattr(faults.subprocess, "Popen", lambda *a, **kw: process)
    monkeypatch.setattr(faults, "wait_for", lambda *a, **kw: None)

    class HealthyResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(
        faults.urllib.request, "urlopen", lambda *a, **kw: HealthyResponse()
    )
    faults.run_fault(root, environment, output, partial=partial, timeout=30)
    assert actions == [("stop", "owned-router"), ("start", "owned-router")]
    assert (output / "router-restored.json").is_file()
