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
    ]
    try:
        subprocess.run(
            [*command, "up", "-d", "db", "model-router", "hindsight"],
            check=True,
            timeout=300,
        )
        # Closure during startup must not leave newly created containers running.
        require_supervision(root, lease, now=time.time())
        if (root / "closed.json").exists():
            raise ValueError("Activation closed during candidate startup")
    except Exception:
        stop_owned(lease, docker=docker, root=root, reason="startup_failed")
        raise
