"""Source-pinned revision-5 activation clock. No runtime override or extension."""

ACTIVATION_ID = "hindsight-semantic-follow-up-2026-10-11"
STARTED = 1791749563
TARGET = 1791767563
DEADLINE = 1791771163
# Reserve the approved final 45 minutes for bounded shutdown, verification and reporting.
STOP_MARGIN = 2700
WORK_CUTOFF = DEADLINE - STOP_MARGIN


def receipt() -> dict:
    """Exact clock identity captured in a newly initialized campaign registry."""
    return {
        "activation_id": ACTIVATION_ID,
        "started": STARTED,
        "target": TARGET,
        "work_cutoff": WORK_CUTOFF,
        "hard_deadline": DEADLINE,
        "stop_margin": STOP_MARGIN,
    }
