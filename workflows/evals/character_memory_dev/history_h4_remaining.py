"""Bind the approved remaining H4 turns to the immutable first campaign."""

from __future__ import annotations

import json

from workflows.evals.deepseek_dev_smoke.isolation import ROOT

from .natural_live_results import sha256_file

ORIGINAL_MANIFEST = (
    ROOT
    / "workflows/evals/character_memory_dev/outputs/history-h4-live-20260926/manifest.json"
)
PROPOSAL = (
    ROOT
    / "workflows/evals/character_memory_dev/outputs/history-h4-offline-review-20260926/remaining-campaign-proposal.json"
)
ORIGINAL_SHA256 = "07228ca7c3642d3528c76db345ef5a14e2bd9463ada14858784872af1b9458a2"
PROPOSAL_SHA256 = "8aac6844cfab933f738913859efc833370df0d538720281d17e4cdabb0cd1476"


def validate_remaining(
    original: dict, proposal: dict, planned_cells: list[dict]
) -> list[dict]:
    """Derive the schedule from old unrun state, then require exact proposal agreement."""
    if (
        original["schema_version"] != 1
        or proposal["schema_version"] != 1
        or proposal["status"] != "proposal_only_no_dispatch"
        or proposal["original_manifest_sha256"] != ORIGINAL_SHA256
        or original["planned_cells"] != planned_cells
        or len(original["cells"]) != len(planned_cells)
    ):
        raise RuntimeError(
            "H4 remaining schedule source differs from approved original"
        )
    attempted = []
    remaining = []
    selected = []
    for planned, cell in zip(planned_cells, original["cells"], strict=True):
        if (cell["name"], cell["arm"]) != (planned["name"], planned["arm"]):
            raise RuntimeError("H4 original cell ordering changed")
        name, arm = cell["name"], cell["arm"]
        if cell["status"] == "unrun_after_stop":
            if cell.get("target", {}).get("status") != "unrun_after_stop":
                raise RuntimeError("H4 unrun target carries an attempted state")
            selected.append(planned)
            remaining.append(
                {"case": name, "arm": arm, "turn": "target", "dependency": None}
            )
            if planned.get("followup_scheduled"):
                if cell.get("followup", {}).get("status") != "unrun_dependency":
                    raise RuntimeError("H4 unrun followup has an unexpected state")
                remaining.append(
                    {
                        "case": name,
                        "arm": arm,
                        "turn": "followup",
                        "dependency": f"{name}:{arm}:target_committed",
                    }
                )
        else:
            attempted.append({"case": name, "arm": arm, "status": cell["status"]})
    if (
        attempted != proposal["excluded_attempted_cells"]
        or remaining != proposal["remaining_turns"]
        or len(attempted) != proposal["historical_attempted_native_turns"]
        or len(remaining) != proposal["historical_unrun_native_turns"]
        or len(selected) != 15
        or len(remaining) != 21
    ):
        raise RuntimeError("H4 proposed remaining turns differ from immutable history")
    return selected


def load_remaining(planned_cells: list[dict]) -> tuple[dict, dict, list[dict]]:
    if (
        sha256_file(ORIGINAL_MANIFEST) != ORIGINAL_SHA256
        or sha256_file(PROPOSAL) != PROPOSAL_SHA256
    ):
        raise RuntimeError("H4 approved original or proposal hash changed")
    original = json.loads(ORIGINAL_MANIFEST.read_text())
    proposal = json.loads(PROPOSAL.read_text())
    return original, proposal, validate_remaining(original, proposal, planned_cells)
