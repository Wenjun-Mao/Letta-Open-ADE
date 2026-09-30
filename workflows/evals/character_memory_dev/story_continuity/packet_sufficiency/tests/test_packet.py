"""Portable preparation checks, not independent semantic judgments."""

from __future__ import annotations

import hashlib
import json
import shutil

import pytest

from workflows.evals.character_memory_dev.story_continuity.packet_sufficiency.packet import (
    DIRECTORY,
    checked_bytes,
    load_inputs,
    render_packet,
)


def test_frozen_packet_is_exact_and_complete():
    context, cases, _ = load_inputs()
    assert len(cases) == 10
    assert context["local_suffix"] == context["saved_facts"] == []
    assert render_packet() == (DIRECTORY / "REVIEW_PACKET.md").read_text()
    assert len([row for case in cases for row in case["exchanges"]]) == 69
    originals = {
        name: json.loads(path.read_bytes())["cases"]
        for name, path in {
            "historical": DIRECTORY.parent / "retrieval_diversity/cases.json",
            "controls": DIRECTORY / "controls.json",
        }.items()
    }
    mapping = json.loads((DIRECTORY / "mapping.json").read_bytes())
    for case in cases:
        entry = mapping[case["id"]]
        source = next(c for c in originals[entry["fixture"]] if c["id"] == entry["id"])
        assert case["query"] == source["query"]
        assert [(row["user"], row["assistant"]) for row in case["exchanges"]] == [
            (user, assistant) for _, user, assistant in source["exchanges"]
        ]
        assert set(case) == {"id", "query", "exchanges"}
        for index, row in enumerate(case["exchanges"], 1):
            assert set(row) == {"id", "at", "user", "assistant"}
            assert row["id"] == f"E{index:02d}"
            assert row["at"] == f"2026-09-{index:02d}T12:00:00+00:00"


def test_review_packet_excludes_operator_labels_and_results():
    packet = render_packet()
    mapping = json.loads((DIRECTORY / "mapping.json").read_bytes())
    for entry in mapping.values():
        assert entry["id"] not in packet
    for forbidden in (
        "evidence_groups",
        "irrelevant_ids",
        "rationale",
        "baseline",
        "Jaccard",
        "top-four",
        "2/7",
        "7/7",
        "observed.json",
    ):
        assert forbidden not in packet


def test_new_inputs_have_more_than_four_distinct_pairs_and_no_query_echo():
    controls = json.loads((DIRECTORY / "controls.json").read_bytes())["cases"]
    assert len(controls) == 2
    for case in controls:
        assert set(case) == {"id", "query", "exchanges"}
        pairs = [(row[1], row[2]) for row in case["exchanges"]]
        assert len(set(pairs)) == len(pairs) > 4
        assert len({assistant for _, assistant in pairs}) > 4
        assert all(case["query"] not in text for pair in pairs for text in pair)


def test_changed_input_bytes_fail_closed(tmp_path):
    path = tmp_path / "input.json"
    original = b'{"source":"frozen"}'
    path.write_bytes(original)
    digest = hashlib.sha256(original).hexdigest()
    assert checked_bytes(path, digest) == original
    path.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="Frozen audit input differs"):
        checked_bytes(path, digest)


@pytest.mark.parametrize(
    "name",
    ["controls.json", "context.json", "mapping.json", "RUBRIC.md", "freeze.json"],
)
def test_renderer_rejects_tampered_source(tmp_path, name):
    directory = tmp_path / "packet_sufficiency"
    shutil.copytree(DIRECTORY, directory)
    shutil.copytree(
        DIRECTORY.parent / "retrieval_diversity", tmp_path / "retrieval_diversity"
    )
    with (directory / name).open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="Frozen audit input differs"):
        render_packet(directory)
