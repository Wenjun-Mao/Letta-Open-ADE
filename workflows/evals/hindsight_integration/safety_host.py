"""Finite host side of public safety cases; commands select only exact owned services."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import time
import urllib.request
from uuid import UUID

from .native_faults import healthy_lease
from .operations import DockerOperations, Lease, create_record, stop_owned
from .paired_backup import owned_service
from .startup import require_configuration
from .stale_finalizer_host import StaleFinalizer, identifiers


STEPS = {
    "recall-outage": ("stop-native", "start-native"),
    "runtime-restart": ("restart-runtime",),
    "stale-worker": ("lock-subject", "expire-finalizer"),
}


class OwnedControls:
    def __init__(self, root, environment, output):
        self.root, self.environment, self.output = root, environment, output
        self.lease, self.docker = Lease.load(root), DockerOperations()
        self.original = {
            name: owned_service(self.docker, self.lease, name)
            for name in ("hindsight", "ade-api", "ade-worker")
        }
        self.changed = []
        values = dict(
            shlex.split(line)[0].split("=", 1)
            for line in environment.read_text().splitlines()
            if line and not line.startswith("#")
        )
        self.native_key = values["INTEGRATION_HINDSIGHT_KEY"]
        self.workspace = values["INTEGRATION_WORKSPACE_KEY"]
        self.finalizer = None

    def fence(self):
        healthy_lease(self.root, self.lease, self.docker)
        require_configuration(self.root, self.environment, self.lease)

    def current(self, name):
        row = owned_service(self.docker, self.lease, name)
        original = self.original[name]
        if any(row[key] != original[key] for key in ("id", "image", "mounts")):
            raise ValueError("owned_runtime_container_or_store_changed")
        return row

    def stop(self, name):
        self.fence()
        row = self.current(name)
        if name not in self.changed:
            self.changed.append(name)
        self.docker.stop(row["id"])

    def start(self, name):
        self.fence()
        row = self.current(name)
        if row["state"] != "running":
            self.docker._run(["start", row["id"]])
        if name == "hindsight":
            self.native_ready()
        if name in self.changed:
            self.changed.remove(name)

    def native_ready(self):
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            self.fence()
            try:
                request = urllib.request.Request(
                    "http://127.0.0.1:18889/health",
                    headers={"Authorization": "Bearer " + self.native_key},
                )
                with urllib.request.urlopen(request, timeout=3) as response:
                    if response.status == 200:
                        return
            except OSError:
                pass
            time.sleep(1)
        raise TimeoutError("owned_native_did_not_restart")

    def perform(self, action):
        self.fence()
        if action == "stop-native":
            self.stop("hindsight")
        elif action == "start-native":
            self.start("hindsight")
        elif action == "restart-runtime":
            for name in ("ade-api", "ade-worker", "hindsight"):
                self.stop(name)
            for name in ("hindsight", "ade-api", "ade-worker"):
                self.start(name)
        elif action == "restore-owned":
            self.restore()
        else:
            raise ValueError("undeclared_owned_control")
        return {name: self.current(name) for name in self.original}

    def restore(self):
        if self.finalizer is not None:
            self.finalizer.close()
        for name in ("hindsight", "ade-api", "ade-worker"):
            if name in self.changed:
                self.start(name)


def respond(path, *, output, controls, scenarios, positions):
    runner_root = (output / "run").resolve()
    if path.is_symlink() or not path.resolve().is_relative_to(runner_root):
        raise ValueError("host_request_outside_owned_run")
    scenario = path.parent.parent.name
    if scenario not in scenarios or not re.fullmatch(r"[0-9]{4}\.json", path.name):
        raise ValueError("undeclared_host_request_path")
    value = json.loads(path.read_bytes())
    if set(value) != {"id", "action", "details", "product_revision", "time"}:
        raise ValueError("invalid_host_request_fields")
    identity = str(UUID(value["id"]))
    if value["product_revision"] != controls.lease.source_revision:
        raise ValueError("host_request_binding_mismatch")
    action, position = value["action"], positions[scenario]
    fields = {
        "lock-subject": ("subject_id", "conversation_id"),
        "expire-finalizer": ("run_id",),
    }
    if action in fields and scenario == "stale-worker":
        identifiers(value["details"], fields[action])
    elif value["details"] != {}:
        raise ValueError("host_request_binding_mismatch")
    if action != "restore-owned" and (
        position >= len(STEPS[scenario]) or action != STEPS[scenario][position]
    ):
        raise ValueError("host_control_out_of_declared_order")
    receipt = {
        "id": identity,
        "action": action,
        "product_revision": controls.lease.source_revision,
        "started_at": time.time(),
        "status": "failed",
    }
    try:
        if scenario == "stale-worker" and action in fields:
            if controls.finalizer is None:
                controls.finalizer = StaleFinalizer(controls, controls.workspace)
            method = (
                controls.finalizer.lock
                if action == "lock-subject"
                else controls.finalizer.expire
            )
            receipt["control_result"] = method(value["details"])
        else:
            receipt["owned_after"] = controls.perform(action)
        receipt["status"] = "ok"
        if action != "restore-owned":
            positions[scenario] += 1
    except Exception as exc:
        receipt["error_type"] = type(exc).__name__
    receipt["finished_at"] = time.time()
    create_record(path.parent.parent / "host-responses" / path.name, receipt)
    create_record(output / "host-controls" / f"{time.time_ns()}.json", receipt)
    return receipt


def finish_owned_child(process, controls, name):
    try:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    finally:
        try:
            for row in controls.docker.owned(controls.lease):
                if row["name"].lstrip("/") == name and row["state"] in {
                    "running",
                    "paused",
                    "restarting",
                }:
                    controls.docker.stop(row["id"])
        finally:
            try:
                controls.restore()
            except Exception:
                stop_owned(
                    controls.lease,
                    docker=controls.docker,
                    root=controls.root,
                    reason="owned_host_restore_failed",
                )
                raise


def require_runner_image(root, lease, docker):
    receipt = json.loads((root / "images.json").read_text())
    candidates = [row for row in receipt["images"] if row["role"] == "runner"]
    if (
        receipt["source_revision"] != lease.source_revision
        or receipt["activation_id"] != lease.activation_id
        or len(candidates) != 1
    ):
        raise ValueError("owned_runner_image_receipt_mismatch")
    record = candidates[0]
    actual = docker._run(["image", "inspect", record["image"], "--format", "{{.Id}}"])
    if actual.strip() != record["image_id"]:
        raise ValueError("owned_runner_image_changed")
    return record


def run_host(root, environment, output, *, controller_revision, scenarios):
    controller = Path(__file__).resolve().parents[3]
    if controller.name != controller_revision or not re.fullmatch(
        r"[a-f0-9]{40}", controller_revision
    ):
        raise ValueError("Use the staged committed host controller")
    if (
        not scenarios
        or len(set(scenarios)) != len(scenarios)
        or any(name not in STEPS for name in scenarios)
    ):
        raise ValueError("Use unique declared owned-host scenarios")
    root, output = root.resolve(), output.resolve()
    if output.exists() or not output.is_relative_to(root / "evidence"):
        raise ValueError("Host controller requires a new owned evidence directory")
    controls = OwnedControls(root, environment, output)
    controls.fence()
    runner_image = require_runner_image(root, controls.lease, controls.docker)
    timeout = 600 * len(scenarios) + 240
    if time.time() + timeout >= controls.lease.dispatch_deadline:
        raise ValueError("Owned host faults do not fit the dispatch window")
    output.mkdir(mode=0o700)
    name = controls.lease.project + "-" + output.name
    if not re.fullmatch(r"[a-z0-9-]{1,120}", name):
        raise ValueError("Invalid owned controller container name")
    if any(
        row["name"].lstrip("/") == name for row in controls.docker.owned(controls.lease)
    ):
        raise ValueError("Owned controller container name already exists")
    product = root.parents[2] / "releases" / controls.lease.source_revision
    python_path = f"/controller/{controller_revision}:/app/services/ade-api/src:/app/packages/agent-runtime-eval-contracts/src:/app/packages/model-catalog-contracts/src:/app"
    command = [
        "docker",
        "compose",
        "--env-file",
        str(environment),
        "-f",
        str(product / "workflows/evals/hindsight_integration/compose.yaml"),
        "run",
        "--rm",
        "--no-deps",
        "--name",
        name,
        "--workdir",
        f"/controller/{controller_revision}",
        "--volume",
        f"{controller}:/controller/{controller_revision}:ro",
        "--env",
        "PYTHONPATH=" + python_path,
        "runner",
        "-m",
        "workflows.evals.hindsight_integration.safety_runner",
        "--out",
        "/evidence/" + str((output / "run").relative_to(root / "evidence")),
        "--controller-revision",
        controller_revision,
    ]
    for scenario in scenarios:
        command.extend(["--scenario", scenario])
    create_record(
        output / "host-plan.json",
        {
            "product_revision": controls.lease.source_revision,
            "controller_revision": controller_revision,
            "controller_file_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "stale_finalizer_host_sha256": hashlib.sha256(
                Path(__file__).with_name("stale_finalizer_host.py").read_bytes()
            ).hexdigest(),
            "activation_id": controls.lease.activation_id,
            "steps": {key: list(STEPS[key]) for key in scenarios},
            "command": command,
            "timeout_seconds": timeout,
            "original_owned": controls.original,
            "runner_image": runner_image,
        },
    )
    process, positions, handled = None, {key: 0 for key in scenarios}, set()
    try:
        with (output / "runner.log").open("x") as log:
            (output / "runner.log").chmod(0o600)
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                controls.fence()
                for path in sorted((output / "run").glob("*/host-requests/*.json")):
                    if path not in handled:
                        respond(
                            path,
                            output=output,
                            controls=controls,
                            scenarios=scenarios,
                            positions=positions,
                        )
                        handled.add(path)
                if time.monotonic() >= deadline:
                    raise TimeoutError("owned_host_controller_deadline")
                time.sleep(0.5)
        if process.returncode or any(
            positions[key] != len(STEPS[key]) for key in scenarios
        ):
            raise RuntimeError("owned_host_safety_cases_failed")
        create_record(
            output / "host-outcome.json",
            {"status": "passed", "positions": positions, "time": time.time()},
        )
    except Exception as exc:
        create_record(
            output / "host-failure.json",
            {
                "error_type": type(exc).__name__,
                "positions": positions,
                "time": time.time(),
            },
        )
        raise
    finally:
        finish_owned_child(process, controls, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--controller-revision", required=True)
    parser.add_argument(
        "--scenario", action="append", choices=tuple(STEPS), required=True
    )
    args = parser.parse_args()
    run_host(
        args.root,
        args.environment,
        args.out,
        controller_revision=args.controller_revision,
        scenarios=args.scenario,
    )


if __name__ == "__main__":
    main()
