"""Closed parent identity, source volume ownership and bounded resource commands."""

import copy
import json
import time
from uuid import uuid4

import pytest

from .. import stopped_stores as stores
from ..operations import Lease, OWNER_LABEL, PROJECT_LABEL, SOURCE_LABEL, create_record


@pytest.fixture
def parent(tmp_path):
    now = int(time.time())
    root = tmp_path / "closed"
    lease = Lease(
        "ade-hindsight-integration-closed",
        str(uuid4()),
        "a" * 40,
        now - 7200,
        now - 3600,
        now,
        "/mnt/projects",
        (),
    )
    lease.save(root)
    checkpoint = root / "evidence/paired-failed"
    labels = {
        PROJECT_LABEL: lease.project,
        OWNER_LABEL: lease.activation_id,
        SOURCE_LABEL: lease.source_revision,
    }
    rows, volumes = [], {}
    for name, service in (
        ("ade-data", "ade-db"),
        ("hindsight-data", "db"),
        (None, "model-router"),
    ):
        mounts = []
        if name:
            volume = lease.project + "_" + name
            mounts = [
                {
                    "Type": "volume",
                    "Name": volume,
                    "Destination": "/var/lib/postgresql/data",
                    "RW": True,
                }
            ]
            volumes[volume] = {
                "Name": volume,
                "Driver": "local",
                "Options": None,
                "Labels": {**labels, "com.docker.compose.volume": name},
            }
        rows.append(
            {
                "id": service,
                "state": "exited",
                "image": "sha256:" + "b" * 64,
                "auto_remove": False,
                "mounts": mounts,
                "labels": {**labels, "com.docker.compose.service": service},
            }
        )
    point = copy.deepcopy(rows)
    for row in point[:2]:
        row["state"] = "running"
    create_record(
        root / "closed.json", {"activation_id": lease.activation_id, "time": now}
    )
    create_record(
        checkpoint / "plan.json",
        {
            "activation_id": lease.activation_id,
            "product_revision": lease.source_revision,
        },
    )
    create_record(
        checkpoint / "closeout.json",
        {"baseline_unchanged": True, "running_owned": [], "stop_failures": []},
    )
    create_record(
        checkpoint / "no-writers.json",
        {
            "owned": point,
            "time": now - 1,
            "native_progress": {"pending": ["kept-operation"], "incomplete_banks": []},
            "ade_migration_head": "head",
        },
    )

    class Docker:
        extra = []

        def owned(self, _lease):
            return rows

        def snapshot(self):
            return rows + self.extra

        def _run(self, command):
            assert command[:2] == ["volume", "inspect"]
            return json.dumps([volumes[command[2]]])

    return root, checkpoint, lease, rows, volumes, Docker()


def test_exact_closed_point_preserves_operations_and_source_bindings(parent):
    root, checkpoint, lease, _, _, docker = parent
    bound = stores.bind_parent(root, checkpoint, docker)
    assert bound["source_revision"] == lease.source_revision
    assert bound["native_progress"]["pending"] == ["kept-operation"]
    assert len(bound["files"]) == 6 and len(bound["stores"]) == 2
    assert all(row["image_id"].startswith("sha256:") for row in bound["stores"])


@pytest.mark.parametrize(
    "fault",
    [
        "active",
        "oom",
        "image",
        "mount",
        "volume_owner",
        "volume_driver",
        "volume_options",
        "external",
        "restarted",
    ],
)
def test_changed_unowned_or_active_store_is_refused_before_copy(parent, fault):
    root, checkpoint, _, rows, volumes, docker = parent
    if fault == "active":
        rows[0]["state"] = "running"
    elif fault == "oom":
        rows[0]["oom"] = True
    elif fault == "image":
        rows[0]["image"] = "sha256:" + "d" * 64
    elif fault == "mount":
        rows[0]["mounts"][0]["Name"] = "unowned"
    elif fault == "volume_owner":
        next(iter(volumes.values()))["Labels"][OWNER_LABEL] = str(uuid4())
    elif fault == "volume_driver":
        next(iter(volumes.values()))["Driver"] = "remote"
    elif fault == "volume_options":
        next(iter(volumes.values()))["Options"] = {"device": "/outside"}
    elif fault == "restarted":
        rows[0]["started_at"] = "changed-after-checkpoint"
    else:
        docker.extra = [{**rows[0], "id": "foreign", "state": "running"}]
    with pytest.raises(ValueError):
        stores.bind_parent(root, checkpoint, docker)


@pytest.mark.parametrize("writable", [True, False])
def test_only_registered_readonly_helper_may_read_source_while_copying(
    parent, writable
):
    root, checkpoint, _, rows, _, docker = parent
    now = int(time.time())
    lease = Lease(
        "ade-hindsight-integration-new",
        str(uuid4()),
        "c" * 40,
        now - 1,
        now + 3600,
        now + 7200,
        "/mnt/projects",
        (),
    )
    helper = copy.deepcopy(rows[0])
    helper.update(
        id="new-copy",
        state="running",
        labels={
            PROJECT_LABEL: lease.project,
            OWNER_LABEL: lease.activation_id,
            SOURCE_LABEL: lease.source_revision,
            "com.docker.compose.service": "ade-copy",
        },
    )
    helper["mounts"][0].update(RW=writable, Destination="/source")
    docker.extra = [helper]
    if writable:
        with pytest.raises(ValueError, match="active_dependent"):
            stores.bind_parent(root, checkpoint, docker, copy_lease=lease)
    else:
        assert stores.bind_parent(root, checkpoint, docker, copy_lease=lease)["stores"]
        with pytest.raises(ValueError, match="active_dependent"):
            stores.bind_parent(root, checkpoint, docker)


def test_copy_creation_uses_only_new_volume_readonly_source_exact_image_and_no_network(
    tmp_path, monkeypatch
):
    now = int(time.time())
    lease = Lease(
        "ade-hindsight-integration-new",
        str(uuid4()),
        "c" * 40,
        now - 1,
        now + 3600,
        now + 7200,
        "/mnt/projects",
        (),
    )
    calls = []

    class Docker:
        def _run(self, command):
            calls.append(command)
            return "d" * 64 if command[0] == "create" else ""

    binding = {"copy_image_id": "sha256:" + "e" * 64}
    resources = stores.CopyResources(
        tmp_path, lease, Docker(), tmp_path, tmp_path, binding
    )
    monkeypatch.setattr(resources, "fence", lambda: None)
    monkeypatch.setattr(resources, "wait", lambda *args, **kwargs: None)
    rows = [{"path": "PG_VERSION", "sha256": "controlled"}]
    create_record(
        tmp_path / "copy.json",
        {
            "source_unchanged": True,
            "copy_verified": True,
            "source_before": rows,
            "source_after": rows,
            "target_before_startup": rows,
        },
    )
    target, identity = resources.copy(
        {"store": "ade", "volume": "parent-only"}, tmp_path
    )
    assert target == lease.project + "_ade-copy" and identity == "d" * 64
    command = next(command for command in calls if command[0] == "create")
    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--pull") + 1] == "never"
    assert command[command.index("--memory") + 1] == "3g"
    assert command[command.index("--memory-swap") + 1] == "3g"
    assert (
        "type=volume,source=parent-only,target=/source,readonly,volume-nocopy"
        in command
    )
    assert command[command.index(binding["copy_image_id"]) + 1] == "/copy.py"
    assert "--rm" not in command and "--publish" not in command
