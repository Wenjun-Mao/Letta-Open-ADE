"""Persistent epoch startup admission: dormant identity is never an active-exit exemption."""

from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

from . import host_guard as host
from .receipts import ReceiptStore


def identity(container):
    return {
        key: value
        for key, value in host.baseline_projection(container).items()
        if key not in {"status", "health", "restarts"}
    }


def dormant_projection(container):
    return {
        **host.baseline_projection(container),
        "finished": container["State"].get("FinishedAt"),
        "oom_killed": container["State"].get("OOMKilled", False),
        "memory": container["HostConfig"].get("Memory"),
        "nano_cpus": container["HostConfig"].get("NanoCpus"),
        "service": container["Config"]["Labels"]["com.docker.compose.service"],
        "release_directory": container["Config"]["Labels"][
            "com.docker.compose.project.working_dir"
        ],
    }


@contextmanager
def transaction(directory):
    descriptor = os.open(
        directory / "lifecycle.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    try:
        until = time.monotonic() + 20
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= until:
                    raise RuntimeError("lifecycle_lease_timeout") from None
                time.sleep(0.05)
        yield
    finally:
        os.close(descriptor)


def persistent(container):
    labels = container["Config"]["Labels"]
    return (
        labels["com.docker.compose.service"] != "runner"
        and labels.get("com.docker.compose.oneoff") != "True"
    )


def verified_dormant(directory, epoch, candidates):
    stopped = directory / f"epoch-{epoch['index']:04d}.stopped.json"
    if not stopped.exists():
        raise RuntimeError("rearm_requires_stopped_epoch_and_diagnosis")
    receipt = json.loads(stopped.read_text())
    if receipt["epoch_sha256"] != epoch["sha256"]:
        raise RuntimeError("stopped_epoch_receipt_conflict")
    proven = receipt.get("stopped_containers", [])
    result = []
    for container in candidates:
        projection = dormant_projection(container)
        if container["State"]["Status"] == "running" or projection not in proven:
            raise RuntimeError("dormant_identity_not_proven_by_stop_readback")
        if persistent(container):
            result.append(projection)
    return result


def path(directory, epoch, service, suffix):
    return directory / f"epoch-{epoch['index']:04d}-{service}.{suffix}.json"


def read_record(directory, epoch, service, suffix):
    file = path(directory, epoch, service, suffix)
    if not file.exists():
        return None
    value = json.loads(file.read_text())
    if value["epoch_sha256"] != epoch["sha256"] or value["service"] != service:
        raise RuntimeError("startup_admission_record_conflict")
    return value


def write_record(directory, epoch, service, suffix, value):
    ReceiptStore(directory).write(
        path(directory, epoch, service, suffix).name,
        {"epoch_sha256": epoch["sha256"], "service": service, **value},
    )


def startup_services(arguments):
    if not arguments or arguments[0] != "up":
        return []
    if "--always-recreate-deps" in arguments:
        raise RuntimeError("implicit_dependency_recreation_rejected")
    services = [a for a in arguments[1:] if a in host.SERVICES]
    if (
        not services
        or "runner" in services
        or any(a.startswith("--scale") for a in arguments)
    ):
        raise RuntimeError("explicit_persistent_startup_services_required")
    if "hindsight" in services and "--no-deps" not in arguments:
        services = list(dict.fromkeys([*services, "db", "model-router"]))
    return services


def _classify(directory, epoch, candidates, now):
    dormant = epoch.get("dormant_containers", [])
    rows, reason = {}, None
    for service in host.SERVICES - {"runner"}:
        intent = read_record(directory, epoch, service, "activation")
        started = read_record(directory, epoch, service, "started")
        result = read_record(directory, epoch, service, "activation-result")
        relevant = [
            c
            for c in candidates
            if persistent(c)
            and c["Config"]["Labels"]["com.docker.compose.service"] == service
        ]
        active_found = False
        for container in relevant:
            current = identity(container)
            proven_dormant = dormant_projection(container) in dormant
            if started is not None and current == started["identity"]:
                rows[container["Id"]] = "active"
                active_found = True
            elif proven_dormant:
                rows[container["Id"]] = "dormant"
            elif started is not None:
                rows[container["Id"]] = "unadmitted"
                reason = "candidate_identity_changed_without_rearm"
            elif intent is not None and container["Config"]["Labels"][
                "com.docker.compose.project.working_dir"
            ] == str(
                Path(intent["release"]) / "workflows/evals/hindsight_memory_probe"
            ):
                if container["State"]["Status"] == "created":
                    rows[container["Id"]] = "startup_pending"
                else:
                    # Persist the actual first identity, even if it exited before the first sample.
                    write_record(
                        directory,
                        epoch,
                        service,
                        "started",
                        {
                            "identity": current,
                            "job_token": intent["job_token"],
                            "observed_time": now,
                        },
                    )
                    started = read_record(directory, epoch, service, "started")
                    rows[container["Id"]] = "active"
                    active_found = True
            else:
                rows[container["Id"]] = "unadmitted"
                reason = "candidate_startup_not_admitted"
        if started is not None and not active_found:
            reason = reason or "candidate_active_identity_missing"
        if (
            intent is not None
            and started is None
            and (now >= intent["deadline"] or result is not None)
        ):
            reason = "candidate_startup_not_observed"
    return {"containers": rows, "reason": reason}


def classify(directory, epoch, candidates, now):
    with transaction(directory):
        return _classify(directory, epoch, candidates, now)


def prepare(directory, epoch, candidates, services, job_token, deadline, now):
    with transaction(directory):
        view = _classify(directory, epoch, candidates, now)
        if view["reason"]:
            raise RuntimeError(view["reason"])
        for service in services:
            intent = read_record(directory, epoch, service, "activation")
            if intent is not None:
                # Compose dependencies already running are an idempotent prerequisite, never a restart waiver.
                if any(
                    c["Config"]["Labels"]["com.docker.compose.service"] == service
                    and view["containers"].get(c["Id"]) == "active"
                    and c["State"]["Status"] == "running"
                    for c in candidates
                ):
                    continue
                raise RuntimeError("startup_already_admitted_requires_rearm")
            write_record(
                directory,
                epoch,
                service,
                "activation",
                {
                    "job_token": job_token,
                    "deadline": deadline,
                    "release": epoch["release"],
                    "registered_time": now,
                },
            )


def complete(directory, job_token):
    # Called by the detached reaper immediately after Compose exits, before terminal success receipt.
    from . import epochs
    from .supervisor import load_registry

    registry = load_registry(directory)
    epoch = epochs.active(directory, registry)
    items = host.containers()
    candidates = host.candidate_containers(
        items, epochs.effective_registry(directory, registry)
    )
    sample = host.host_sample(epoch["release"])
    with transaction(directory):
        view = _classify(directory, epoch, candidates, time.time())
        for service in host.SERVICES - {"runner"}:
            intent = read_record(directory, epoch, service, "activation")
            if intent is not None and intent["job_token"] == job_token:
                write_record(
                    directory,
                    epoch,
                    service,
                    "activation-result",
                    {"job_token": job_token, "observed_time": time.time()},
                )
        if view["reason"]:
            raise RuntimeError(view["reason"])
        for service in host.SERVICES - {"runner"}:
            intent = read_record(directory, epoch, service, "activation")
            if (
                intent is not None
                and intent["job_token"] == job_token
                and read_record(directory, epoch, service, "started") is None
            ):
                raise RuntimeError("startup_completion_without_active_readback")

        reason, _ = host.guard_reason(
            epochs.effective_registry(directory, registry),
            items,
            sample["memory_available"],
            sample["disk_free"],
            None,
            time.time(),
            epoch["allocations"],
            _classify(directory, epoch, candidates, time.time()),
        )
        if reason:
            raise RuntimeError(reason)
