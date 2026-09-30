"""Synthetic campaign state for portable schedule tests, never live evidence."""

from copy import deepcopy

from workflows.evals.character_memory_dev.history_h4_campaign import _planned_cells
from workflows.evals.character_memory_dev.history_h4_remaining import (
    ORIGINAL_SHA256,
    PROPOSAL_SHA256,
    SECOND_SHA256,
)
from workflows.evals.character_memory_dev.history_h4_run import load_frozen_h4_contract


def synthetic_schedules() -> tuple[list[dict], dict, dict, dict, dict]:
    contract, fixture = load_frozen_h4_contract()
    planned = _planned_cells(contract, fixture)
    original = {
        "schema_version": 1,
        "planned_cells": deepcopy(planned),
        "cells": [
            _cell(cell, attempted=index < 11) for index, cell in enumerate(planned)
        ],
    }
    first_proposal = {
        "schema_version": 1,
        "status": "proposal_only_no_dispatch",
        "original_manifest_sha256": ORIGINAL_SHA256,
        "excluded_attempted_cells": [
            {"case": cell["name"], "arm": cell["arm"], "status": "observed"}
            for cell in planned[:11]
        ],
        "remaining_turns": _turns(planned[11:]),
        "historical_attempted_native_turns": 11,
        "historical_unrun_native_turns": 21,
    }
    second = {
        "schema_version": 1,
        "status": "stopped_structural",
        "original_manifest_sha256": ORIGINAL_SHA256,
        "proposal_sha256": PROPOSAL_SHA256,
        "planned_cells": deepcopy(planned[11:]),
        "planned_turns": deepcopy(first_proposal["remaining_turns"]),
        "cells": [
            _cell(cell, attempted=index < 3) for index, cell in enumerate(planned[11:])
        ],
        "pair_checks": [
            {
                "case_id": "invalidated_ended",
                "status": "mismatched",
                "base_packet_equal": False,
            }
        ],
    }
    after_two = {
        "schema_version": 1,
        "status": "proposal_only_no_dispatch",
        "original_manifest_sha256": ORIGINAL_SHA256,
        "remaining_21_manifest_sha256": SECOND_SHA256,
        "excluded_attempted_turns": [
            {
                "case": cell["name"],
                "arm": cell["arm"],
                "turn": "target",
                "campaign": "original" if index < 11 else "remaining_21",
                "status": "observed",
            }
            for index, cell in enumerate(planned[:14])
        ],
        "remaining_turns": _turns(planned[14:]),
        "historical_planned_native_turns": 32,
        "historical_attempted_native_turns": 14,
        "historical_unrun_native_turns": 18,
    }
    return planned, original, first_proposal, second, after_two


def _cell(planned: dict, *, attempted: bool) -> dict:
    cell = {
        "name": planned["name"],
        "arm": planned["arm"],
        "status": "observed" if attempted else "unrun_after_stop",
        "target": {"status": "committed" if attempted else "unrun_after_stop"},
    }
    if planned.get("followup_scheduled"):
        cell["followup"] = {"status": "unrun_dependency"}
    return cell


def _turns(cells: list[dict]) -> list[dict]:
    turns = []
    for cell in cells:
        name, arm = cell["name"], cell["arm"]
        turns.append({"case": name, "arm": arm, "turn": "target", "dependency": None})
        if cell.get("followup_scheduled"):
            turns.append(
                {
                    "case": name,
                    "arm": arm,
                    "turn": "followup",
                    "dependency": f"{name}:{arm}:target_committed",
                }
            )
    return turns
