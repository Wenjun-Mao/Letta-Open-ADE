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
from . import lifecycle
from . import quiescence
from .receipts import ReceiptStore
from .supervisor import WORK_CUTOFF, jobs, lease, load_registry

OPERATIONS = {"build", "pull", "up", "run", "restart", "exec", "stop"}
OWNERSHIP_OPTIONS = {"-p", "--project-name", "-f", "--file", "--env-file",
                     "--project-directory", "-v", "--volume", "--volumes",
                     "--remove-orphans", "--profile", "--build"}
SERVICE_OPTIONS = {
    "up": {"--pull"},
    "run": {"--pull", "--entrypoint", "--env", "-e", "--user"},
    "exec": set(),
    "build": set(),
    "pull": set(),
}
SERVICE_FLAGS = {
    "up": {"-d", "--detach", "--no-build"},
    "run": {"--rm", "--no-deps", "-T", "--no-TTY"},
    "exec": {"-T", "--no-TTY"},
    "build": {"--no-cache"},
    "pull": set(),
}
SERVICE_OPERANDS = {
    "up": {"db", "model-router", "hindsight", "runner"},
    "run": {"hindsight", "runner"},
    "exec": {"db", "model-router", "hindsight", "runner"},
    "build": {"db", "model-router", "runner"},
    "pull": {"hindsight"},
}
RUN_ENVIRONMENT = {"HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"}
CACHE_PROVISIONING_RUN = (
    "run", "--rm", "--no-deps", "--pull", "never", "--user", "0",
    "-e", "HF_HUB_OFFLINE=0", "-e", "TRANSFORMERS_OFFLINE=0",
    "--entrypoint", "python3", "hindsight", "/probe/cache_model.py",
)


def compose_service_options(arguments):
    """Parse the narrow Compose surface without scanning child argv as Compose flags."""
    operation = arguments[0]
    options = SERVICE_OPTIONS.get(operation, set())
    flags = SERVICE_FLAGS.get(operation, set())
    parsed = []
    services = []
    index = 1
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--":
            raise RuntimeError("compose_child_separator_not_allowed")
        option = argument.split("=", 1)[0]
        if (option in OWNERSHIP_OPTIONS
                or argument.startswith(("-p", "-f", "-v")) and not argument.startswith("--")):
            raise RuntimeError("compose_ownership_override_rejected")
        if argument.startswith("-"):
            if option in options:
                if "=" in argument:
                    value = argument.split("=", 1)[1]
                    if not value:
                        raise RuntimeError("compose_option_value_missing")
                    parsed.extend((option, value))
                    index += 1
                else:
                    if index + 1 >= len(arguments) or arguments[index + 1] == "--":
                        raise RuntimeError("compose_option_value_missing")
                    parsed.extend((option, arguments[index + 1]))
                    index += 2
                if operation == "run" and option in {"-e", "--env"}:
                    key, separator, value = parsed[-1].partition("=")
                    if key not in RUN_ENVIRONMENT or not separator or value not in {"0", "1"}:
                        raise RuntimeError("compose_environment_override_rejected")
                if operation == "run" and option == "--entrypoint" and parsed[-1] not in {"python", "python3"}:
                    raise RuntimeError("compose_entrypoint_override_rejected")
                if operation == "run" and option == "--user" and parsed[-1] != "0":
                    raise RuntimeError("compose_user_override_rejected")
                continue
            if option in flags and "=" not in argument:
                parsed.append(argument)
                index += 1
                continue
            raise RuntimeError("compose_option_unrecognized")
        if argument not in SERVICE_OPERANDS.get(operation, set()):
            raise RuntimeError("compose_service_unrecognized")
        services.append(argument)
        if operation in {"run", "exec"}:
            if len(services) != 1:
                raise RuntimeError("compose_service_ambiguous")
            return parsed, index, argument
        index += 1
    if not services:
        raise RuntimeError("compose_service_required")
    if len(services) != len(set(services)):
        raise RuntimeError("compose_service_duplicate")
    return parsed, None, services


