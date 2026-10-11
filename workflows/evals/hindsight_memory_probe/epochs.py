"""Audited stop/rearm/allocation epochs; campaign timestamps and ownership never change."""

import hashlib
import json
import time
from pathlib import Path

from . import host_guard as host
from . import releases
from .receipts import ReceiptStore
from .campaign_clock import WORK_CUTOFF

INITIAL_ALLOCATIONS = {
    "db": {"memory": host.GIB, "cpu": 0.25},
    "hindsight": {"memory": 6 * host.GIB, "cpu": 1.0},
    "model-router": {"memory": host.GIB // 4, "cpu": 0.125},
    "runner": {"memory": host.GIB // 2, "cpu": 0.125},
}


def digest(value):
    return hashlib.sha256(
        json.dumps(
            {k: v for k, v in value.items() if k != "sha256"}, sort_keys=True
        ).encode()
    ).hexdigest()


def validate_allocations(value, sample):
    if set(value) != host.SERVICES:
        raise RuntimeError("allocation_services_changed")
    for caps in value.values():
        if (
            set(caps) != {"memory", "cpu"}
            or not isinstance(caps["memory"], int)
            or caps["memory"] <= 0
        ):
            raise RuntimeError("invalid_allocation")
        if (
            not isinstance(caps["cpu"], (int, float))
            or not 0 < caps["cpu"] <= sample["cpus"]
        ):
            raise RuntimeError("invalid_allocation")
    if (
        sum(c["memory"] for c in value.values()) + 1.5 * host.GIB
        > sample["memory_available"]
    ):
        raise RuntimeError("insufficient_allocation_memory_headroom")
    if (
        sum(c["cpu"] for c in value.values()) + 0.5 > sample["cpus"]
        or sample["disk_free"] < 25 * host.GIB
    ):
        raise RuntimeError("insufficient_allocation_cpu_or_disk")


def active(directory, registry):
    previous, last = None, None
    files = sorted(directory.glob("epoch-[0-9][0-9][0-9][0-9].json"))
    for index, path in enumerate(files, 1):
        value = json.loads(path.read_text())
        if (
            value["index"] != index
            or value["registry_sha256"] != registry["registry_sha256"]
            or value["previous_sha256"] != previous
            or value["sha256"] != digest(value)
        ):
            raise RuntimeError("epoch_chain_conflict")
        previous, last = value["sha256"], value
    if last is None:
        raise RuntimeError("operating_epoch_missing")
    return last


def stopped_path(directory, epoch):
    return directory / f"epoch-{epoch['index']:04d}.stopped.json"


def append(
    directory,
    registry,
    allocations,
    sample,
    reason,
    diagnosis=None,
    now=None,
    release=None,
):
    now = time.time() if now is None else now
    if now >= WORK_CUTOFF:
        raise RuntimeError("hard_deadline_cannot_rearm")
    validate_allocations(allocations, sample)
    if list(directory.glob("epoch-[0-9][0-9][0-9][0-9].json")):
        previous = active(directory, registry)
        if not stopped_path(directory, previous).exists() or diagnosis is None:
            raise RuntimeError("rearm_requires_stopped_epoch_and_diagnosis")
        diagnosis = Path(diagnosis).resolve()
        if (
            directory.resolve() not in diagnosis.parents
            or not diagnosis.is_file()
            or not diagnosis.read_bytes()
        ):
            raise RuntimeError("private_diagnosis_receipt_required")
        diagnosis_hash = hashlib.sha256(diagnosis.read_bytes()).hexdigest()
        previous_hash, index = previous["sha256"], previous["index"] + 1
    else:
        diagnosis_hash, previous_hash, index = None, None, 1
    if (
        not reason
        or len(reason) > 128
        or not all(c.isalnum() or c in "-_" for c in reason)
    ):
        raise RuntimeError("safe_reason_code_required")
    selected_release = str(releases.validate_path(release or registry["release"]))
    if release is not None:
        releases.verify(selected_release)
    value = {
        "release": selected_release,
        "index": index,
        "registry_sha256": registry["registry_sha256"],
        "previous_sha256": previous_hash,
        "allocations": allocations,
        "sample": sample,
        "reason": reason,
        "diagnosis_sha256": diagnosis_hash,
        "time": now,
    }
    value["sha256"] = digest(value)
    ReceiptStore(directory).write(f"epoch-{index:04d}.json", value)
    return value


def effective_registry(directory, registry):
    # Chain verification is mandatory before reading the explicit release allowlist.
    active(directory, registry)
    values = [
        json.loads(p.read_text())
        for p in sorted(directory.glob("epoch-[0-9][0-9][0-9][0-9].json"))
    ]
    return {
        **registry,
        "authorized_releases": sorted(
            {registry["release"], *(v["release"] for v in values)}
        ),
    }
