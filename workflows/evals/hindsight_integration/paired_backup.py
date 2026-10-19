"""Quiesce only the owned candidate and preserve both stores without claiming restore."""

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

from .native_faults import healthy_lease
from .backup_readbacks import (
    PublicReads,
    native_pending,
    product_readbacks,
    router_snapshot,
)
from .operations import DockerOperations, Lease, SOURCE_LABEL, create_record, stop_owned
from .startup import require_configuration


def owned_service(docker, lease, service):
    rows = [
        row
        for row in docker.owned(lease)
        if row["labels"].get("com.docker.compose.service") == service
        and not row.get("auto_remove")
    ]
    if len(rows) != 1 or rows[0]["labels"].get(SOURCE_LABEL) != lease.source_revision:
        raise ValueError("paired_checkpoint_service_identity_mismatch")
    return rows[0]


def sql(container, user, database, query):
    result = subprocess.run(
        [
            "docker",
            "exec",
            container,
            "psql",
            "-U",
            user,
            "-d",
            database,
            "-At",
            "-c",
            query,
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return result.stdout.strip()


def migration_head_query(source_root):
    configuration = configparser.ConfigParser(interpolation=None)
    with (source_root / "services/ade-api/alembic.ini").open() as source:
        configuration.read_file(source)
    schema, table = (
        configuration.get("alembic", key)
        for key in ("version_table_schema", "version_table")
    )
    if not all(
        re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", name) for name in (schema, table)
    ):
        raise ValueError("unsafe_alembic_version_table_identity")
    return f'SELECT version_num FROM "{schema}"."{table}" ORDER BY version_num;'


def dump_database(output, container, user, database):
    descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "wb") as target:
        result = subprocess.run(
            ["docker", "exec", container, "pg_dump", "-U", user, "-d", database, "-Fc"],
            stdout=target,
            stderr=subprocess.PIPE,
            timeout=300,
        )
        target.flush()
        os.fsync(target.fileno())
    if result.returncode:
        raise RuntimeError("owned_database_dump_failed")
    digest = hashlib.sha256()
    with output.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    with output.open("rb") as source:
        listing = subprocess.run(
            ["docker", "exec", "-i", container, "pg_restore", "--list"],
            stdin=source,
            capture_output=True,
            timeout=30,
        )
    if listing.returncode:
        raise RuntimeError("owned_database_archive_unreadable")
    create_record(
        output.with_suffix(".toc.json"),
        {
            "archive_sha256": digest.hexdigest(),
            "toc_sha256": hashlib.sha256(listing.stdout).hexdigest(),
            "toc": listing.stdout.decode("utf-8"),
            "restore_verified": False,
        },
    )
    return {
        "file": output.name,
        "sha256": digest.hexdigest(),
        "bytes": output.stat().st_size,
        "archive_toc_verified": True,
    }


def run_backup(
    root, environment, output, *, controller_revision, product_run, drain_seconds=120
):
    root, output, product_run = root.resolve(), output.resolve(), product_run.resolve()
    if Path(__file__).resolve().parents[3].name != controller_revision:
        raise ValueError("Use the staged committed controller directory")
    if (
        not re.fullmatch(r"[a-f0-9]{40}", controller_revision)
        or not 0 <= drain_seconds <= 300
    ):
        raise ValueError("Use a committed controller and bounded drain")
    if (
        output.exists()
        or not output.is_relative_to(root / "evidence")
        or not product_run.is_relative_to(root / "evidence")
    ):
        raise ValueError("Paired checkpoint requires new owned evidence paths")
    lease, docker = Lease.load(root), DockerOperations()
    healthy_lease(root, lease, docker)
    require_configuration(root, environment, lease)
    head_query = migration_head_query(Path(__file__).resolve().parents[3])
    invocation = json.loads((product_run / "invocation.json").read_text())
    if invocation["source"]["source_revision"] != lease.source_revision:
        raise ValueError("paired_product_run_source_mismatch")
    if time.time() + drain_seconds + 1200 >= lease.dispatch_deadline:
        raise ValueError("Paired checkpoint cannot fit the dispatch window")
    output.mkdir(mode=0o700)
    values = dict(
        shlex.split(line)[0].split("=", 1)
        for line in environment.read_text().splitlines()
        if line and not line.startswith("#")
    )
    reads = PublicReads(output / "public-http", values)
    create_record(
        output / "plan.json",
        {
            "product_revision": lease.source_revision,
            "controller_revision": controller_revision,
            "controller_file_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "activation_id": lease.activation_id,
            "drain_seconds": drain_seconds,
            "scope": "No-writers paired backup; not a restored or release-qualified recovery point",
        },
    )
    try:
        create_record(
            output / "product-readbacks.json",
            {"relationships": product_readbacks(reads, product_run)},
        )
        ade = owned_service(docker, lease, "ade-db")
        native = owned_service(docker, lease, "db")
        banks = json.loads(
            sql(
                ade["id"],
                "ade_integration_admin",
                "ade_integration",
                "SELECT coalesce(json_agg(row_to_json(r)), '[]') FROM "
                "(SELECT bank_id,state,last_error_code FROM ade.memory_relationships "
                "ORDER BY bank_id) r;",
            )
        )
        create_record(output / "relationship-states.json", {"relationships": banks})
        for name in ("ade-web", "ade-api", "ade-worker"):
            docker.stop(owned_service(docker, lease, name)["id"])
        deadline, stable = time.monotonic() + drain_seconds, 0
        while True:
            progress = native_pending(reads, banks)
            stable = (
                stable + 1
                if not progress["pending"] and not progress["incomplete_banks"]
                else 0
            )
            create_record(output / "drain" / f"{time.time_ns()}.json", progress)
            if stable >= 3 or time.monotonic() >= deadline:
                break
            time.sleep(2)
        docker.stop(owned_service(docker, lease, "hindsight")["id"])
        create_record(output / "router-traffic.json", router_snapshot(reads))
        for name in ("model-router", "fault-proxy"):
            docker.stop(owned_service(docker, lease, name)["id"])
        writers = [
            row
            for row in docker.owned(lease)
            if row["state"] in {"running", "restarting", "paused"}
            and row["labels"].get("com.docker.compose.service") not in {"ade-db", "db"}
        ]
        if writers:
            raise ValueError("paired_checkpoint_writers_still_running")
        create_record(
            output / "no-writers.json",
            {
                "time": time.time(),
                "owned": docker.owned(lease),
                "native_progress": progress,
                "ade_migration_head": sql(
                    ade["id"],
                    "ade_integration_admin",
                    "ade_integration",
                    head_query,
                ),
            },
        )
        dumps = [
            {
                "store": "ade",
                "image_id": ade["image"],
                **dump_database(
                    output / "ade.dump",
                    ade["id"],
                    "ade_integration_admin",
                    "ade_integration",
                ),
            },
            {
                "store": "hindsight",
                "image_id": native["image"],
                **dump_database(
                    output / "hindsight.dump",
                    native["id"],
                    "hindsight_integration",
                    "hindsight_integration",
                ),
            },
        ]
        create_record(
            output / "paired-backup.json",
            {"dumps": dumps, "time": time.time(), "restore_verified": False},
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
            lease, docker=docker, root=root, reason="paired_checkpoint_closeout"
        )
        baseline = docker.snapshot([row["id"] for row in lease.baseline])
        running = [
            row["id"]
            for row in docker.owned(lease)
            if row["state"] in {"running", "restarting", "paused"}
        ]
        create_record(
            output / "closeout.json",
            {
                "time": time.time(),
                "baseline_unchanged": baseline == list(lease.baseline),
                "baseline_count": len(baseline),
                "running_owned": running,
                "stop_failures": stopped["failures"],
            },
        )
        if running or baseline != list(lease.baseline) or stopped["failures"]:
            raise RuntimeError("paired_checkpoint_closeout_incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--product-run", type=Path, required=True)
    parser.add_argument("--controller-revision", required=True)
    args = parser.parse_args()
    result = run_backup(
        args.root,
        args.environment,
        args.out,
        controller_revision=args.controller_revision,
        product_run=args.product_run,
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
