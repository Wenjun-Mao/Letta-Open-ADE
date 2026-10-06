"""Synthetic offline regression checks for the documentation review gate."""

import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest


review = runpy.run_path(str(Path(__file__).with_name("review.py")))


@pytest.fixture
def specification():
    return review["load"]()


def test_current_specification_is_source_backed_and_compatible(specification):
    figure, evidence, inventory = specification
    counts = review["validate"](figure, evidence, inventory)
    assert counts["tours"] == 7
    assert counts["source_files"] >= 20
    assert figure["props"]["autoplay"] is False


def test_unknown_renderer_field_is_rejected(specification):
    figure, evidence, inventory = specification
    figure["props"]["edges"][0]["status"] = "current"
    with pytest.raises(ValueError, match="Unsupported interfig fields"):
        review["validate"](figure, evidence, inventory)


def test_cli_emits_complete_figure_without_rendering(specification):
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("review.py")), "--emit"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == specification[0]


def test_module_cannot_move_to_another_subsystem(specification):
    figure, evidence, inventory = specification
    next(item for item in inventory["entries"] if item["id"] == "MEM-02")[
        "subsystem"
    ] = "Retention & Updates"
    with pytest.raises(ValueError, match="Subsystem ownership drift"):
        review["validate"](figure, evidence, inventory)


def test_experimental_edge_cannot_leak_into_current_tour(specification):
    figure, evidence, inventory = specification
    figure["props"]["steps"][0]["flow"].append({"edges": "reference-reply"})
    with pytest.raises(ValueError, match="Experimental edge leaked"):
        review["validate"](figure, evidence, inventory)


def test_future_tour_cannot_animate_current_code(specification):
    figure, evidence, inventory = specification
    figure["props"]["steps"][-1]["flow"].append({"edges": "submit"})
    with pytest.raises(ValueError, match="Unimplemented tour animates"):
        review["validate"](figure, evidence, inventory)


def test_deferred_external_tools_cannot_acquire_execution_edge(specification):
    figure, evidence, inventory = specification
    figure["props"]["edges"][0]["to"] = "external"
    with pytest.raises(ValueError, match="Deferred node"):
        review["validate"](figure, evidence, inventory)


def test_all_edges_require_provenance(specification):
    figure, evidence, inventory = specification
    evidence["claims"][0]["edges"].remove("submit")
    with pytest.raises(ValueError, match="Edge lacks source provenance"):
        review["validate"](figure, evidence, inventory)


def test_source_anchor_drift_is_rejected(specification):
    figure, evidence, inventory = specification
    evidence["claims"][0]["sources"][0]["anchor"] = "invented_runtime_boundary"
    with pytest.raises(ValueError, match="Missing source anchor"):
        review["validate"](figure, evidence, inventory)


def test_source_escape_is_rejected(specification):
    figure, evidence, inventory = specification
    evidence["claims"][0]["sources"][0]["path"] = "repo:../private.txt"
    with pytest.raises(ValueError, match="Source escapes repository"):
        review["validate"](figure, evidence, inventory)


def test_stale_inventory_status_is_rejected(specification):
    figure, evidence, inventory = specification
    next(item for item in inventory["entries"] if item["id"] == "MEM-03")["status"] = (
        "implemented"
    )
    with pytest.raises(ValueError, match="Status drift"):
        review["validate"](figure, evidence, inventory)


def test_parallel_animation_cannot_imply_extra_concurrency(specification):
    figure, evidence, inventory = specification
    figure["props"]["steps"][0]["flow"].append({"edges": ["submit", "fact-query"]})
    with pytest.raises(ValueError, match="Parallel beat"):
        review["validate"](figure, evidence, inventory)


def test_unsupported_reverse_packet_is_rejected(specification):
    figure, evidence, inventory = specification
    figure["props"]["steps"][0]["flow"].append(
        {"edges": {"edge": "submit", "back": True}}
    )
    with pytest.raises(ValueError, match="explicit return edges"):
        review["validate"](figure, evidence, inventory)


def test_atomic_finalization_and_candidate_review_boundary(specification):
    figure, evidence, inventory = specification
    review["validate"](figure, evidence, inventory)
    main = figure["props"]["steps"][0]
    grouped = [
        beat["edges"] for beat in main["flow"] if isinstance(beat.get("edges"), list)
    ]
    assert grouped == [
        ["save-user", "save-accepted-run"],
        ["commit-facts", "commit-index", "commit-dialogue", "commit-run"],
    ]
    assert "reference-reply" not in {
        beat.get("edges") for beat in main["flow"] if isinstance(beat.get("edges"), str)
    }
    assert evidence["node_bindings"]["behavior"] == ["CHAR-03", "CHAR-04"]
