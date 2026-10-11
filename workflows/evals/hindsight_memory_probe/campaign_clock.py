"""Source-pinned revision-5 activation clock. No runtime override or extension."""

from pathlib import Path

ACTIVATION_ID = "hindsight-semantic-follow-up-2026-10-11"
STARTED = 1791749563
TARGET = 1791767563
DEADLINE = 1791771163
# Reserve the approved final 45 minutes for bounded shutdown, verification and reporting.
STOP_MARGIN = 2700
WORK_CUTOFF = DEADLINE - STOP_MARGIN
RECEIPTS_RELATIVE = Path("activations") / ACTIVATION_ID / "receipts"


def activation_receipts_root(private_root: str | Path) -> Path:
    """Resolve the activation-specific capture root under the retained private root."""
    root = Path(private_root).absolute()
    receipts = root / RECEIPTS_RELATIVE
    for path in (
        root,
        root / "activations",
        root / "activations" / ACTIVATION_ID,
        receipts,
        receipts / "supervisor",
    ):
        if path.is_symlink():
            raise RuntimeError("activation_namespace_symlink")
    return receipts


def activation_namespace(release: str | Path) -> dict[str, str]:
    """Return the only host namespace admitted for this activation's state."""
    project_root = Path(release).resolve().parent.parent
    receipts = activation_receipts_root(project_root / "private")
    return {
        "activation_id": ACTIVATION_ID,
        "receipts_root": str(receipts),
        "supervisor_state": str(receipts / "supervisor"),
    }


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
