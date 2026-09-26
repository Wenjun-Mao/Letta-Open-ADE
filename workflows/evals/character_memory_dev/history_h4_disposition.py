"""Terminal evidence and pair comparability for native H4 cells."""

from __future__ import annotations


class CampaignStop(RuntimeError):
    """A native integrity failure invalidates the remaining finite schedule."""


OBSERVABLE_REJECTION_DETAILS = frozenset({"conversation_tool_step_budget_exceeded"})


def _classify_turn(turn: dict, *, name: str, arm: str, label: str) -> str:
    """Require terminal evidence and completed captures for every attempted turn."""
    captures = turn.get("provider_captures") or []
    evidence_complete = (
        turn.get("terminal_safety") == "verified"
        and bool(turn.get("attempt_sha256"))
        and captures
        and all(receipt.get("status") == "completed" for receipt in captures)
    )
    if evidence_complete and (
        turn.get("status") == "committed"
        and turn.get("terminal_outcome") == "committed"
        and turn.get("base_packet") is not None
    ):
        return "committed"
    delta = turn.get("observed_delta") or {}
    no_commit = (
        delta.get("generation_advance") == 0
        and delta.get("revision_count") == 0
        and delta.get("entity_additions") == []
        and delta.get("run_revisions") == []
        and delta.get("other_revision_ids") == []
    )
    if (
        evidence_complete
        and no_commit
        and (
            turn.get("status") == "rejected"
            and turn.get("terminal_outcome") == "confirmed_rejection"
            and (turn.get("run") or {}).get("status") == "failed"
            and turn.get("failure_detail_code") in OBSERVABLE_REJECTION_DETAILS
        )
    ):
        return "bounded_rejection"
    raise CampaignStop(
        f"{name}/{arm}/{label} has invalid native evidence: "
        f"{turn.get('failure') or turn.get('status')}"
    )


def _classify_cell(result: dict) -> str:
    """Retain the one-turn contract for controls and existing unit checks."""
    if result.get("status") not in {"observed", "rejected"}:
        raise CampaignStop(
            f"{result['name']}/{result['arm']} failed before target completion"
        )
    target = result.get("target") or {}
    disposition = _classify_turn(
        target, name=result["name"], arm=result["arm"], label="target"
    )
    if result["status"] != ("observed" if disposition == "committed" else "rejected"):
        raise CampaignStop(
            f"{result['name']}/{result['arm']} cell status contradicts target"
        )
    return disposition


def _classify_cell_turns(result: dict) -> list[dict]:
    captures = result.get("setup_captures") or []
    if any(receipt.get("status") != "completed" for receipt in captures):
        raise CampaignStop(f"{result['name']}/{result['arm']} setup capture incomplete")
    if (result.get("setup") or {}).get("embedding_dispatches", 0) and not captures:
        raise CampaignStop(f"{result['name']}/{result['arm']} setup capture missing")
    target = _classify_cell(result)
    dispositions = [
        {
            "name": result["name"],
            "arm": result["arm"],
            "turn": "target",
            "disposition": target,
        }
    ]
    if "followup" in result:
        followup = result["followup"]
        if target == "bounded_rejection":
            if followup.get("status") != "unrun_dependency":
                raise CampaignStop("H4 followup ran without a committed target")
            followup_disposition = "dependency_skip"
        else:
            followup_disposition = _classify_turn(
                followup, name=result["name"], arm=result["arm"], label="followup"
            )
        dispositions.append(
            {
                "name": result["name"],
                "arm": result["arm"],
                "turn": "followup",
                "disposition": followup_disposition,
            }
        )
    return dispositions


def _paired_packet_check(case_id: str, paired: list[dict]) -> dict:
    left = paired[0].get("target", {}).get("base_packet")
    right = paired[1].get("target", {}).get("base_packet")
    comparable = left is not None and right is not None
    equal = left == right if comparable else None
    return {
        "case_id": case_id,
        "comparable": comparable,
        "base_packet_equal": equal,
        "status": (
            "incomplete_bounded_rejection"
            if not comparable
            else "matched"
            if equal
            else "mismatched"
        ),
    }
