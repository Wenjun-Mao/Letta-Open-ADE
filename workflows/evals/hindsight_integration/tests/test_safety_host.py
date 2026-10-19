"""Owned-control state machine and cleanup; no Docker, network or provider use."""

import copy
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from .. import safety_host
from ..operations import create_record


def controls(tmp_path):
    value = safety_host.OwnedControls.__new__(safety_host.OwnedControls)
    value.root, value.lease = tmp_path, SimpleNamespace(source_revision="a" * 40)
    value.changed = []
    value.finalizer = None
    value.isolation = None
    value.events = []
    rows = [
        {
            "id": name,
            "name": "/" + name,
            "image": "sha256:" + "b" * 64,
            "mounts": [{"Source": name + "-private-store"}],
            "state": "running",
            "labels": {
                "com.docker.compose.service": name,
                "io.ade.integration.source": "a" * 40,
            },
        }
        for name in ("hindsight", "ade-api", "ade-worker")
    ]
    value.original = {row["id"]: copy.deepcopy(row) for row in rows}
    value.fence = lambda: None
    value.native_ready = lambda: value.events.append(("ready", "hindsight"))

    class Docker:
        def owned(self, lease):
            return copy.deepcopy(rows)

        def stop(self, identity):
            value.events.append(("stop", identity))
            next(row for row in rows if row["id"] == identity)["state"] = "exited"

        def _run(self, command):
            assert command[0] == "start"
            value.events.append(tuple(command))
            next(row for row in rows if row["id"] == command[1])["state"] = "running"

    value.docker = Docker()
    return value, rows


def test_owned_runtime_restart_keeps_exact_containers_and_stores(tmp_path):
    value, rows = controls(tmp_path)
    after = value.perform("restart-runtime")
    assert value.events == [
        ("stop", "ade-api"),
        ("stop", "ade-worker"),
        ("stop", "hindsight"),
        ("start", "hindsight"),
        ("ready", "hindsight"),
        ("start", "ade-api"),
        ("start", "ade-worker"),
    ]
    assert not value.changed
    assert all(row["state"] == "running" for row in after.values())
    assert {row["image"] for row in rows} == {"sha256:" + "b" * 64}


@pytest.mark.parametrize(
    "field,new", [("id", "foreign-id"), ("image", "foreign-image"), ("mounts", [])]
)
def test_changed_service_identity_is_refused_before_control(tmp_path, field, new):
    value, rows = controls(tmp_path)
    rows[0][field] = new
    with pytest.raises(ValueError):
        value.perform("stop-native")
    assert not value.events


def test_restore_only_restarts_services_this_controller_stopped(tmp_path):
    value, _ = controls(tmp_path)
    value.perform("stop-native")
    value.restore()
    assert value.events == [
        ("stop", "hindsight"),
        ("start", "hindsight"),
        ("ready", "hindsight"),
    ]
    assert not value.changed


@pytest.mark.parametrize(
    "mutation",
    [
        {"action": "start-native"},
        {"details": {"container": "incumbent"}},
        {"product_revision": "b" * 40},
        {"action": "docker-prune"},
    ],
)
def test_rpc_cannot_choose_foreign_resources_or_skip_declared_steps(tmp_path, mutation):
    value, _ = controls(tmp_path)
    plan = {
        "id": str(uuid4()),
        "action": "stop-native",
        "details": {},
        "product_revision": "a" * 40,
        "time": 1,
    }
    plan.update(mutation)
    path = tmp_path / "run/recall-outage/host-requests/0001.json"
    create_record(path, plan)
    with pytest.raises(ValueError):
        safety_host.respond(
            path,
            output=tmp_path,
            controls=value,
            scenarios=["recall-outage"],
            positions={"recall-outage": 0},
        )
    assert not value.events


def test_rpc_records_failure_without_forwarding_exception_details(tmp_path):
    value, _ = controls(tmp_path)

    def failed(action):
        raise OSError("PRIVATE-DIAGNOSTIC-NOT-A-RECEIPT")

    value.perform = failed
    path = tmp_path / "run/recall-outage/host-requests/0001.json"
    create_record(
        path,
        {
            "id": str(uuid4()),
            "action": "stop-native",
            "details": {},
            "product_revision": "a" * 40,
            "time": 1,
        },
    )
    positions = {"recall-outage": 0}
    receipt = safety_host.respond(
        path,
        output=tmp_path,
        controls=value,
        scenarios=["recall-outage"],
        positions=positions,
    )
    assert receipt["status"] == "failed" and receipt["error_type"] == "OSError"
    assert positions == {"recall-outage": 0}
    assert "PRIVATE-DIAGNOSTIC" not in json.dumps(receipt)


def test_child_exit_failure_still_restores_owned_services(tmp_path):
    value, _ = controls(tmp_path)
    restored = []
    value.restore = lambda: restored.append(True)

    class Process:
        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout):
            raise RuntimeError("controlled_wait_failure")

    with pytest.raises(RuntimeError):
        safety_host.finish_owned_child(Process(), value, "owned-runner")
    assert restored == [True]


def test_runner_receipt_must_match_actual_image_id(tmp_path):
    lease = SimpleNamespace(source_revision="a" * 40, activation_id=str(uuid4()))
    image = {
        "role": "runner",
        "image": "owned-runner:revision",
        "image_id": "sha256:" + "b" * 64,
    }
    create_record(
        tmp_path / "images.json",
        {
            "source_revision": lease.source_revision,
            "activation_id": lease.activation_id,
            "images": [image],
        },
    )
    assert (
        safety_host.require_runner_image(
            tmp_path, lease, SimpleNamespace(_run=lambda args: image["image_id"])
        )
        == image
    )
    with pytest.raises(ValueError, match="image_changed"):
        safety_host.require_runner_image(
            tmp_path, lease, SimpleNamespace(_run=lambda args: "sha256:" + "c" * 64)
        )
