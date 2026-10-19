"""Host-controlled interruption of only this activation's native Router."""

import argparse
from pathlib import Path
import subprocess
import time
import urllib.request

from .operations import (
    DockerOperations,
    Lease,
    SOURCE_LABEL,
    check_lease,
    create_record,
    resources,
)
from .startup import require_configuration, require_supervision


def wait_for(path, process, *, deadline):
    while time.monotonic() < deadline:
        if path.is_file():
            return
        if process.poll() is not None:
            raise RuntimeError(
                "Native recovery runner ended before the fault checkpoint"
            )
        time.sleep(0.15)
    raise TimeoutError("Native recovery checkpoint deadline exceeded")


def healthy_lease(root, lease, docker):
    issues = check_lease(
        lease,
        docker=docker,
        capacity=resources(lease.disk_path),
        closed=(root / "closed.json").exists(),
    )
    if issues:
        raise ValueError("Native fault refused: " + ",".join(issues))
    require_supervision(root, lease, now=time.time())


def run_fault(root, environment, output, *, partial, timeout):
    lease = Lease.load(root)
    docker = DockerOperations()
    healthy_lease(root, lease, docker)
    if time.time() + timeout >= lease.dispatch_deadline:
        raise ValueError("Native fault cannot fit the activation dispatch window")
    if output.exists() or not output.resolve().is_relative_to(
        (root / "evidence").resolve()
    ):
        raise ValueError("Fault attempt requires a new activation evidence directory")
    require_configuration(root, environment, lease)
    routers = [
        record
        for record in docker.owned(lease)
        if (record.get("labels") or {}).get("com.docker.compose.service")
        == "model-router"
    ]
    if len(routers) != 1 or routers[0]["state"] != "running":
        raise ValueError("Fault requires exactly one healthy owned Router")
    router = routers[0]
    if router["labels"].get(SOURCE_LABEL) != lease.source_revision:
        raise ValueError("Fault Router source does not match activation")
    create_record(
        output / "host-plan.json",
        {
            "activation_id": lease.activation_id,
            "router_id": router["id"],
            "source_revision": lease.source_revision,
            "partial": partial,
            "timeout_seconds": timeout,
            "fault": "owned_router_stop_then_same_operation_retry",
        },
    )
    command = [
        "docker",
        "compose",
        "--env-file",
        str(environment),
        "-f",
        str(Path(__file__).with_name("compose.yaml")),
        "run",
        "--rm",
        "runner",
        "-m",
        "workflows.evals.hindsight_integration.native_recovery",
        "--out",
        "/evidence/" + str(output.relative_to(root / "evidence")),
        "--timeout",
        str(timeout),
    ]
    if partial:
        command.append("--partial")
    interrupted = False
    process = None
    deadline = time.monotonic() + timeout
    try:
        if not partial:
            docker.stop(router["id"])
            interrupted = True
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        if partial:
            wait_for(output / "fault-ready.json", process, deadline=deadline)
            healthy_lease(root, lease, docker)
            docker.stop(router["id"])
            interrupted = True
        create_record(
            output / "router-stopped.json",
            {"router_id": router["id"], "time": time.time()},
        )
        wait_for(output / "fault-observed.json", process, deadline=deadline)
        healthy_lease(root, lease, docker)
        docker._run(["start", router["id"]])
        interrupted = False
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:18019/v1/health", timeout=2
                ) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise TimeoutError("Owned Router did not recover")
        create_record(
            output / "router-restored.json",
            {
                "activation_id": lease.activation_id,
                "router_id": router["id"],
                "time": time.time(),
            },
        )
        stdout, _ = process.communicate(timeout=max(1, deadline - time.monotonic()))
        print(stdout)
        if process.returncode:
            raise RuntimeError("Native recovery runner failed; preserve its evidence")
    finally:
        try:
            if interrupted:
                healthy_lease(root, lease, docker)
                docker._run(["start", router["id"]])
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    run_fault(
        args.root,
        args.environment,
        args.out,
        partial=args.partial,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
