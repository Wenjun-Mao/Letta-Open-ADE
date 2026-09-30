"""PC-11 requires private observations v1; historical capture v1 alone is not proof.

This workflow consumes JSON only. Runtime persistence remains the readback owner.
"""

import json

from .schedule import digest

CONTRACT = "ade-private-evaluation-observations-v1"
STATE_KEYS = {"generation", "facts", "entities", "revisions", "sources", "predecessors"}
ROW_KEYS = {
    "facts": set(
        "id workspace_id subject_id entity_id normalized_key fact_type qualifier value status assertion_schema_version version current_revision_id created_at updated_at".split()
    ),
    "entities": set("id workspace_id subject_id kind label created_at".split()),
    "revisions": set(
        "id fact_id workspace_id subject_id operation fact_version value run_id action_id reason created_at".split()
    ),
    "sources": set(
        "id revision_id message_id start_char end_char quote message_sha256 authority_role".split()
    ),
    "predecessors": {"revision_id", "predecessor_revision_id"},
}
ACTIVITY_KEYS = {
    "id",
    "status",
    "attempt_count",
    "created_at",
    "started_at",
    "finished_at",
}


def checked_seal(value: dict) -> None:
    if not isinstance(value, dict):
        raise ValueError("Missing private observation")
    body = {key: item for key, item in value.items() if key != "sha256"}
    raw = json.dumps(
        body, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()
    if value.get("sha256") != digest(raw):
        raise ValueError("Private observation hash mismatch")


def _snapshot(snapshot: dict, *, scope: dict, run_id: str, status: str) -> list:
    if snapshot.get("status") != "complete":
        raise ValueError("Incomplete private persistence observation")
    checked_seal(snapshot)
    state = snapshot.get("state", {})
    if set(state) != STATE_KEYS or not isinstance(state["generation"], int):
        raise ValueError("Incomplete full persistence state")
    for table, columns in ROW_KEYS.items():
        rows = state[table]
        if not isinstance(rows, list) or len(rows) > 512:
            raise ValueError("Invalid full persistence rows")
        identities = []
        for row in rows:
            if set(row) != columns:
                raise ValueError("Incomplete full persistence row")
            if "subject_id" in columns and (
                row["subject_id"] != scope["subject"]
                or row["workspace_id"] != scope["workspace"]
            ):
                raise ValueError("Cross-scope persistence observation")
            identities.append(
                row.get(
                    "id", (row.get("revision_id"), row.get("predecessor_revision_id"))
                )
            )
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate persistence identity")
    activity = snapshot.get("subject_run_activity")
    if not isinstance(activity, list) or len(activity) > 512:
        raise ValueError("Missing bounded isolation inventory")
    if any(set(row) != ACTIVITY_KEYS for row in activity) or len(
        {row["id"] for row in activity}
    ) != len(activity):
        raise ValueError("Incomplete or duplicate isolation inventory")
    current = [row for row in activity if row["id"] == run_id]
    if (
        len(current) != 1
        or current[0]["attempt_count"] != 1
        or current[0]["status"] != status
    ):
        raise ValueError("Private observation attempt/status mismatch")
    others = [row for row in activity if row["id"] != run_id]
    if any(row["status"] in {"pending", "running"} for row in others):
        raise ValueError("Concurrent subject activity is not isolated evidence")
    return others


def validate_observations(
    *, capture: dict, readback: dict, target_scope: dict, source_ledger: dict
) -> dict:
    observation = capture.get("private_observations", {})
    if observation.get("contract") != CONTRACT:
        raise ValueError("Required private observations v1 missing or incompatible")
    checked_seal(observation)
    run = readback["run"]
    terminal = capture["terminal_readback"]
    expected = {
        "scope": target_scope,
        "run_id": run["id"],
        "attempt": capture["attempt"],
        "conversation_id": run["conversation_id"],
        "definition_version_id": readback["definition_version_id"],
        "policy_binding": capture["policy_binding"],
        "accepted_memory_generation": terminal["accepted_memory_generation"],
    }
    if observation.get("binding") != expected or capture["attempt"] != 1:
        raise ValueError("Private observation scope/run/attempt binding mismatch")
    before, after = observation.get("before", {}), observation.get("after", {})
    prior = _snapshot(before, scope=target_scope, run_id=run["id"], status="running")
    later = _snapshot(after, scope=target_scope, run_id=run["id"], status=run["status"])
    if prior != later or observation.get("isolation") != "isolated":
        raise ValueError("Concurrent or unconfirmed observation is not isolated proof")
    if (
        before["state"] != after["state"]
        or before["state"]["generation"] != terminal["accepted_memory_generation"]
        or after["state"]["generation"] != terminal["observed_memory_generation"]
    ):
        raise ValueError("Pure story changed full persistence state or generation")
    return _history(
        observation.get("history", {}), capture, readback, target_scope, source_ledger
    )


def _history(
    history: dict, capture: dict, readback: dict, scope: dict, ledger: dict
) -> dict:
    if (
        history.get("status") != "complete"
        or history.get("universe") != "scoped_completed_pairs"
    ):
        raise ValueError("History inventory incomplete, unavailable or not read")
    if set(history) != {
        "status",
        "universe",
        "limit",
        "candidates",
        "reader_omitted",
    } or not isinstance(history["candidates"], list):
        raise ValueError("Missing history inventory fields")
    candidates = history["candidates"]
    if any(set(row) != {"run_id", "reason"} for row in candidates):
        raise ValueError("Malformed history candidate")
    if history.get("limit") != 128 or len(candidates) > 128:
        raise ValueError("History inventory bound mismatch")
    by_id = {row["run_id"]: row["reason"] for row in candidates}
    if len(by_id) != len(candidates):
        raise ValueError("Duplicate history candidate")
    expected, excluded = set(), {}
    for source_id, source in ledger.items():
        if source["ordinal"] >= readback["ordinal"]:
            raise ValueError("Source chronology mismatch")
        if source["scope"] != scope:
            excluded[source_id] = "outside_history_scope"
        elif source["status"] != "succeeded":
            excluded[source_id] = "not_succeeded"
        else:
            expected.add(source_id)
    if set(by_id) != expected:
        raise ValueError(
            "History inventory lacks known candidates or contains cross-scope sources"
        )
    selection = capture["history_selection"]
    for key in (
        "corpus_run_ids",
        "admitted_run_ids",
        "ranked_run_ids",
        "omitted_capacity_run_ids",
    ):
        values = selection.get(key)
        if not isinstance(values, list) or len(values) != len(set(values)):
            raise ValueError("Missing or duplicate selection inventory")
    corpus = selection["corpus_run_ids"]
    admitted = selection["admitted_run_ids"]
    ranked = selection["ranked_run_ids"]
    capacity = selection["omitted_capacity_run_ids"]
    allowed = {
        "admitted",
        "content",
        "annotation",
        "packet_capacity",
        "top_k",
        "selector_not_selected",
        "purged_before_exposure",
    }
    if any(reason not in allowed for reason in by_id.values()):
        raise ValueError("Unknown history omission reason")
    if set(corpus) != {
        key for key, reason in by_id.items() if reason not in {"content", "annotation"}
    }:
        raise ValueError("Reader inventory/corpus disagreement")
    if set(admitted) != {key for key, reason in by_id.items() if reason == "admitted"}:
        raise ValueError("History admission reason mismatch")
    if set(capacity) != {
        key for key, reason in by_id.items() if reason == "packet_capacity"
    }:
        raise ValueError("History capacity reason mismatch")
    if len(ranked) != len(set(ranked)) or not set(ranked) <= set(corpus):
        raise ValueError("Invalid ranking inventory")
    for key, reason in by_id.items():
        if (
            reason in {"selector_not_selected", "purged_before_exposure"}
            and key in ranked
        ):
            raise ValueError("Invalid selector/purge omission")
        if reason == "top_k" and key not in ranked[4:]:
            raise ValueError("Invalid top-k omission")
        if reason in {"admitted", "packet_capacity"} and key not in ranked[:4]:
            raise ValueError("Invalid admitted/capacity rank")
    counts = history.get("reader_omitted")
    if counts != {
        "capacity_at_least": 0,
        "content": list(by_id.values()).count("content"),
        "annotation": list(by_id.values()).count("annotation"),
    }:
        raise ValueError("Reader omission counts incomplete or inconsistent")
    return {"candidate_reasons": by_id, "known_exclusions": excluded}
