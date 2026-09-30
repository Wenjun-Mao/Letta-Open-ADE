"""Preserve returned reports and verify quoted text, not semantic ground truth."""

from __future__ import annotations

import hashlib
import json
import re

import pytest

from workflows.evals.character_memory_dev.story_continuity.packet_sufficiency.packet import (
    DIRECTORY,
    load_inputs,
)


REPORTS = DIRECTORY / "reports"
RECEIPT = json.loads((REPORTS / "receipt-2026-09-30.json").read_bytes())


def test_returned_reports_do_not_satisfy_clean_session_gate():
    raw = (DIRECTORY / "REVIEW_PACKET.md").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RECEIPT["packet_sha256"]
    git_blob = b"blob " + str(len(raw)).encode() + b"\0" + raw
    assert hashlib.sha1(git_blob).hexdigest() == RECEIPT["packet_git_blob_sha1"]
    assert RECEIPT["clean_session_requirement_satisfied"] is False
    assert RECEIPT["human_validation"] is False
    assert RECEIPT["cross_report_independence_verified"] is False
    assert RECEIPT["new_control_selections_computed_at_receipt"] is False


@pytest.mark.parametrize("report", RECEIPT["reports"], ids=lambda r: r["id"])
def test_original_report_bytes_case_coverage_and_same_case_quoted_text(report):
    raw = (REPORTS / report["path"]).read_bytes()
    assert len(raw) == report["byte_count"]
    assert hashlib.sha256(raw).hexdigest() == report["sha256"]
    text = raw.decode()
    assert RECEIPT["packet_commit"] in text
    _, cases, _ = load_inputs()
    by_id = {case["id"]: case for case in cases}
    sections = list(re.finditer(r"(?ms)^## (C\d{2})[^\n]*\n(.*?)(?=^## |\Z)", text))
    assert [match[1] for match in sections] == report["covered_cases"] == list(by_id)
    quotation_count = 0
    for match in sections:
        case_id, body = match.groups()
        assert re.findall(r"(?m)^### (\d)\. ", body) == list("12345678")
        case = by_id[case_id]
        sources = [case["query"]] + [
            row[role] for row in case["exchanges"] for role in ("user", "assistant")
        ]
        # This verifies quotation bytes within the case, not citation-role mapping
        # or the reasoning attached to a quote. Those need source review.
        for quote in re.findall("“([^”]+)”", body):
            if not re.search(r"[\u3400-\u9fff]", quote):
                continue
            quotation_count += 1
            assert any(quote in source for source in sources), (case_id, quote)
    assert quotation_count == report["mandarin_quote_occurrences_checked"]
    assert report["source_text_mismatches"] == 0
