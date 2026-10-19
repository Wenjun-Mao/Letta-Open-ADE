"""Fail-closed startup for the exact provisioned native candidate."""

import hashlib
import json
from pathlib import Path
import subprocess
import time

from .operations import (
    DockerOperations,
    Lease,
    check_lease,
    resources,
    stop_owned,
)
from .runtime_assets import require_runtime_assets


def require_supervision(root: Path, lease: Lease, *, now: float) -> None:
    checks = sorted((root / "checks").glob("*.json"))
    if not checks:
        raise ValueError("Startup requires an active host supervisor")
    check = json.loads(checks[-1].read_bytes())
    if (
        check.get("activation_id") != lease.activation_id
        or check.get("source_revision") != lease.source_revision
        or check.get("issues") != []
        or not isinstance(check.get("time"), (float, int))
        or not 0 <= now - check["time"] <= 60
    ):
        raise ValueError("Startup requires a fresh healthy source-bound supervisor")


def require_configuration(root: Path, environment: Path, lease: Lease) -> None:
    provisioned = json.loads((root / "provisioned.json").read_bytes())
    if (
        provisioned.get("environment_path") != str(environment.resolve())
        or provisioned.get("environment_sha256")
        != hashlib.sha256(environment.read_bytes()).hexdigest()
        or provisioned.get("activation_id") != lease.activation_id
    ):
        raise ValueError("Candidate configuration differs from provisioned identity")


def start_native(root: Path, environment: Path) -> None:
    _start(root, environment, [["up", "-d", "db", "model-router", "hindsight"]])


def start_product(root: Path, environment: Path) -> None:
    _start(
        root,
        environment,
        [
            ["up", "-d", "--wait", "--wait-timeout", "60", "ade-db"],
            ["run", "--rm", "--no-deps", "ade-migrate"],
            [
                "up",
                "-d",
                "--wait",
                "--wait-timeout",
                "240",
                "db",
                "model-router",
                "hindsight",
                "fault-proxy",
                "ade-api",
                "ade-worker",
                "ade-web",
            ],
        ],
        product=True,
    )


def _start(
    root: Path, environment: Path, steps: list[list[str]], *, product=False
) -> None:
    lease = Lease.load(root)
    docker = DockerOperations()
    issues = check_lease(
        lease,
        docker=docker,
        capacity=resources(lease.disk_path),
        closed=(root / "closed.json").exists(),
    )
    if issues:
        raise ValueError("Candidate startup refused: " + ",".join(issues))
    require_supervision(root, lease, now=time.time())
    require_configuration(root, environment, lease)
    compose = Path(__file__).with_name("compose.yaml")
    command = [
        "docker",
        "compose",
        "--env-file",
        str(environment),
        "-f",
        str(compose),
        *(["--profile", "product"] if product else []),
    ]
    try:
        for step in steps:
            require_supervision(root, lease, now=time.time())
            require_configuration(root, environment, lease)
            if product:
                require_runtime_assets(root)
            if (
                root / "closed.json"
            ).exists() or time.time() >= lease.dispatch_deadline:
                raise ValueError("Activation closed during candidate startup")
            subprocess.run([*command, *step], check=True, timeout=300)
            # Closure during startup must not leave newly created containers running.
            require_supervision(root, lease, now=time.time())
            require_configuration(root, environment, lease)
            if (
                root / "closed.json"
            ).exists() or time.time() >= lease.dispatch_deadline:
                raise ValueError("Activation closed during candidate startup")
    except Exception:
        stop_owned(lease, docker=docker, root=root, reason="startup_failed")
        raise
