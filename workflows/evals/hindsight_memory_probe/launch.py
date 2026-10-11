"""Register/monitor owned builds and one-shot work before dispatch; stdlib only."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from . import host_guard as host
from . import epochs
from .receipts import ReceiptStore
from .supervisor import WORK_CUTOFF, jobs, lease, load_registry

OPERATIONS = {"build", "pull", "up", "run", "restart", "exec", "stop"}


def launch(state, kind, timeout, arguments):
    registry = load_registry(state)
    epoch = epochs.active(state, registry)
    now = time.time()
    if (
        now >= WORK_CUTOFF
        or timeout <= 0
        or timeout > 3600
        or epochs.stopped_path(state, epoch).exists()
    ):
        raise RuntimeError("invalid_or_elapsed_work_deadline")
    controllers = [json.loads(p.read_text()) for p in state.glob("*.controller.json")]
    if not any(
        host.identity_matches(c["identity"])
        and c["registry_sha256"] == registry["registry_sha256"]
        and c.get("epoch_sha256") == epoch["sha256"]
        for c in controllers
    ):
        raise RuntimeError("detached_supervisor_required")
    # A live PID is insufficient: require held supervisor lease, not just stale state.
    try:
        with lease(state):
            pass
    except BlockingIOError:
        pass
    else:
        raise RuntimeError("supervisor_lease_not_held")
    with lease(state, "jobs.lock"):
        owned_registry = epochs.effective_registry(state, registry)
        items = host.containers()
        candidates = host.candidate_containers(items, owned_registry)
        sample = host.host_sample(registry["release"])
        reason, _ = host.guard_reason(
            owned_registry,
            items,
            sample["memory_available"],
            sample["disk_free"],
            None,
            now,
        )
        if reason or sample["memory_available"] < 1.5 * host.GIB:
            raise RuntimeError("unsafe_work_launch")
        for job in jobs(state):
            if job.get("epoch_sha256") == epoch["sha256"] and not host.tagged_processes(
                job["token"]
            ):
                result_path = state / f"job-{job['token']}.result.json"
                if (
                    not result_path.exists()
                    or json.loads(result_path.read_text()).get("exit_code") != 0
                ):
                    raise RuntimeError("prior_work_failed_requires_diagnosed_rearm")
        if any(host.tagged_processes(j["token"]) for j in jobs(state)):
            raise RuntimeError("serial_work_only")
        if kind == "dummy":
            if arguments:
                raise RuntimeError("dummy_takes_no_command")
            command = [sys.executable, "-c", "import time; time.sleep(90)"]
        else:
            if not arguments or arguments[0] not in OPERATIONS:
                raise RuntimeError("owned_compose_operation_required")
            if any(
                a
                in {
                    "-p",
                    "--project-name",
                    "-f",
                    "--file",
                    "--env-file",
                    "--project-directory",
                    "--volumes",
                    "-v",
                    "--volume",
                    "--remove-orphans",
                    "--build",
                    "--profile",
                }
                or a.split("=")[0]
                in {
                    "--project-name",
                    "--file",
                    "--env-file",
                    "--project-directory",
                    "--volume",
                }
                for a in arguments[1:]
            ):
                raise RuntimeError("compose_ownership_override_rejected")
            if arguments[0] == "up" and (
                "--no-build" not in arguments
                or "--pull" not in arguments
                or arguments[arguments.index("--pull") + 1] != "never"
            ):
                raise RuntimeError("startup_must_use_qualified_local_images")
            if arguments[0] == "run" and (
                "--pull" not in arguments
                or arguments[arguments.index("--pull") + 1] != "never"
            ):
                raise RuntimeError("one_shot_must_use_qualified_local_images")
            if arguments[0] in {"restart", "stop"}:
                raise RuntimeError("use_supervisor_pause_and_diagnosed_rearm")
            if kind == "build":
                if arguments[0] not in {"build", "pull"} or any(
                    c["State"]["Status"] == "running" for c in candidates
                ):
                    raise RuntimeError("builds_are_serial_before_inference")
            elif arguments[0] in {"build", "pull"}:
                raise RuntimeError("build_must_be_registered_as_build")
            running_caps = sum(
                c["HostConfig"].get("Memory", 0)
                for c in candidates
                if c["State"]["Status"] == "running"
            )
            if (
                sample["memory_available"]
                < max(
                    0,
                    sum(c["memory"] for c in epoch["allocations"].values())
                    - running_caps,
                )
                + 1.5 * host.GIB
            ):
                raise RuntimeError("insufficient_prospective_memory_headroom")
            if (
                sample["cpus"]
                < sum(c["cpu"] for c in epoch["allocations"].values()) + 0.5
            ):
                raise RuntimeError("insufficient_cpu_headroom")
            release = Path(epoch["release"])
            private = release.parent.parent / "private"
            command = [
                "docker",
                "compose",
                "--project-name",
                host.PROJECT,
                "--env-file",
                str(private / "secrets.env"),
                "-f",
                str(release / "workflows/evals/hindsight_memory_probe/compose.yaml"),
                *arguments,
            ]
        token = uuid.uuid4().hex
        read_fd, write_fd = os.pipe()
        store = ReceiptStore(state)
        log = os.open(
            state / f"process-{token}.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        child = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "workflows.evals.hindsight_memory_probe.process_child",
                str(read_fd),
                json.dumps(command),
                str(state),
                token,
            ],
            cwd=epoch["release"],
            pass_fds=(read_fd,),
            start_new_session=True,
            env={
                **os.environ,
                "ADE_PROBE_PROCESS_OWNER": token,
                "COMPOSE_PARALLEL_LIMIT": "1",
                "PROBE_RELEASE_SHA": Path(epoch["release"]).name,
                **{
                    f"PROBE_{name.upper().replace('-', '_')}_{key.upper()}": str(value)
                    for name, caps in epoch["allocations"].items()
                    for key, value in caps.items()
                },
            },
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
        )
        os.close(log)
        os.close(read_fd)
        try:
            identity = host.proc_identity(child.pid)
            if identity is None:
                raise RuntimeError("process_identity_unavailable")
            store.write(
                f"job-{token}.json",
                {
                    "kind": kind,
                    "identity": identity,
                    "token": token,
                    "deadline": min(WORK_CUTOFF, now + timeout),
                    "created": now,
                    "epoch_sha256": epoch["sha256"],
                },
            )
            os.write(write_fd, b"1")
        finally:
            os.close(write_fd)
        # exec changes cmdline; capture stable start tick + current cmdline after handshake.
        # Ownership checks use persisted launch identity for the gate, unique inherited marker after exec.
        return child.pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--kind", choices=["build", "work", "dummy"], required=True)
    parser.add_argument("--timeout", type=int, required=True)
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        print(
            launch(
                args.state,
                args.kind,
                args.timeout,
                args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments,
            )
        )
    except Exception:
        print("probe_work_launch_failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
