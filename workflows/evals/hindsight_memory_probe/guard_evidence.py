"""Redacted immutable evidence for a supervisor safety-stop decision."""

from __future__ import annotations

from . import host_guard as host
from . import lifecycle
from .receipts import CaptureFailure, ReceiptStore


def _admission_projection(intent):
    return {
        key: intent[key]
        for key in ("service", "job_token", "release", "deadline", "registered_time")
    }


def publish(directory, registry, epoch, candidates, observation, reason, sampled_at):
    """Persist the exact redacted lifecycle/guard inputs without raw Docker inspect data."""
    receipt = {
        "registry_sha256": registry["registry_sha256"],
        "epoch_sha256": epoch["sha256"],
        "sampled_at": sampled_at,
        "guard_reason": reason,
        "lifecycle": observation["view"],
        "admissions": {
            service: _admission_projection(intent)
            for service, intent in observation["admissions"].items()
        },
        "candidates": [
            {
                "baseline": host.baseline_projection(container),
                "dormant": lifecycle.dormant_projection(container),
            }
            for container in candidates
        ],
    }
    try:
        ReceiptStore(directory).write(
            f"epoch-{epoch['index']:04d}-guard-failure.json", receipt
        )
        return True
    except CaptureFailure:
        # The safety stop still proceeds; unavailable evidence is not represented as saved.
        return False
