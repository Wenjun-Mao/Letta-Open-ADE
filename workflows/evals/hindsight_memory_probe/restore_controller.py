"""Detached finite controller for one explicitly admitted disposable restore."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import select
import subprocess
import time
import traceback
from pathlib import Path

from . import epochs, host_guard as host, restore, restore_cleanup, restore_compare, restore_database as db
from . import restore_process, restore_snapshot
from .campaign_clock import WORK_CUTOFF
from .receipts import ReceiptStore


class Controller:
    def __init__(self, directory: Path, token: str, controller_token: str):
        self.directory = directory
        self.operation = restore.read_operation(directory)
        self.token = token
        self.controller_token = controller_token
        if (self.operation["token"] != token
                or os.environ.get("ADE_PROBE_PROCESS_OWNER") != controller_token):
            raise RuntimeError("restore_controller_registration_mismatch")
        self.store = ReceiptStore(directory)
        self.registry = json.loads((directory / "registry.json").read_text())
        self.epoch = epochs.active(directory, self.registry)
        self.admission = json.loads((directory / f"epoch-{self.epoch['index']:04d}.finalize-admission.json").read_text())
        self.finalized_hash = hashlib.sha256(
            (directory / f"epoch-{self.epoch['index']:04d}.finalized.json").read_bytes()
        ).hexdigest()
        self.stage = "controller-start"
        self.operation_hash = hashlib.sha256(restore.operation_path(directory).read_bytes()).hexdigest()
        db.COMMAND_RUNNER = self.docker_json
        db.TEXT_RUNNER = self.docker_text
        host.CONTAINER_READER = self.read_containers

    def read_containers(self) -> list[dict]:
        identifiers = self.docker_text(["docker", "ps", "-aq", "--no-trunc"])
        return self.docker_json(["docker", "inspect", *identifiers]) if identifiers else []

    def docker_text(self, command: list[str], timeout: int = 10) -> list[str]:
        path = Path(self.operation["restore_root"]) / f"docker-text-{time.time_ns()}.partial"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as output:
                code = restore_process.run_command(
                    self.directory, self.operation, command, timeout,
                    operation_label="restore-identity-list-readback", monitor=self.check_basic,
                    stdout=output, stderr=subprocess.DEVNULL,
                )
                output.flush()
                os.fsync(output.fileno())
            if code != 0:
                raise RuntimeError("restore_docker_readback_failed")
            return path.read_text(encoding="utf-8").splitlines()
        finally:
            path.unlink(missing_ok=True)

    def write(self, suffix: str, value: dict) -> None:
        self.store.write(f"restore-{self.token}-{suffix}.json", value)

    def check_safe(self) -> None:
        self.check_basic()
        current_finalized = self.directory / f"epoch-{self.epoch['index']:04d}.finalized.json"
        if hashlib.sha256(current_finalized.read_bytes()).hexdigest() != self.finalized_hash:
            raise RuntimeError("restore_finalization_proof_changed")
        registry = json.loads((self.directory / "registry.json").read_text())
        if registry != self.registry or epochs.active(self.directory, registry) != self.epoch:
            raise RuntimeError("restore_main_epoch_changed")
        create_pending = (
            (self.directory / f"restore-{self.token}-create.intent.json").exists()
            and not (self.directory / f"restore-{self.token}-create.result.json").exists()
        )
        restore._verify_host(self.directory, self.registry, self.admission,
                             prospective=False, allow_restore_creation=create_pending)
        db.verify_compose(self.operation)
        container = db.restore_container(self.operation, allow_unregistered=create_pending)
        create_result = self.directory / f"restore-{self.token}-create.result.json"
        if create_result.exists():
            if container is None:
                raise RuntimeError("restore_container_disappeared")
            state = container.get("State", {})
            if state.get("Status") != "running":
                raise RuntimeError("restore_unexpected_container_exit")
            if state.get("OOMKilled") or container.get("RestartCount") != 0:
                raise RuntimeError("restore_container_restart_or_oom")

    def check_basic(self) -> None:
        if time.time() >= min(self.operation["deadline"], WORK_CUTOFF):
            raise RuntimeError("restore_deadline_elapsed")
        stop_path = self.directory / f"restore-{self.token}-stop.intent.json"
        if stop_path.is_file():
            stop = json.loads(stop_path.read_text())
            expected = {"schema": 1, "token": self.token,
                        "registry_sha256": self.operation["registry_sha256"],
                        "epoch_sha256": self.operation["epoch_sha256"],
                        "kind": "emergency_restore_preemption"}
            if any(stop.get(key) != value for key, value in expected.items()):
                raise RuntimeError("restore_stop_intent_invalid")
            raise RuntimeError("restore_stop_requested")
        operation_bytes = restore.operation_path(self.directory).read_bytes()
        if hashlib.sha256(operation_bytes).hexdigest() != self.operation_hash:
            raise RuntimeError("restore_operation_changed")
        sample = host.host_sample(self.operation["release_path"])
        if (sample["memory_available"] < int(1.5 * host.GIB)
                or sample["cpus"] < 0.75 or sample["disk_free"] < 15 * host.GIB):
            raise RuntimeError("restore_host_headroom_insufficient")
        for path in self.directory.glob(f"restore-{self.token}-*-job.json"):
            job = json.loads(path.read_text())
            if time.time() >= job["deadline"] and host.tagged_processes(job["token"]):
                raise RuntimeError("restore_registered_process_deadline_elapsed")

    def docker_json(self, command: list[str], timeout: int = 10):
        path = Path(self.operation["restore_root"]) / f"docker-readback-{time.time_ns()}.partial"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb") as output:
                code = restore_process.run_command(
                    self.directory, self.operation, command, timeout,
                    operation_label="restore-identity-readback", monitor=self.check_basic,
                    stdout=output, stderr=subprocess.DEVNULL,
                )
                output.flush()
                os.fsync(output.fileno())
            if code != 0:
                raise RuntimeError("restore_docker_readback_failed")
            return json.loads(path.read_bytes())
        finally:
            path.unlink(missing_ok=True)

    def validate_source(self) -> None:
        source = db.source_container(self.directory, self.operation)
        if (source["Image"] != self.operation["compose"]["source_image_id"]
                or source["Config"]["Image"] != self.operation["compose"]["source_image"]):
            raise RuntimeError("restore_qualified_image_mismatch")

    def command(self, command: list[str], timeout: int, label: str | None = None, *,
                operation_label: str | None = None,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL) -> int:
        self.check_safe()
        return restore_process.run_command(self.directory, self.operation, command, timeout,
                                           operation_label=operation_label or label or "restore-command",
                                           monitor=self.check_safe,
                                           stdin=stdin, stdout=stdout, stderr=stderr)

    def ensure_container(self, allow_unregistered: bool = False) -> dict:
        self.check_safe()
        value = db.restore_container(self.operation, allow_unregistered=allow_unregistered)
        if value is None:
            raise RuntimeError("restore_container_missing")
        return value

    def run(self, resume: bool = False) -> None:
        self.check_safe()
        create_path = self.directory / f"restore-{self.token}-create.result.json"
        if not create_path.exists():
            if resume and (self.directory / f"restore-{self.token}-create.intent.json").exists():
                raise RuntimeError("restore_resume_create_outcome_ambiguous")
            self.stage = "create"
            if db.restore_container(self.operation, allow_unregistered=False) is not None:
                raise RuntimeError("restore_project_collision")
            if db.verify_volume(self.operation, allow_unregistered=True) is not None:
                raise RuntimeError("restore_volume_collision")
            self.write("create.intent", {"token": self.token, "started_at": time.time(),
                                          "compose_sha256": self.operation["compose"]["sha256"],
                                          "project": self.operation["compose"]["project"],
                                          "volume": self.operation["compose"]["volume"]})
            config = self.operation["compose"]["path"]
            command = ["docker", "compose", "--project-name", self.operation["compose"]["project"],
                       "-f", config, "up", "-d", "--pull", "never", "db"]
            code = self.command(command, 90, "compose-create", stderr=subprocess.DEVNULL)
            if code != 0:
                raise RuntimeError("restore_compose_create_failed")
            container = db.restore_container(self.operation, allow_unregistered=True)
            volume = db.verify_volume(self.operation, allow_unregistered=True)
            if container is None or volume is None or container["State"]["Status"] != "running":
                raise RuntimeError("restore_create_identity_readback_failed")
            created = {"token": self.token, "container_id": container["Id"],
                       "image_id": container["Image"], "started_at": container["State"]["StartedAt"],
                       "service": "db", "project": self.operation["compose"]["project"],
                       "config_path": self.operation["compose"]["path"],
                       "config_sha256": self.operation["compose"]["sha256"],
                       "volume": self.operation["compose"]["volume"], "volume_identity": {
                           key: volume.get(key) for key in ("Name", "Driver", "Scope", "Mountpoint", "CreatedAt")},
                       "created_at": time.time()}
            self.write("create.result", created)
            self.stage = "readiness"
            ready_until = min(time.time() + 90, self.operation["deadline"])
            ready = False
            while time.time() < ready_until:
                if self.command(["docker", "exec", "-i", container["Id"], "psql", "-U",
                                 "hindsight_probe", "-d", "hindsight_probe", "-At", "-c",
                                 "SELECT current_database()"], 10, "database-readiness") == 0:
                    ready = True
                    break
                time.sleep(2)
            if not ready:
                raise RuntimeError("restore_database_startup_timeout")
        self.stage = "restore"
        container = self.ensure_container()
        restore_result_path = self.directory / f"restore-{self.token}-restore.result.json"
        if not restore_result_path.exists():
            self.write("restore.intent", {"token": self.token, "started_at": time.time(),
                                           "container_id": container["Id"],
                                           "archive_sha256": self.operation["archive"]["sha256"]})
            archive = Path(self.operation["archive"]["path"])
            if db.sha256_file(archive) != self.operation["archive"]["sha256"]:
                raise RuntimeError("restore_archive_changed_after_admission")
            stderr_path = Path(self.operation["restore_root"]) / "pg_restore.stderr"
            fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with archive.open("rb") as source, os.fdopen(fd, "wb") as diagnostics:
                command = ["docker", "exec", "-i", container["Id"], "pg_restore",
                           "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl",
                           "-U", "hindsight_probe", "-d", "hindsight_probe"]
                code = self.command(command, min(900, int(self.operation["deadline"] - time.time())),
                                    "pg-restore", stdin=source, stderr=diagnostics)
                diagnostics.flush()
                os.fsync(diagnostics.fileno())
            if code != 0:
                raise RuntimeError("restore_pg_restore_failed")
            self.write("restore.result", {"token": self.token, "status": "completed",
                "container_id": container["Id"], "image_id": container["Image"],
                "archive_sha256": self.operation["archive"]["sha256"],
                "command": ["pg_restore", "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl"],
                "completed_at": time.time()})
        self.stage = "snapshot"
        container = self.ensure_container()
        snapshot = restore_snapshot.snapshot(self.directory, self.operation, container,
                                             self.store, self.command)
        self.write("snapshot.result", {"token": self.token, "snapshot": snapshot,
                                       "completed_at": time.time()})
        self.stage = "compare"
        if db.sha256_file(Path(self.operation["selection"]["path"])) != self.operation["selection"]["sha256"]:
            raise RuntimeError("restore_selection_changed")
        if db.sha256_file(Path(self.operation["snapshot"]["path"])) != self.operation["snapshot"]["sha256"]:
            raise RuntimeError("restore_original_snapshot_changed")
        original = json.loads(Path(self.operation["snapshot"]["path"]).read_text())
        selection = json.loads(Path(self.operation["selection"]["path"]).read_text())
        comparison = restore_compare.compare(original, Path(self.operation["snapshot"]["root"]),
            snapshot, Path(self.operation["restore_root"]), selection)
        self.write("compare.result", comparison)
        if comparison["status"] != "completed":
            raise RuntimeError("restore_comparison_mismatch")
        result = {"token": self.token, "status": "completed",
                  "claim": "logical_persisted_state_restore_only",
                  "archive_sha256": self.operation["archive"]["sha256"],
                  "original_snapshot_sha256": self.operation["snapshot"]["sha256"],
                  "restored_snapshot_sha256": db.sha256_file(Path(self.operation["restore_root"]) / "canonical-snapshot.json"),
                  "comparison_sha256": db.sha256_file(self.directory / f"restore-{self.token}-compare.result.json"),
                  "completed_at": time.time()}
        self.write("result", result)

    def run_guarded(self, resume: bool = False) -> int:
        failure = None
        try:
            self.validate_source()
            self.check_safe()
            self.run(resume)
        except Exception as exc:
            reason = str(exc) if isinstance(exc, RuntimeError) and str(exc).replace("_", "").isalnum() else "restore_controller_failed"
            frame = traceback.extract_tb(exc.__traceback__)[-1]
            failure = {"token": self.token, "status": "failed", "stage": self.stage,
                       "error_type": type(exc).__name__, "error_site": f"{Path(frame.filename).name}:{frame.name}:{frame.lineno}",
                       "reason": reason, "time": time.time(),
                       "archive_preserved": Path(self.operation["archive"]["path"]).is_file(),
                       "original_snapshot_preserved": Path(self.operation["snapshot"]["path"]).is_file()}
            try:
                self.write("failure.result", failure)
            except Exception:
                os.write(2, b"probe_restore_failure_receipt_unavailable\n")
        try:
            restore_cleanup.cleanup(self.directory, controller_token=self.controller_token)
        except Exception:
            try:
                self.write("cleanup.failure", {"token": self.token, "status": "failed",
                    "reason": "restore_cleanup_readback_failed", "time": time.time()})
            except Exception:
                os.write(2, b"probe_restore_cleanup_receipt_unavailable\n")
        return 1 if failure else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--gate-fd", type=int, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not select.select([args.gate_fd], [], [], 20)[0] or os.read(args.gate_fd, 1) != b"1":
        return 1
    os.close(args.gate_fd)
    controller_token = os.environ.get("ADE_PROBE_PROCESS_OWNER", "")
    try:
        return Controller(args.state, args.token, controller_token).run_guarded(args.resume)
    except Exception:
        os.write(2, b"probe_restore_controller_startup_failed\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
