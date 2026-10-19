"""Bind closed-parent database stores and create only new owned copy resources."""

import hashlib
import json
from pathlib import Path
import re
import time

from .native_faults import healthy_lease
from .operations import Lease, OWNER_LABEL, PROJECT_LABEL, SOURCE_LABEL
from .paired_backup import owned_service


ACTIVE = {"running", "restarting", "paused"}
STORES = {
    "ade": ("ade-db", "ade-data", "ade_integration_admin", "ade_integration"),
    "hindsight": (
        "db",
        "hindsight-data",
        "hindsight_integration",
        "hindsight_integration",
    ),
}


def file_binding(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def source_volume(docker, lease, row, volume):
    mounts = [
        mount
        for mount in row["mounts"]
        if mount["Destination"] == "/var/lib/postgresql/data"
    ]
    expected = lease.project + "_" + volume
    if len(mounts) != 1 or (
        mounts[0].get("Type") != "volume" or mounts[0].get("Name") != expected
    ):
        raise ValueError("closed_parent_database_volume_mismatch")
    records = json.loads(docker._run(["volume", "inspect", expected]))
    if len(records) != 1:
        raise ValueError("closed_parent_volume_inspection_mismatch")
    record = records[0]
    labels = record.get("Labels") or {}
    if (
        record.get("Name") != expected
        or record.get("Driver") != "local"
        or record.get("Options")
        or labels.get(PROJECT_LABEL) != lease.project
        or labels.get(OWNER_LABEL) != lease.activation_id
        or labels.get(SOURCE_LABEL) != lease.source_revision
        or labels.get("com.docker.compose.volume") != volume
    ):
        raise ValueError("closed_parent_volume_ownership_mismatch")
    return expected


def bind_parent(parent, checkpoint, docker, *, copy_lease=None):
    lease = Lease.load(parent)
    closed = json.loads((parent / "closed.json").read_bytes())
    closeout = json.loads((checkpoint / "closeout.json").read_bytes())
    point = json.loads((checkpoint / "no-writers.json").read_bytes())
    plan = json.loads((checkpoint / "plan.json").read_bytes())
    if (
        closed.get("activation_id") != lease.activation_id
        or plan.get("activation_id") != lease.activation_id
        or plan.get("product_revision") != lease.source_revision
        or not point["time"] <= closed["time"]
        or closeout.get("baseline_unchanged") is not True
        or closeout.get("running_owned") != []
        or closeout.get("stop_failures") != []
    ):
        raise ValueError("parent_checkpoint_not_closed_and_quiescent")
    original = docker.owned(lease)
    if any(row["state"] != "exited" or row.get("oom") for row in original):
        raise ValueError("closed_parent_not_stopped")
    previous_owned = {row["id"]: row for row in point["owned"]}
    stable = ("id", "image", "mounts", "labels", "started_at", "restarts")
    if set(previous_owned) != {row["id"] for row in original} or any(
        any(row.get(key) != previous_owned[row["id"]].get(key) for key in stable)
        for row in original
    ):
        raise ValueError("closed_parent_changed_since_checkpoint")
    stores = []
    for name, (service, volume, user, database) in STORES.items():
        row = owned_service(docker, lease, service)
        previous = [item for item in point["owned"] if item["id"] == row["id"]]
        if len(previous) != 1 or any(
            row[key] != previous[0][key] for key in ("id", "image", "mounts", "labels")
        ):
            raise ValueError("closed_parent_database_changed_since_checkpoint")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", row["image"]):
            raise ValueError("closed_parent_database_image_not_immutable")
        stores.append(
            {
                "store": name,
                "container_id": row["id"],
                "image_id": row["image"],
                "volume": source_volume(docker, lease, row, volume),
                "user": user,
                "database": database,
            }
        )
    if any(
        row["state"] in ACTIVE
        and row["labels"].get("com.docker.compose.service") not in {"db", "ade-db"}
        for row in point["owned"]
    ):
        raise ValueError("parent_checkpoint_contains_active_writers")
    volumes = {store["volume"] for store in stores}
    router = owned_service(docker, lease, "model-router")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", router["image"]):
        raise ValueError("closed_parent_copy_image_not_immutable")
    for row in docker.snapshot():
        used = [
            mount for mount in row.get("mounts", []) if mount.get("Name") in volumes
        ]
        if row["state"] not in ACTIVE or not used:
            continue
        if (
            copy_lease is None
            or not copy_lease.owns(row)
            or row["image"] != router["image"]
            or row["labels"].get("com.docker.compose.service")
            not in {"ade-copy", "hindsight-copy"}
            or any(
                mount.get("RW") is not False or mount.get("Destination") != "/source"
                for mount in used
            )
        ):
            raise ValueError("parent_volume_has_active_dependent")
    files = [parent / name for name in ("lease.json", "lease.seal.json", "closed.json")]
    files += [
        checkpoint / name for name in ("plan.json", "no-writers.json", "closeout.json")
    ]
    return {
        "activation_id": lease.activation_id,
        "source_revision": lease.source_revision,
        "owned_stopped": original,
        "stores": stores,
        "copy_image_id": router["image"],
        "files": [file_binding(path) for path in files],
        "native_progress": point["native_progress"],
        "ade_migration_head": point["ade_migration_head"],
    }


class CopyResources:
    def __init__(self, root, lease, docker, parent, checkpoint, binding):
        self.root, self.lease, self.docker = root, lease, docker
        self.parent, self.checkpoint, self.binding = parent, checkpoint, binding

    def fence(self):
        healthy_lease(self.root, self.lease, self.docker)
        if (
            bind_parent(
                self.parent, self.checkpoint, self.docker, copy_lease=self.lease
            )
            != self.binding
        ):
            raise ValueError("closed_parent_changed_during_checkpoint")

    def labels(self, service):
        labels = {
            PROJECT_LABEL: self.lease.project,
            OWNER_LABEL: self.lease.activation_id,
            SOURCE_LABEL: self.lease.source_revision,
            "com.docker.compose.service": service,
        }
        return [
            argument
            for key, value in labels.items()
            for argument in ("--label", f"{key}={value}")
        ]

    def create(self, service, image, arguments, command=()):
        self.fence()
        identity = self.docker._run(
            [
                "create",
                "--name",
                f"{self.lease.project}-{service}",
                "--pull",
                "never",
                "--network",
                "none",
                "--restart",
                "no",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "128",
                *self.labels(service),
                *arguments,
                image,
                *command,
            ]
        ).strip()
        if not re.fullmatch(r"[a-f0-9]{64}", identity):
            raise ValueError("copy_container_identity_invalid")
        return identity

    def start(self, identity):
        self.fence()
        self.docker._run(["start", identity])

    def wait(self, identity, *, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.fence()
            rows = self.docker.snapshot([identity])
            if len(rows) != 1:
                raise ValueError("owned_copy_container_missing")
            if rows[0]["state"] == "exited":
                status = self.docker._run(
                    ["inspect", "--format", "{{.State.ExitCode}}", identity]
                ).strip()
                if status != "0":
                    raise RuntimeError("owned_store_copy_failed")
                return
            time.sleep(1)
        raise TimeoutError("owned_store_copy_timeout")

    def copy(self, store, output):
        self.fence()
        target = self.lease.project + "_" + store["store"] + "-copy"
        if target in self.docker._run(["volume", "ls", "-q"]).splitlines():
            raise ValueError("copy_volume_already_exists")
        self.docker._run(
            ["volume", "create", *self.labels(store["store"] + "-copy"), target]
        )
        script = Path(__file__).with_name("copy_stopped_volume.py").resolve()
        identity = self.create(
            store["store"] + "-copy",
            self.binding["copy_image_id"],
            [
                "--cpus",
                "0.25",
                "--memory",
                "3g",
                "--memory-swap",
                "3g",
                "--user",
                "0:0",
                "--entrypoint",
                "python",
                "--mount",
                f"type=volume,source={store['volume']},target=/source,readonly,volume-nocopy",
                "--mount",
                f"type=volume,source={target},target=/target,volume-nocopy",
                "--mount",
                f"type=bind,source={script},target=/copy.py,readonly",
                "--mount",
                f"type=bind,source={output},target=/evidence",
            ],
            [
                "/copy.py",
                "--source",
                "/source",
                "--target",
                "/target",
                "--receipt",
                "/evidence/copy.json",
            ],
        )
        self.start(identity)
        self.wait(identity, timeout=900)
        receipt = json.loads((output / "copy.json").read_bytes())
        if (
            receipt.get("source_unchanged") is not True
            or receipt.get("copy_verified") is not True
            or not receipt.get("source_before")
            or receipt["source_before"] != receipt.get("source_after")
            or receipt["source_before"] != receipt.get("target_before_startup")
        ):
            raise ValueError("copy_receipt_not_verified")
        return target, identity
