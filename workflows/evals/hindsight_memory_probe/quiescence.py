"""Durable stop admission precedes bounded registration drain; no post-stop handshake."""

import fcntl
import json
import os
import time
from contextlib import contextmanager

from . import epochs
from .campaign_clock import WORK_CUTOFF
from .receipts import ReceiptStore


def stop_path(directory, epoch):
    return directory / f"epoch-{epoch['index']:04d}.stop-admission.json"


@contextmanager
def bounded_lease(directory, name, seconds, required=True):
    fd = os.open(directory / name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    acquired = False
    try:
        until = time.monotonic() + seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                if time.monotonic() >= until:
                    if required:
                        raise RuntimeError("quiescence_lease_timeout") from None
                    break
                time.sleep(0.05)
        yield acquired
    finally:
        os.close(fd)


def admit_stop(directory, epoch, reason):
    # Never hold this lock while waiting for jobs.lock; launcher order is jobs -> admission.
    with bounded_lease(directory, "admission.lock", 20):
        path = stop_path(directory, epoch)
        if path.exists():
            if json.loads(path.read_text())["epoch_sha256"] != epoch["sha256"]:
                raise RuntimeError("stop_admission_epoch_conflict")
        else:
            ReceiptStore(directory).write(
                path.name,
                {
                    "epoch_sha256": epoch["sha256"],
                    "reason": reason,
                    "time": time.time(),
                },
            )


def require_open(directory, registry, epoch):
    from .supervisor import load_registry

    if (
        time.time() >= WORK_CUTOFF
        or load_registry(directory) != registry
        or epochs.active(directory, registry) != epoch
        or stop_path(directory, epoch).exists()
        or epochs.stopped_path(directory, epoch).exists()
        or (directory / f"epoch-{epoch['index']:04d}.pause-request.json").exists()
    ):
        raise RuntimeError("epoch_stopping_or_dispatch_deadline_elapsed")


@contextmanager
def dispatch_admission(directory, registry, epoch):
    with bounded_lease(directory, "admission.lock", 20):
        require_open(directory, registry, epoch)
        yield
