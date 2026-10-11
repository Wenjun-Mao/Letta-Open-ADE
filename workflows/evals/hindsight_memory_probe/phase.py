"""Serial operation annotation; immutable intent plus atomic active phase pointer."""

import argparse
import json
import os
import re
import time
import uuid
from pathlib import Path

from .receipts import ReceiptStore

PHASES = ["startup", "retain", "consolidation", "recall", "character"]


def set_phase(directory, phase, operation_id):
    if phase not in PHASES or not re.fullmatch("[A-Za-z0-9_-]{1,96}", operation_id):
        raise RuntimeError("invalid_phase")
    store = ReceiptStore(directory)
    value = {"phase": phase, "operation_id": operation_id, "time_ns": time.time_ns()}
    name = f"phase-{uuid.uuid4().hex}.intent.json"
    store.write(name, value)
    descriptor = os.open(
        directory / ".phase.tmp",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(directory / ".phase.tmp", directory / "phase.json")
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument("--operation-id", required=True)
    args = parser.parse_args()
    set_phase(args.receipts, args.phase, args.operation_id)
