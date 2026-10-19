"""Host lease and exact-container ownership for the isolated integration stack."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import tempfile
from uuid import UUID, uuid4


OWNER_LABEL = "io.ade.integration.activation"
SOURCE_LABEL = "io.ade.integration.source"
PROJECT_LABEL = "com.docker.compose.project"
PROJECT_PREFIX = "ade-hindsight-integration"
MAX_LEASE_SECONDS = 12 * 60 * 60
SHUTDOWN_MARGIN_SECONDS = 60 * 60
GIB = 1024**3

INSPECTION = (
    '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},'
    '"state":{{json .State.Status}},"started_at":{{json .State.StartedAt}},'
    '"restarts":{{json .RestartCount}},"oom":{{json .State.OOMKilled}},'
    '"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}null{{end}},'
    '"mounts":{{json .Mounts}},"labels":{{json .Config.Labels}},'
    '"networks":{{json .NetworkSettings.Networks}}}'
)


def encoded(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def create_record(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".activation-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(encoded(value) + b"\n")
            target.flush()
            os.fsync(target.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


class DockerOperations:
    def _run(self, arguments: list[str], *, timeout: int = 20) -> str:
        result = subprocess.run(
            ["docker", *arguments], capture_output=True, text=True, timeout=timeout
        )
        if result.returncode:
            raise RuntimeError("docker_operation_failed")
        return result.stdout

    def snapshot(self, identities: list[str] | None = None) -> list[dict]:
        if identities is None:
            identities = self._run(["ps", "-aq", "--no-trunc"]).split()
        if not identities:
            return []
        output = self._run(["inspect", "--format", INSPECTION, *identities])
        return sorted(
            (json.loads(line) for line in output.splitlines()), key=lambda x: x["id"]
        )

    def owned(self, lease: Lease) -> list[dict]:
        identities = self._run(
            [
                "ps",
                "-aq",
                "--no-trunc",
                "--filter",
                f"label={PROJECT_LABEL}={lease.project}",
                "--filter",
                f"label={OWNER_LABEL}={lease.activation_id}",
            ]
        ).split()
        records = self.snapshot(identities)
        if any(not lease.owns(record) for record in records):
            raise RuntimeError("container_ownership_mismatch")
        return records

    def stop(self, identity: str) -> None:
        self._run(["stop", "--time", "30", identity], timeout=45)


@dataclass(frozen=True)
class Lease:
    project: str
    activation_id: str
    source_revision: str
    started_at: int
    dispatch_deadline: int
    expires_at: int
    disk_path: str
    baseline: tuple[dict, ...]
    minimum_available_ram: int = 4 * GIB
    minimum_free_disk: int = 10 * GIB

    def __post_init__(self) -> None:
        if not re.fullmatch(r"ade-hindsight-integration(?:-[a-z0-9-]+)?", self.project):
            raise ValueError("Invalid isolated integration project")
        UUID(self.activation_id)
        if not re.fullmatch(r"[0-9a-f]{40}", self.source_revision):
            raise ValueError("An exact committed source revision is required")
        if (
            not self.started_at < self.dispatch_deadline < self.expires_at
            or self.expires_at - self.started_at > MAX_LEASE_SECONDS
            or self.expires_at - self.dispatch_deadline < SHUTDOWN_MARGIN_SECONDS
            or self.minimum_available_ram < 4 * GIB
            or self.minimum_free_disk < 10 * GIB
        ):
            raise ValueError("Invalid finite lease or resource reserve")

    def owns(self, record: dict) -> bool:
        labels = record.get("labels") or {}
        return (
            labels.get(PROJECT_LABEL) == self.project
            and labels.get(OWNER_LABEL) == self.activation_id
        )

    def save(self, root: Path) -> None:
        value = asdict(self)
        create_record(root / "lease.json", value)
        create_record(
            root / "lease.seal.json",
            {"sha256": hashlib.sha256(encoded(value)).hexdigest()},
        )

    @classmethod
    def load(cls, root: Path) -> Lease:
        value = json.loads((root / "lease.json").read_bytes())
        seal = json.loads((root / "lease.seal.json").read_bytes())
        if hashlib.sha256(encoded(value)).hexdigest() != seal["sha256"]:
            raise ValueError("Activation lease changed")
        value["baseline"] = tuple(value["baseline"])
        return cls(**value)


def prepare_lease(
    root: Path,
    *,
    docker: DockerOperations,
    project: str,
    source_revision: str,
    disk_path: str,
    duration: int = MAX_LEASE_SECONDS,
    now: int | None = None,
) -> Lease:
    snapshots = docker.snapshot()
    if any(
        (record.get("labels") or {}).get(PROJECT_LABEL) == project
        and record["state"] in {"running", "restarting", "paused"}
        for record in snapshots
    ):
        raise ValueError(
            "Reconcile and stop the previous activation before a new lease"
        )
    now = int(time.time()) if now is None else now
    lease = Lease(
        project,
        str(uuid4()),
        source_revision,
        now,
        now + duration - SHUTDOWN_MARGIN_SECONDS,
        now + duration,
        disk_path,
        tuple(
            record
            for record in snapshots
            if (record.get("labels") or {}).get(PROJECT_LABEL) != project
        ),
    )
    lease.save(root)
    return lease


def resources(disk_path: str) -> dict[str, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, _, value = line.partition(":")
        if key == "MemAvailable":
            values["available_ram"] = int(value.split()[0]) * 1024
    disk = os.statvfs(disk_path)
    values["free_disk"] = disk.f_bavail * disk.f_frsize
    return values


def check_lease(
    lease: Lease,
    *,
    docker: DockerOperations,
    capacity: dict[str, int],
    now: int | None = None,
    closed: bool = False,
) -> list[str]:
    now = int(time.time()) if now is None else now
    issues = []
    if closed:
        issues.append("activation_closed")
    if now >= lease.dispatch_deadline:
        issues.append("dispatch_window_closed")
    if capacity["available_ram"] < lease.minimum_available_ram:
        issues.append("host_ram_reserve_breached")
    if capacity["free_disk"] < lease.minimum_free_disk:
        issues.append("host_disk_reserve_breached")
    baseline = docker.snapshot([record["id"] for record in lease.baseline])
    if baseline != list(lease.baseline):
        issues.append("baseline_changed")
    owned = docker.owned(lease)
    if any(
        (record.get("labels") or {}).get(SOURCE_LABEL) != lease.source_revision
        for record in owned
    ):
        issues.append("candidate_source_mismatch")
    if any(
        record.get("oom") or record.get("health") == "unhealthy" for record in owned
    ):
        issues.append("candidate_unhealthy")
    return issues


def stop_owned(
    lease: Lease, *, docker: DockerOperations, root: Path, reason: str
) -> dict:
    try:
        create_record(
            root / "closed.json",
            {
                "activation_id": lease.activation_id,
                "reason": reason,
                "time": time.time(),
            },
        )
    except FileExistsError:
        closed = json.loads((root / "closed.json").read_bytes())
        if closed.get("activation_id") != lease.activation_id:
            raise ValueError("Closed activation belongs to another owner")
    failures = []
    stopped = []
    try:
        records = docker.owned(lease)
    except Exception as exc:
        records = []
        failures.append({"id": None, "error_type": type(exc).__name__})

    def order(record: dict) -> tuple[int, str]:
        service = (record.get("labels") or {}).get("com.docker.compose.service", "")
        priority = 0 if service == "model-router" else 2
        if "db" in service:
            priority = 3
        return priority, record["id"]

    for record in sorted(records, key=order):
        if record["state"] not in {"running", "restarting", "paused"}:
            continue
        try:
            docker.stop(record["id"])
            stopped.append(record["id"])
        except Exception as exc:
            failures.append({"id": record["id"], "error_type": type(exc).__name__})
    receipt = {
        "activation_id": lease.activation_id,
        "reason": reason,
        "stopped": stopped,
        "failures": failures,
        "time": time.time(),
    }
    create_record(root / "stops" / f"{time.time_ns()}.json", receipt)
    return receipt


def supervise(root: Path, *, interval: float = 15) -> int:
    lease = Lease.load(root)
    docker = DockerOperations()
    while True:
        try:
            if Lease.load(root) != lease:
                raise ValueError("Activation lease changed")
            capacity = resources(lease.disk_path)
            issues = check_lease(
                lease,
                docker=docker,
                capacity=capacity,
                closed=(root / "closed.json").exists(),
            )
        except Exception as exc:
            issues = [f"supervision_failed_{type(exc).__name__}"]
            capacity = {}
        create_record(
            root / "checks" / f"{time.time_ns()}.json",
            {
                "time": time.time(),
                "issues": issues,
                "capacity": capacity,
                "activation_id": lease.activation_id,
                "source_revision": lease.source_revision,
            },
        )
        if issues:
            receipt = stop_owned(
                lease, docker=docker, root=root, reason=",".join(issues)
            )
            if not receipt["failures"]:
                return 1
        time.sleep(interval)
