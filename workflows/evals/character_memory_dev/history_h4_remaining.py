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
SECOND_MANIFEST = (
    ROOT
    / "workflows/evals/character_memory_dev/outputs/history-h4-remaining-live-20260926/manifest.json"
)
SECOND_SHA256 = "e309d643542406446cd349962bc3dee598f22ac49bfaaceaf8b6fd1e606ddb6a"
AFTER_TWO_PROPOSAL = (
    ROOT
    / "workflows/evals/character_memory_dev/outputs/history-h4-offline-review-20260926/remaining-after-two-campaigns-proposal.json"
)
AFTER_TWO_PROPOSAL_SHA256 = (
    "fd0a24c10cc8dd53e10247fb99df3dcd42616a8952c81ca1d7bfc0eccd8e1177"
)


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


def validate_remaining_after_two(
    original: dict,
    first_proposal: dict,
    second: dict,
    proposal: dict,
    planned_cells: list[dict],
) -> list[dict]:
    first_selected = validate_remaining(original, first_proposal, planned_cells)
    if (
        second.get("schema_version") != 1
        or second.get("status") != "stopped_structural"
        or second.get("original_manifest_sha256") != ORIGINAL_SHA256
        or second.get("proposal_sha256") != PROPOSAL_SHA256
        or second.get("planned_cells") != first_selected
        or second.get("planned_turns") != first_proposal["remaining_turns"]
        or len(second.get("cells", [])) != len(first_selected)
        or proposal.get("schema_version") != 1
        or proposal.get("status") != "proposal_only_no_dispatch"
        or proposal.get("original_manifest_sha256") != ORIGINAL_SHA256
        or proposal.get("remaining_21_manifest_sha256") != SECOND_SHA256
        or not any(
            check.get("case_id") == "invalidated_ended"
            and check.get("status") == "mismatched"
            and check.get("base_packet_equal") is False
            for check in second.get("pair_checks", [])
        )
    ):
        raise RuntimeError("H4 second campaign or approval binding changed")

    attempted = []
    attempted_keys = set()
    for campaign, manifest in (("original", original), ("remaining_21", second)):
        for planned, cell in zip(
            manifest["planned_cells"], manifest["cells"], strict=True
        ):
            if (cell["name"], cell["arm"]) != (planned["name"], planned["arm"]):
                raise RuntimeError("H4 campaign cell order changed")
            key = (cell["name"], cell["arm"], "target")
            if cell["status"] == "unrun_after_stop":
                if cell.get("target", {}).get("status") != "unrun_after_stop":
                    raise RuntimeError("H4 unrun cell carries an attempted target")
                if (
                    planned.get("followup_scheduled")
                    and cell.get("followup", {}).get("status") != "unrun_dependency"
                ):
                    raise RuntimeError("H4 unrun followup carries an attempted state")
                continue
            if key in attempted_keys:
                raise RuntimeError("H4 previously attempted target was rerun")
            attempted_keys.add(key)
            attempted.append(
                {
                    "case": cell["name"],
                    "arm": cell["arm"],
                    "turn": "target",
                    "campaign": campaign,
                    "status": cell["status"],
                }
            )
            if planned.get("followup_scheduled"):
                raise RuntimeError("H4 prior followup attempt is outside this schedule")

    remaining = []
    selected = []
    for planned in planned_cells:
        name, arm = planned["name"], planned["arm"]
        if (name, arm, "target") in attempted_keys:
            continue
        selected.append(planned)
        remaining.append(
            {"case": name, "arm": arm, "turn": "target", "dependency": None}
        )
        if planned.get("followup_scheduled"):
            remaining.append(
                {
                    "case": name,
                    "arm": arm,
                    "turn": "followup",
                    "dependency": f"{name}:{arm}:target_committed",
                }
            )
    if (
        attempted != proposal.get("excluded_attempted_turns")
        or remaining != proposal.get("remaining_turns")
        or proposal.get("historical_planned_native_turns") != 32
        or proposal.get("historical_attempted_native_turns") != 14
        or proposal.get("historical_unrun_native_turns") != 18
        or len(selected) != 12
        or len(remaining) != 18
    ):
        raise RuntimeError("H4 18-turn proposal differs from both immutable manifests")
    return selected


def load_remaining_after_two(
    planned_cells: list[dict],
) -> tuple[dict, dict, dict, list[dict]]:
    original, first_proposal, _ = load_remaining(planned_cells)
    if (
        sha256_file(SECOND_MANIFEST) != SECOND_SHA256
        or sha256_file(AFTER_TWO_PROPOSAL) != AFTER_TWO_PROPOSAL_SHA256
    ):
        raise RuntimeError("H4 second manifest or 18-turn proposal hash changed")
    second = json.loads(SECOND_MANIFEST.read_text())
    proposal = json.loads(AFTER_TWO_PROPOSAL.read_text())
    selected = validate_remaining_after_two(
        original, first_proposal, second, proposal, planned_cells
    )
    return original, second, proposal, selected
