"""Recover a writer-free closed checkpoint through new networkless database copies."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import time

from .native_faults import healthy_lease
from .operations import DockerOperations, Lease, create_record, stop_owned
from .paired_backup import dump_database, migration_head_query, sql
from .stopped_stores import ACTIVE, CopyResources, bind_parent, file_binding


def ready(resources, identity, store):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        resources.fence()
        result = subprocess.run(
            [
                "docker",
                "exec",
                identity,
                "pg_isready",
                "-U",
                store["user"],
                "-d",
                store["database"],
            ],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    raise TimeoutError("copied_database_not_ready")


def database_copy(resources, store, volume):
    identity = resources.create(
        store["store"] + "-db",
        store["image_id"],
        [
            "--cpus",
            "0.25",
            "--memory",
            "1g",
            "--memory-swap",
            "1g",
            "--env",
            "PGDATA=/var/lib/postgresql/data",
            "--mount",
            f"type=volume,source={volume},target=/var/lib/postgresql/data,volume-nocopy",
        ],
        [
            "postgres",
            "-c",
            "listen_addresses=",
            "-c",
            "shared_buffers=32MB",
            "-c",
            "max_connections=20",
        ],
    )
    resources.start(identity)
    ready(resources, identity, store)
    return identity


def run_checkpoint(root, parent, checkpoint, output, *, controller_revision):
    paths = [Path(path).absolute() for path in (root, parent, checkpoint, output)]
    if any(path != path.resolve() for path in paths):
        raise ValueError("checkpoint_paths_must_not_use_symlinks")
    root, parent, checkpoint, output = paths
    source = Path(__file__).resolve().parents[3]
    if (
        not re.fullmatch(r"[a-f0-9]{40}", controller_revision)
        or source.name != controller_revision
    ):
        raise ValueError("Use the staged committed checkpoint controller")
    lease, docker = Lease.load(root), DockerOperations()
    if (
        root == parent
        or root.parent != parent.parent
        or not checkpoint.is_relative_to(parent / "evidence")
        or not output.is_relative_to(root / "evidence")
        or output.exists()
        or lease.source_revision != controller_revision
        or time.time() + 2400 >= lease.dispatch_deadline
    ):
        raise ValueError("checkpoint_requires_new_finite_owner_and_evidence")
    healthy_lease(root, lease, docker)
    output.mkdir(parents=True, mode=0o700)
    binding = None
    try:
        binding = bind_parent(parent, checkpoint, docker)
        create_record(
            output / "plan.json",
            {
                "activation_id": lease.activation_id,
                "controller_revision": controller_revision,
                "controller_file": file_binding(Path(__file__)),
                "parent": binding,
                "copy_targets": [
                    {
                        "store": store["store"],
                        "volume": lease.project + "_" + store["store"] + "-copy",
                    }
                    for store in binding["stores"]
                ],
                "scope": "Read-only physical copies of the closed writer-free point; no providers or product runtime",
                "restore_verified": False,
            },
        )
        resources = CopyResources(root, lease, docker, parent, checkpoint, binding)
        query = migration_head_query(source)
        dumps = []
        for store in binding["stores"]:
            evidence = output / store["store"]
            evidence.mkdir(mode=0o700)
            target, helper = resources.copy(store, evidence)
            resources.fence()
            identity = database_copy(resources, store, target)
            if store["store"] == "ade":
                head = sql(identity, store["user"], store["database"], query)
                if head != binding["ade_migration_head"]:
                    raise ValueError("copied_ade_migration_head_changed")
            resources.fence()
            dumped = dump_database(
                evidence / (store["store"] + ".dump"),
                identity,
                store["user"],
                store["database"],
            )
            resources.fence()
            docker.stop(identity)
            dumps.append(
                {
                    **dumped,
                    "store": store["store"],
                    "image_id": store["image_id"],
                    "parent_container_id": store["container_id"],
                    "copy_container_id": identity,
                    "copy_helper_id": helper,
                    "parent_volume": store["volume"],
                    "copy_volume": target,
                    "copy_receipt": file_binding(evidence / "copy.json"),
                }
            )
        resources.fence()
        create_record(
            output / "paired-backup.json",
            {
                "dumps": dumps,
                "time": time.time(),
                "parent_activation": binding["activation_id"],
                "parent_source_revision": binding["source_revision"],
                "parent_checkpoint_files": binding["files"],
                "native_progress_at_checkpoint": binding["native_progress"],
                "restore_verified": False,
            },
        )
        return dumps
    except Exception as exc:
        create_record(
            output / "failure.json",
            {"error_type": type(exc).__name__, "time": time.time()},
        )
        raise
    finally:
        stopped = stop_owned(
            lease, docker=docker, root=root, reason="stopped_checkpoint_closeout"
        )
        baseline = docker.snapshot([row["id"] for row in lease.baseline])
        running = [row["id"] for row in docker.owned(lease) if row["state"] in ACTIVE]
        parent_unchanged = False
        try:
            parent_unchanged = (
                binding is not None
                and bind_parent(parent, checkpoint, docker, copy_lease=lease) == binding
            )
        finally:
            create_record(
                output / "closeout.json",
                {
                    "time": time.time(),
                    "baseline_unchanged": baseline == list(lease.baseline),
                    "baseline_count": len(baseline),
                    "running_owned": running,
                    "stop_failures": stopped["failures"],
                    "closed_parent_unchanged": parent_unchanged,
                },
            )
        if (
            running
            or baseline != list(lease.baseline)
            or stopped["failures"]
            or not parent_unchanged
        ):
            raise RuntimeError("stopped_checkpoint_closeout_incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "parent", "checkpoint", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--controller-revision", required=True)
    args = parser.parse_args()
    result = run_checkpoint(
        args.root,
        args.parent,
        args.checkpoint,
        args.out,
        controller_revision=args.controller_revision,
    )
    print(
        json.dumps(
            {
                "stores": [
                    {key: row[key] for key in ("store", "sha256", "bytes")}
                    for row in result
                ]
            }
        )
    )


if __name__ == "__main__":
    main()
