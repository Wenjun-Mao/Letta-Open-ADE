"""P1 owned BuildKit cancellation observer; positive sentinel plus post-cancel host readback."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from . import host_guard as host
from .campaign_clock import DEADLINE
from .receipts import ReceiptStore

SENTINEL = "ADE_PROBE_BUILDKIT_SENTINEL"
CONTRACT = "ade-owned-buildkit-cancellation-v1"


def sentinel_processes(token, proc_root=Path("/proc")):
    found = []
    for directory in proc_root.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            argv = (directory / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
            if (
                argv[-2:] == [SENTINEL.encode(), token.encode()]
                and b"/probe-cancellation.py" in argv
            ):
                identity = host.proc_identity(int(directory.name), proc_root)
                if identity is None:
                    raise RuntimeError("build_sentinel_identity_unavailable")
                found.append(identity)
        except PermissionError:
            # Visibility must be demonstrated by an actual positive sentinel before any absence proof.
            raise RuntimeError("host_process_visibility_incomplete") from None
        except FileNotFoundError:
            continue
    return found


def observe(directory, pid):
    from .supervisor import jobs

    matches = [
        j
        for j in jobs(directory)
        if j["identity"]["pid"] == pid and j["kind"] == "build-cancel"
    ]
    if len(matches) != 1:
        raise RuntimeError("unique_registered_cancellation_build_required")
    job = matches[0]
    token = job["build_sentinel"]
    if token != job["token"]:
        raise RuntimeError("build_sentinel_registration_conflict")
    store = ReceiptStore(directory)
    seen, absent, samples = [], 0, []
    until = min(DEADLINE - 30, job["deadline"] + 45)
    while time.time() < until:
        current = sentinel_processes(token)
        client_alive = bool(host.tagged_processes(token))
        row = {
            "time": time.time(),
            "sentinel_identities": current,
            "client_alive": client_alive,
        }
        samples.append(row)
        if current and not seen:
            seen = current
            store.write(f"build-cancel-{token}.seen.json", row)
        if seen and not current and not client_alive and time.time() >= job["deadline"]:
            absent += 1
            if absent == 3:
                from .supervisor import load_registry
                from .epochs import active, stopped_path

                registry = load_registry(directory)
                epoch = active(directory, registry)
                stopped = json.loads(stopped_path(directory, epoch).read_text())
                if (
                    epoch["sha256"] != job["epoch_sha256"]
                    or stopped["reason"] != "owned_process_deadline_elapsed"
                    or stopped["time"] < job["deadline"]
                ):
                    raise RuntimeError("guard_deadline_cancellation_not_observed")
                proof = {
                    "contract": CONTRACT,
                    "job_token": token,
                    "tag": f"ade-hindsight-probe-cancel:{token}",
                    "hard_deadline": DEADLINE,
                    "registered_deadline": job["deadline"],
                    "observed_sentinel": seen,
                    "no_sentinel_samples": absent,
                    "samples": samples,
                    "outcome": "daemon_cancelled",
                    "job_sha256": hashlib.sha256(
                        (directory / f"job-{token}.json").read_bytes()
                    ).hexdigest(),
                }
                store.write(f"build-cancel-{token}.proof.json", proof)
                print(
                    f"owned_build_daemon_cancellation_observed receipt=build-cancel-{token}.proof.json"
                )
                return proof
        else:
            absent = 0
        time.sleep(1)
    store.write(
        f"build-cancel-{token}.failure.json",
        {
            "contract": CONTRACT,
            "job_token": token,
            "outcome": "sentinel_not_seen_or_daemon_still_active",
            "samples": samples,
        },
    )
    raise RuntimeError("owned_build_cancellation_not_qualified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--pid", type=int, required=True)
    args = parser.parse_args()
    try:
        observe(args.state, args.pid)
    except Exception:
        raise SystemExit("owned_build_cancellation_not_qualified") from None
