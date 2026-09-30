"""Fail-closed packet validation, separate from human semantic judgments.

The source ledger is independently read back, not inferred from model text.
Hashes detect stale/corrupt inputs, not maliciously rewritten provenance.
"""

from __future__ import annotations

import json

from .schedule import digest
from .observations import CONTRACT, checked_seal, validate_observations


def _generation_history(system: str) -> list:
    marker = "Historical evidence (read-only):\n"
    if marker not in system:
        return []
    if system.count(marker) != 1:
        raise ValueError("Duplicate historical packet section")
    # ADE appends curated-tool instructions after this JSON value. Parse the
    # value boundary, not the whole remainder or a permissive substring match.
    history, _end = json.JSONDecoder().raw_decode(system.split(marker, 1)[1])
    if not isinstance(history, list):
        raise ValueError("Malformed generation history")
    return history


def checked_capture(raw: bytes, *, sha256: str, run_id: str, policy: str) -> dict:
    if len(raw) > 2_000_000 or digest(raw) != sha256:
        raise ValueError("Capture hash mismatch")
    capture = json.loads(raw)
    if (
        capture.get("schema_version") != 1
        or capture.get("run_id") != run_id
        or capture.get("attempt") != 1
        or capture.get("policy_binding") != policy
    ):
        raise ValueError("Stale or incompatible capture binding")
    observation = capture.get("private_observations", {})
    if observation.get("contract") != CONTRACT:
        raise ValueError("Required private observations v1 missing or incompatible")
    checked_seal(observation)
    return capture


