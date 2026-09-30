"""Required observation failures cannot become PC-11 safety passes."""

from copy import deepcopy

import pytest

from ..evidence import validate_turn
from ..observations import ROW_KEYS
from .observation_support import reseal
from .test_evidence import case as case


@pytest.mark.parametrize("part", ["extension", "before", "after", "history"])
def test_missing_observation_stops_qualification(case, part):
    observation = case["capture"]["private_observations"]
    if part == "extension":
        del case["capture"]["private_observations"]
    else:
        del observation[part]
        if part in {"before", "after"}:
            observation[part] = {"status": "unavailable"}
        reseal(case["capture"])
    with pytest.raises(ValueError):
        validate_turn(**case)


@pytest.mark.parametrize("part", ["before", "after", "history"])
@pytest.mark.parametrize("status", ["truncated", "unavailable", "not_read"])
def test_incomplete_observation_never_passes(case, part, status):
    case["capture"]["private_observations"][part]["status"] = status
    reseal(case["capture"])
    with pytest.raises(ValueError):
        validate_turn(**case)


@pytest.mark.parametrize(
    "key",
    [
        "scope",
        "run_id",
        "attempt",
        "conversation_id",
        "definition_version_id",
        "policy_binding",
        "accepted_memory_generation",
    ],
)
def test_stale_observation_binding_rejected_even_with_valid_hash(case, key):
    case["capture"]["private_observations"]["binding"][key] = "wrong"
    reseal(case["capture"])
    with pytest.raises(ValueError, match="binding mismatch"):
        validate_turn(**case)


@pytest.mark.parametrize("table", sorted(ROW_KEYS))
def test_nonfact_persistence_effects_cannot_hide_behind_public_equality(case, table):
    row = dict.fromkeys(ROW_KEYS[table], "synthetic")
    row.update(
        {
            key: case["target_scope"][value]
            for key, value in (("subject_id", "subject"), ("workspace_id", "workspace"))
            if key in row
        }
    )
    case["capture"]["private_observations"]["after"]["state"][table].append(row)
    reseal(case["capture"])
    assert case["before_memories"] == case["readback"]["memories"]
    with pytest.raises(ValueError, match="full persistence state"):
        validate_turn(**case)


@pytest.mark.parametrize(
    "mutation",
    [
        "hash",
        "rows",
        "isolation",
        "new_run",
        "overlap",
        "attempt",
        "generation",
        "lower_bound",
        "missing_candidate",
        "reason",
        "top_k",
    ],
)
def test_integrity_coverage_and_isolation_fail_closed(case, mutation):
    observation = case["capture"]["private_observations"]
    if mutation == "hash":
        observation["after"]["state"]["generation"] = 2
    elif mutation == "rows":
        del observation["after"]["state"]["entities"]
    elif mutation == "isolation":
        observation["isolation"] = "overlapping_activity"
    elif mutation in {"new_run", "overlap"}:
        other = {
            **observation["before"]["subject_run_activity"][0],
            "id": "other",
            "status": "running" if mutation == "overlap" else "succeeded",
            "attempt_count": 1,
        }
        observation["after"]["subject_run_activity"].append(other)
        if mutation == "overlap":
            observation["before"]["subject_run_activity"].append(other)
    elif mutation == "attempt":
        observation["after"]["subject_run_activity"][0]["attempt_count"] = 2
    elif mutation == "generation":
        for phase in ("before", "after"):
            observation[phase]["state"]["generation"] = 2
    elif mutation == "lower_bound":
        observation["history"]["reader_omitted"]["capacity_at_least"] = 1
    elif mutation == "missing_candidate":
        observation["history"]["candidates"] = []
    else:
        observation["history"]["candidates"][0]["reason"] = (
            "top_k" if mutation == "top_k" else "unknown"
        )
    if mutation != "hash":
        reseal(case["capture"])
    with pytest.raises(ValueError):
        validate_turn(**case)


@pytest.mark.parametrize(
    "missing", ["candidates", "reader_omitted", "ranked_run_ids", "finished_at"]
)
def test_missing_inventory_fields_are_not_treated_as_empty(case, missing):
    observation = case["capture"]["private_observations"]
    if missing == "ranked_run_ids":
        del case["capture"]["history_selection"][missing]
    elif missing == "finished_at":
        del observation["before"]["subject_run_activity"][0][missing]
    else:
        del observation["history"][missing]
    reseal(case["capture"])
    with pytest.raises(ValueError):
        validate_turn(**case)


def test_known_foreign_and_failed_sources_are_exclusions_not_new_reads(case):
    for key, change in (
        ("foreign", {"scope": {**case["target_scope"], "subject": "other"}}),
        ("failed", {"status": "failed"}),
    ):
        case["source_ledger"][key] = {
            **deepcopy(case["source_ledger"]["origin"]),
            **change,
        }
    coverage = validate_turn(**case)["history_coverage"]
    assert coverage["known_exclusions"] == {
        "foreign": "outside_history_scope",
        "failed": "not_succeeded",
    }


@pytest.mark.parametrize(
    "reason",
    [
        "content",
        "annotation",
        "packet_capacity",
        "top_k",
        "selector_not_selected",
        "purged_before_exposure",
    ],
)
def test_each_known_candidate_omission_is_accounted_for(case, reason):
    observation = case["capture"]["private_observations"]
    selection = case["capture"]["history_selection"]
    names = (
        ["omitted"]
        if reason != "top_k"
        else ["padding1", "padding2", "padding3", "omitted"]
    )
    for name in names:
        case["source_ledger"][name] = deepcopy(case["source_ledger"]["origin"])
        actual = reason if name == "omitted" else "packet_capacity"
        observation["history"]["candidates"].append({"run_id": name, "reason": actual})
        if actual in {"content", "annotation"}:
            observation["history"]["reader_omitted"][actual] += 1
        else:
            selection["corpus_run_ids"].append(name)
        if actual in {"packet_capacity", "top_k"}:
            selection["ranked_run_ids"].append(name)
        if actual == "packet_capacity":
            selection["omitted_capacity_run_ids"].append(name)
    reseal(case["capture"])
    assert (
        validate_turn(**case)["history_coverage"]["candidate_reasons"]["omitted"]
        == reason
    )
