"""Temporary OCI campaign expiry/safety supervisor. No scheduler or controller dependence."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from . import host_guard as host
from . import epochs
from . import releases
from . import lifecycle
from . import quiescence
from .receipts import ReceiptStore

from .campaign_clock import STARTED, TARGET, DEADLINE, WORK_CUTOFF

CAP_MEMORY = int(7.75 * host.GIB)
CAP_CPU = 1.5


def load_registry(directory):
    raw = (directory / "registry.json").read_bytes()
    value = json.loads(raw)
    if (
        value["started"] != STARTED
        or value["target"] != TARGET
        or value["hard_deadline"] != DEADLINE
        or value["project"] != host.PROJECT
        or value["caps_memory"] != CAP_MEMORY
        or value["caps_cpu"] != CAP_CPU
        or value["registry_sha256"] != digest_registry(value)
    ):
        raise RuntimeError("immutable_campaign_registry_conflict")
    return value


def digest_registry(value):
    return hashlib.sha256(
        json.dumps(
            {k: v for k, v in value.items() if k != "registry_sha256"}, sort_keys=True
        ).encode()
    ).hexdigest()


@contextmanager
def lease(directory, name="supervisor.lock"):
    descriptor = os.open(
        directory / name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def initialize(directory, release, now=None):
    now = time.time() if now is None else now
    if now >= WORK_CUTOFF:
        raise RuntimeError("hard_deadline_elapsed")
    release = releases.validate_path(release)
    releases.verify(release)
    if release.parent != Path("/mnt/projects/apps/ade-hindsight-probe/releases"):
        raise RuntimeError("release_path_not_owned")
    if len(release.name) != 40 or any(
        c not in "0123456789abcdef" for c in release.name
    ):
        raise RuntimeError("clean_sha_release_required")
    store = ReceiptStore(directory)
    with lease(directory):
        if (directory / "registry.json").exists():
            raise RuntimeError("registry_already_exists_use_readback_resume")
        sample = host.host_sample(release)
        if sample["memory_available"] < CAP_MEMORY + 1.5 * host.GIB:
            raise RuntimeError("insufficient_prospective_memory_headroom")
        if sample["cpus"] < CAP_CPU + 0.5 or sample["disk_free"] < 25 * host.GIB:
            raise RuntimeError("insufficient_cpu_or_staging_disk")
        items = host.containers()
        registry = {
            "project": host.PROJECT,
            "release": str(release),
            "started": STARTED,
            "target": TARGET,
            "hard_deadline": DEADLINE,
            "caps_memory": CAP_MEMORY,
            "caps_cpu": CAP_CPU,
            "baseline": [host.baseline_projection(c) for c in items],
            "initial_sample": sample,
            "created": now,
        }
        # Existing candidate state must be recovered, never silently adopted as baseline.
        if host.candidate_containers(items, registry):
            raise RuntimeError("candidate_exists_without_registry")
        registry["registry_sha256"] = digest_registry(registry)
        store.write("registry.json", registry)
        epochs.append(
            directory, registry, epochs.INITIAL_ALLOCATIONS, sample, "initial", now=now
        )


def jobs(directory):
    return [
        json.loads(p.read_text())
        for p in sorted(directory.glob("job-*.json"))
        if re.fullmatch(r"job-[a-f0-9]{32}\.json", p.name)
    ]


def record(store, event, **fields):
    store.write(
        f"{time.time_ns()}-{uuid.uuid4().hex}.event.json",
        {"event": event, "time": time.time(), **fields},
    )


def stop_owned(directory, registry, store, reason):
    epoch = epochs.active(directory, registry)
    registry = epochs.effective_registry(directory, registry)
    quiescence.admit_stop(directory, epoch, reason)
    # The durable barrier forbids new handshakes, even if a registration is still draining.
    with quiescence.bounded_lease(directory, "jobs.lock", 60, required=False):
        for job in jobs(directory):
            host.stop_processes(job)
        # Give owned process trees a finite grace period; no broad process-group signal.
        until = time.monotonic() + 5
        while time.monotonic() < until and any(
            host.tagged_processes(j["token"]) for j in jobs(directory)
        ):
            time.sleep(0.2)
        for job in jobs(directory):
            for identity in host.tagged_processes(job["token"]):
                if host.identity_matches(identity):
                    try:
                        os.kill(identity["pid"], signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        host.stop_containers(host.containers(), registry)
        stopped_items = host.containers()
        host.ensure_stopped(stopped_items, registry, jobs(directory))
        record(store, "stopped", reason=reason)
        path = epochs.stopped_path(directory, epoch)
        if not path.exists():
            store.write(
                path.name,
                {
                    "reason": reason,
                    "time": time.time(),
                    "epoch_sha256": epoch["sha256"],
                    "stopped_containers": [
                        lifecycle.dormant_projection(c)
                        for c in host.candidate_containers(stopped_items, registry)
                    ],
                },
            )


def readback(directory):
    registry = load_registry(directory)
    candidates = host.candidate_containers(
        host.containers(), epochs.effective_registry(directory, registry)
    )
    return {
        "registry_sha256": registry["registry_sha256"],
        "hard_deadline": DEADLINE,
        "seconds_remaining": max(0, DEADLINE - time.time()),
        "sample": host.host_sample(registry["release"]),
        "owned_containers": [host.baseline_projection(c) for c in candidates],
        "epoch": epochs.active(directory, registry),
        "stopping": quiescence.stop_path(
            directory, epochs.active(directory, registry)
        ).exists(),
        "lifecycle": lifecycle.classify(
            directory, epochs.active(directory, registry), candidates, time.time()
        ),
        "jobs": [
            {
                "kind": j["kind"],
                "identity": j["identity"],
                "alive": bool(host.tagged_processes(j["token"])),
                "deadline": j["deadline"],
                "result": json.loads(
                    (directory / f"job-{j['token']}.result.json").read_text()
                )
                if (directory / f"job-{j['token']}.result.json").exists()
                else None,
            }
            for j in jobs(directory)
        ],
    }


def run(directory, resume=False):
    store = ReceiptStore(directory)
    with lease(directory):
        registry = load_registry(directory)
        if time.time() >= WORK_CUTOFF:
            stop_owned(directory, registry, store, "hard_deadline_elapsed")
            raise RuntimeError("hard_deadline_elapsed")
        epoch = epochs.active(directory, registry)
        if epochs.stopped_path(directory, epoch).exists():
            raise RuntimeError("campaign_already_stopped")
        launches = [
            p
            for p in directory.glob("*.controller.json")
            if json.loads(p.read_text()).get("epoch_sha256") == epoch["sha256"]
        ]
        if bool(launches) != resume:
            raise RuntimeError("resume_requires_prior_controller_and_readback")
        # Positive local readback before resume; baseline and current candidates are checked below.
        record(
            store,
            "resume_readback" if resume else "launch_readback",
            readback=readback(directory),
        )
        controller = {
            "identity": host.proc_identity(os.getpid()),
            "registry_sha256": registry["registry_sha256"],
            "hard_deadline": DEADLINE,
            "epoch_sha256": epoch["sha256"],
        }
        store.write(f"{uuid.uuid4().hex}.controller.json", controller)
        owned_registry = epochs.effective_registry(directory, registry)
        reason, low_since = None, None
        try:
            while reason is None:
                if (
                    load_registry(directory) != registry
                    or epochs.active(directory, registry) != epoch
                ):
                    raise RuntimeError("registry_changed")
                now = time.time()
                if (
                    quiescence.stop_path(directory, epoch).exists()
                    or (
                        directory / f"epoch-{epoch['index']:04d}.pause-request.json"
                    ).exists()
                ):
                    reason = "planned_operator_pause"
                    break
                if now >= WORK_CUTOFF:
                    reason = "hard_deadline_elapsed"
                    break
                sample = host.host_sample(registry["release"])
                items = host.containers()
                reason, low_since = host.guard_reason(
                    owned_registry,
                    items,
                    sample["memory_available"],
                    sample["disk_free"],
                    low_since,
                    now,
                    epoch["allocations"],
                    lifecycle.classify(
                        directory,
                        epoch,
                        host.candidate_containers(items, owned_registry),
                        now,
                    ),
                )
                record(
                    store,
                    "sample",
                    cgroups=host.cgroup_sample(items, owned_registry),
                    **sample,
                )
                for job in jobs(directory):
                    if job.get("epoch_sha256") == epoch["sha256"]:
                        result = directory / f"job-{job['token']}.result.json"
                        if (
                            result.exists()
                            and json.loads(result.read_text()).get("exit_code") != 0
                        ):
                            reason = "owned_process_failed"
                    if now >= job["deadline"] and host.tagged_processes(job["token"]):
                        reason = "owned_process_deadline_elapsed"
                if reason is None:
                    time.sleep(min(5, max(0.01, WORK_CUTOFF - now)))
        except BaseException:
            reason = "supervisor_readback_or_controller_failure"
            raise
        finally:
            stop_owned(directory, registry, store, reason or "supervisor_ended")


def rearm_epoch(directory, reason, diagnosis, allocation_file=None, release=None):
    with lease(directory):
        with lease(directory, "jobs.lock"):
            registry = load_registry(directory)
            owned_registry = epochs.effective_registry(directory, registry)
            items = host.containers()
            if any(
                c["State"]["Status"] == "running"
                for c in host.candidate_containers(items, owned_registry)
            ):
                raise RuntimeError("rearm_requires_candidate_stopped")
            if any(host.tagged_processes(j["token"]) for j in jobs(directory)):
                raise RuntimeError("rearm_requires_jobs_stopped")
            sample = host.host_sample(registry["release"])
            reason_found, _ = host.guard_reason(
                registry,
                [c for c in items if not host.owned(c, owned_registry)],
                sample["memory_available"],
                sample["disk_free"],
                None,
                time.time(),
            )
            if reason_found:
                raise RuntimeError("baseline_or_headroom_not_recovered")
            dormant = lifecycle.verified_dormant(
                directory,
                epochs.active(directory, registry),
                host.candidate_containers(items, owned_registry),
            )
            allocations = (
                json.loads(allocation_file.read_text())
                if allocation_file
                else epochs.active(directory, registry)["allocations"]
            )
            return epochs.append(
                directory,
                registry,
                allocations,
                sample,
                reason,
                diagnosis,
                release=release or epochs.active(directory, registry)["release"],
                dormant_containers=dormant,
            )


def request_pause(directory):
    registry = load_registry(directory)
    store = ReceiptStore(directory)
    epoch = epochs.active(directory, registry)
    quiescence.admit_stop(directory, epoch, "operator_stop")
    try:
        with lease(directory):
            stop_owned(directory, registry, store, "operator_stop")
    except BlockingIOError:
        path = directory / f"epoch-{epoch['index']:04d}.pause-request.json"
        if not path.exists():
            store.write(
                path.name, {"reason": "planned_operator_pause", "time": time.time()}
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--release", type=Path, required=True)
    start = sub.add_parser("run")
    start.add_argument("--resume", action="store_true")
    sub.add_parser("inspect")
    sub.add_parser("stop")
    rearm = sub.add_parser("rearm")
    rearm.add_argument("--reason", required=True)
    rearm.add_argument("--diagnosis", type=Path, required=True)
    rearm.add_argument("--allocations", type=Path)
    rearm.add_argument("--release", type=Path)
    args = parser.parse_args()
    try:
        if args.action == "init":
            initialize(args.state, args.release)
        elif args.action == "run":
            signal.signal(
                signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt())
            )
            run(args.state, args.resume)
        elif args.action == "inspect":
            print(json.dumps(readback(args.state), sort_keys=True))
        elif args.action == "rearm":
            rearm_epoch(
                args.state, args.reason, args.diagnosis, args.allocations, args.release
            )
        else:
            request_pause(args.state)
            return 0
    except (Exception, KeyboardInterrupt):
        # Never display Docker error output, environments or exception text.
        print(
            "probe_supervisor_failed; inspect private event receipts",
            file=__import__("sys").stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