def validate_turn(
    *,
    capture: dict,
    readback: dict,
    before_memories: dict,
    expected_prompt: str,
    source_ledger: dict[str, dict],
    target_scope: dict,
    origin_run_id: str | None,
    archive_probe: bool = False,
    evidence_kind: str,
) -> dict:
    if evidence_kind not in {"scripted", "native"}:
        raise ValueError("Explicit native/scripted provenance required")
    if archive_probe and not origin_run_id:
        raise ValueError("Archive probe requires an origin identity")
    run, state = readback["run"], readback["state"]
    if (
        capture["run_id"] != run["id"]
        or run["attempt_count"] != 1
        or run["retry_count"] != 0
    ):
        raise ValueError("Run/capture attempt mismatch")
    if state["messages_truncated"]:
        raise ValueError("Incomplete independent readback")
    messages = [m for m in state["messages"] if m["run_id"] == run["id"]]
    terminal = capture["terminal_readback"]
    committed = run["status"] == "succeeded"
    if run["status"] not in {"succeeded", "failed", "cancelled"}:
        raise ValueError("Nonterminal evidence")
    expected_roles = ["user", "assistant"] if committed else ["user"]
    if (
        [m["role"] for m in messages] != expected_roles
        or messages[0]["content"] != expected_prompt
        or terminal["run_status"] != run["status"]
        or terminal["attempt_status"] != run["status"]
        or terminal["outcome"] != ("committed" if committed else "confirmed_rejection")
        or terminal["assistant_message_ids"] != [m["id"] for m in messages[1:]]
    ):
        raise ValueError("Terminal evidence does not match persisted messages")
    if committed and messages[1]["content"] != capture["candidate_visible_reply"]:
        raise ValueError("Candidate was not the delivered reply")
    if (
        before_memories != readback["memories"]
        or terminal["revision_ids"]
        or terminal["accepted_memory_generation"]
        != before_memories["memory_generation"]
        or terminal["observed_memory_generation"]
        != before_memories["memory_generation"]
    ):
        raise ValueError("Pure story changed user memory projection")
    observation = validate_observations(
        capture=capture,
        readback=readback,
        target_scope=target_scope,
        source_ledger=source_ledger,
    )
    selection = capture["history_selection"]
    if selection == {"stage": "absent"}:
        if (
            committed
            or capture.get("generation_requests") != {"stage": "absent"}
            or capture.get("reviewer_request") != {"stage": "absent"}
            or capture.get("generation", {"stage": "absent"}) != {"stage": "absent"}
        ):
            raise ValueError("Missing selection for exposed packets")
        return {
            "disposition": "rejected",
            "semantic": "unassessable",
            "evidence_kind": evidence_kind,
        }
    admitted = selection["admitted_run_ids"]
    corpus = selection["corpus_run_ids"]
    if len(set(admitted)) != len(admitted) or not set(admitted) <= set(corpus):
        raise ValueError("Invalid selection identities")
    for source_id in observation["candidate_reasons"]:
        source = source_ledger.get(source_id)
        if (
            not source
            or source["status"] != "succeeded"
            or source["scope"] != target_scope
        ):
            raise ValueError("Uncommitted or cross-scope source")
        if source["ordinal"] >= readback["ordinal"]:
            raise ValueError("Source chronology mismatch")
        if [m["role"] for m in source["messages"]] != ["user", "assistant"]:
            raise ValueError("Malformed source roles")
        for message in source["messages"]:
            if digest(message["content"].encode()) != message["content_sha256"]:
                raise ValueError("Corrupt source content")
    review_request = capture["reviewer_request"]
    requests = capture["generation_requests"]
    if review_request == {"stage": "absent"}:
        if committed:
            raise ValueError("Missing reviewer request")
        # A failed generation can still have exposed history. Parse its actual
        # system packet instead of laundering leakage through early rejection.
        history = []
        if isinstance(requests, list) and requests:
            system = requests[0]["messages"][0]["content"]
            history = _generation_history(system)
    else:
        if [m["role"] for m in review_request["messages"]] != ["system", "user"]:
            raise ValueError("Malformed reviewer roles")
        review = json.loads(review_request["messages"][1]["content"])
        if review["current_user"]["content"] != expected_prompt:
            raise ValueError("Stale reviewer current turn")
        history = review["history"]
    if len(history) != len(admitted):
        raise ValueError("Selection/packet disagreement")
    for window, source_id in zip(history, admitted, strict=True):
        source = source_ledger[source_id]
        if (
            window["run_id"] != source_id
            or window["conversation_id"] != source["conversation_id"]
        ):
            raise ValueError("Packet source identity mismatch")
        if (
            window["archived"] != source["archived"]
            or window["definition_version_id"] != source["definition_version_id"]
            or [(m["role"], m["content"]) for m in window["messages"]]
            != [(m["role"], m["content"]) for m in source["messages"]]
        ):
            raise ValueError("Packet differs from independent source")
    if not isinstance(requests, list) or not requests:
        if committed or history:
            raise ValueError("Missing generation capture")
        requests = []
    if any(
        not request["messages"] or request["messages"][0]["role"] != "system"
        for request in requests
    ):
        raise ValueError("Malformed generation roles")
    for request in requests:
        users = [m for m in request["messages"] if m["role"] == "user"]
        if not users or users[-1]["content"] != expected_prompt:
            raise ValueError("Stale generation current turn")
        system = request["messages"][0]["content"]
        generated_history = _generation_history(system)
        if generated_history != history:
            raise ValueError("Generation/reviewer history mismatch")
    if committed and not isinstance(
        capture.get("reviewer_decision", {}).get("decisions"), list
    ):
        raise ValueError("Missing reviewer decision")
    if not committed:
        return {
            "disposition": "rejected",
            "semantic": "unassessable",
            "evidence_kind": evidence_kind,
        }
    if origin_run_id is not None:
        origin = source_ledger.get(origin_run_id)
        if not origin or origin["status"] != "succeeded":
            raise ValueError("Origin absent or uncommitted")
        if archive_probe:
            if (
                origin_run_id not in admitted
                or not origin["archived"]
                or origin["definition_version_id"] == readback["definition_version_id"]
            ):
                raise ValueError(
                    "Archive probe requires admitted archived prior-version origin"
                )
            if any(not source_ledger[key]["archived"] for key in admitted):
                raise ValueError(
                    "Unarchived intermediate echo cannot qualify archive recall"
                )
    return {
        "disposition": "committed",
        "evidence_kind": evidence_kind,
        "semantic": "not_measured"
        if evidence_kind == "scripted"
        else "human_review_required",
        "entity_coverage": "all_subject_entities_including_orphans",
        "full_persistence": "independent_complete_before_after_unchanged",
        "history_coverage": observation,
        "admitted_run_ids": admitted,
    }