def pull_policy(options):
    return [options[index + 1] for index, option in enumerate(options[:-1])
            if option == "--pull"]


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
        quiescence.require_open(state, registry, epoch)
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
            epoch["allocations"],
            lifecycle.classify(state, epoch, candidates, now),
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
        token = uuid.uuid4().hex
        operation = None
        service = None
        if kind == "dummy":
            if arguments:
                raise RuntimeError("dummy_takes_no_command")
            command = [sys.executable, "-c", "import time; time.sleep(90)"]
        elif kind == "build-cancel":
            operation = "build-cancel"
            if arguments or timeout > 120 or now + 600 >= registry["hard_deadline"]:
                raise RuntimeError("bounded_cancellation_fixture_required")
            if any(c["State"]["Status"] == "running" for c in candidates):
                raise RuntimeError("cancellation_probe_requires_candidate_stopped")
            if (
                sample["memory_available"]
                < sum(c["memory"] for c in epoch["allocations"].values())
                + 1.5 * host.GIB
            ):
                raise RuntimeError("insufficient_build_probe_headroom")
            context = (
                Path(epoch["release"])
                / "workflows/evals/hindsight_memory_probe/docker/cancellation"
            )
            command = [
                "docker",
                "build",
                "--platform",
                "linux/arm64",
                "--network",
                "none",
                "--progress",
                "plain",
                "--no-cache",
                "--build-arg",
                f"PROBE_CANCELLATION_TOKEN={token}",
                "--tag",
                f"ade-hindsight-probe-cancel:{token}",
                "--file",
                str(context / "Dockerfile"),
                str(context),
            ]
        else:
            if not arguments or arguments[0] not in OPERATIONS:
                raise RuntimeError("owned_compose_operation_required")
            if arguments[0] in {"restart", "stop"}:
                raise RuntimeError("use_supervisor_pause_and_diagnosed_rearm")
            compose_options, _service_boundary, _services = compose_service_options(arguments)
            operation = arguments[0]
            service = _services
            if arguments[0] == "up" and (
                "--no-build" not in compose_options
                or sum(option in {"-d", "--detach"} for option in compose_options) != 1
                or pull_policy(compose_options) != ["never"]
            ):
                raise RuntimeError("startup_must_use_qualified_local_images")
            if arguments[0] == "run" and (
                "--rm" not in compose_options or "--no-deps" not in compose_options
                or
                pull_policy(compose_options) != ["never"]
            ):
                raise RuntimeError("one_shot_must_use_qualified_local_images")
            root_user_requested = arguments[0] == "run" and any(
                compose_options[index] == "--user" and compose_options[index + 1] == "0"
                for index in range(len(compose_options) - 1)
            )
            if root_user_requested and (
                kind != "work" or timeout != 1800
                or tuple(arguments) != CACHE_PROVISIONING_RUN
            ):
                raise RuntimeError("compose_user_override_rejected")
            if arguments[0] == "exec" and not ({"-T", "--no-TTY"} & set(compose_options)):
                raise RuntimeError("exec_must_disable_tty")
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
        startup = lifecycle.startup_services(arguments) if kind != "dummy" else []
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
                **({"DOCKER_BUILDKIT": "1"} if kind == "build-cancel" else {}),
                "PROBE_RELEASE_SHA": Path(epoch["release"]).name,
                "ADE_PROBE_REGISTRY_SHA256": registry["registry_sha256"],
                "ADE_PROBE_EPOCH_SHA256": epoch["sha256"],
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
                    "operation": operation,
                    "service": service,
                    "build_sentinel": token if kind == "build-cancel" else None,
                    "identity": identity,
                    "token": token,
                    "deadline": min(WORK_CUTOFF, now + timeout),
                    "created": now,
                    "epoch_sha256": epoch["sha256"],
                },
            )
            lifecycle.prepare(
                state,
                epoch,
                candidates,
                startup,
                token,
                min(WORK_CUTOFF, now + timeout),
                now,
            )
            with quiescence.dispatch_admission(state, registry, epoch):
                os.write(write_fd, b"1")
        finally:
            os.close(write_fd)
        # exec changes cmdline; capture stable start tick + current cmdline after handshake.
        # Ownership checks use persisted launch identity for the gate, unique inherited marker after exec.
        return child.pid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument(
        "--kind", choices=["build", "work", "dummy", "build-cancel"], required=True
    )
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
