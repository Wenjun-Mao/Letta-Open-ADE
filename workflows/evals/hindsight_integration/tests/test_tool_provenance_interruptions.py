"""A failed attempt may preserve an in-flight call, never a fabricated result."""

import copy

import pytest

from ..tool_provenance import validate_tool_provenance
from .tool_provenance_fixtures import BANK, memory, serial_capture, tool_events


def interrupted_capture(*, prior_completed=False):
    item = {
        "id": "call-a",
        "arguments": {"query": "prior history"},
        "results": [memory()],
    }
    group = [item, {**item, "id": "call-b"}] if prior_completed else [item]
    chain, records = serial_capture([group])
    pending = tool_events(records)[-2]
    return chain[:1], records[: records.index(pending) + 1]


@pytest.mark.parametrize("prior_completed", [False, True])
def test_failed_attempt_accepts_only_observed_terminal_inflight_prefix(prior_completed):
    chain, records = interrupted_capture(prior_completed=prior_completed)
    assert validate_tool_provenance(chain, records, BANK, successful=False) == {}


def test_successful_attempt_cannot_qualify_an_unfinished_lookup():
    chain, records = interrupted_capture()
    with pytest.raises(ValueError, match="tool_lookup_unfinished"):
        validate_tool_provenance(chain, records, BANK, successful=True)


@pytest.mark.parametrize("with_continuation", [False, True])
def test_unfinished_lookup_cannot_be_followed_by_any_model_dispatch(with_continuation):
    chain, records = interrupted_capture()
    complete_chain, complete_records = serial_capture()
    dispatch = copy.deepcopy(complete_records[-2])
    dispatch["sequence"] = len(records) + 1
    records.append(dispatch)
    if with_continuation:
        chain.append(complete_chain[-1])
    with pytest.raises(ValueError):
        validate_tool_provenance(chain, records, BANK, successful=False)


def test_unfinished_lookup_still_requires_its_parent_call_arguments():
    chain, records = interrupted_capture()
    records[-1]["value"]["query"] = "another query"
    with pytest.raises(ValueError, match="tool_lookup_arguments_mismatch"):
        validate_tool_provenance(chain, records, BANK, successful=False)


def test_unfinished_lookup_cannot_be_orphaned_or_precede_its_parent_response():
    chain, records = interrupted_capture()
    with pytest.raises(ValueError, match="unmatched_tool_lookup"):
        validate_tool_provenance([], records, BANK, successful=False)
    records.insert(3, records.pop())
    for sequence, row in enumerate(records, 1):
        row["sequence"] = sequence
    with pytest.raises(ValueError, match="tool_lookup_outside_parent_request_window"):
        validate_tool_provenance(chain, records, BANK, successful=False)


def test_failed_lookup_cannot_be_followed_by_another_inflight_lookup():
    chain, records = interrupted_capture(prior_completed=True)
    tool_events(records)[1]["type"] = "memory_lookup.failed"
    with pytest.raises(ValueError, match="tool_lookup_continued_after_failure"):
        validate_tool_provenance(chain, records, BANK, successful=False)
