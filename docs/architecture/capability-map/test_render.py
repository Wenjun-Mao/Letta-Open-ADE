"""Offline checks for the documentation inventory and generated views."""

import copy
import json
from pathlib import Path
import runpy
import sys
from xml.etree import ElementTree

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
renderer = runpy.run_path(str(HERE / "render.py"))


@pytest.fixture
def inventory():
    return json.loads((HERE / "inventory.json").read_text())


def test_current_inventory_and_views_are_complete(inventory):
    counts = renderer["validate"](inventory)
    assert counts["entries"] == 35
    assert counts["records"] == 6
    assert counts["flows"] == 3
    assert counts["sources"] > 90
    assert (HERE / "inventory.md").read_text() == renderer["render_markdown"](inventory)
    assert (HERE / "ade-capability-map.html").read_text() == renderer["render_html"](
        inventory, (HERE / "template.html").read_text()
    )
    assert (HERE / "ade-capability-map.svg").read_text() == renderer["render_svg"](
        inventory
    )


def test_static_overview_has_every_piece_and_only_declared_edges(inventory):
    tree = ElementTree.fromstring(renderer["render_svg"](inventory))
    declared = {item["id"] for item in [*inventory["entries"], *inventory["records"]]}
    ids = [node.get("id") for node in tree.iter() if node.get("id") in declared]
    assert set(ids) == declared
    assert len(ids) == len(declared)
    edges = {(a, b) for flow in inventory["flows"] for a, b, _ in flow["edges"]}
    for node in tree.iter():
        if node.get("data-from"):
            assert (node.get("data-from"), node.get("data-to")) in edges


def test_static_and_browser_views_name_support_and_records_positively(inventory):
    tree = ElementTree.fromstring(renderer["render_svg"](inventory))
    text = " ".join(tree.itertext())
    assert "Platform support / Runtime, storage, model access" in text
    assert "Persisted memory records / ADE PostgreSQL" in text
    for item in inventory["entries"]:
        if item["domain"] == "support":
            assert f"{item['id']} / {item['subsystem']}" in text
    html = renderer["render_html"](inventory, (HERE / "template.html").read_text())
    assert "__FLOW_MODEL__" not in html
    assert "globalThis.AdeFlowModel" in html
    assert "Copyright (c) 2025 Vectorize AI Inc." in html
    assert "outside L1-L3 capability containment" not in html


@pytest.mark.parametrize("marker", ["", "__FLOW_MODEL____FLOW_MODEL__"])
def test_missing_or_duplicate_routing_marker_fails(inventory, marker):
    template = (HERE / "template.html").read_text().replace("__FLOW_MODEL__", marker)
    with pytest.raises(ValueError, match="one routing marker"):
        renderer["render_html"](inventory, template)


def test_character_refinement_preserves_existing_topology(inventory):
    character = next(item for item in inventory["domains"] if item["id"] == "character")
    assert character["subsystems"] == ["Persona Definition", "Conversation Behavior"]
    entries = {
        item["id"]: item
        for item in inventory["entries"]
        if item["domain"] == "character"
    }
    assert set(entries) == {"CHAR-01", "CHAR-02", "CHAR-03", "CHAR-04", "CHAR-05"}
    assert entries["CHAR-03"]["status"] == entries["CHAR-04"]["status"] == "partial"
    recall = next(flow for flow in inventory["flows"] if flow["id"] == "recall")
    assert ["CHAR-03", "CHAR-04", "same generation call"] in recall["edges"]


def test_duplicate_id_fails(inventory):
    inventory["entries"][1]["id"] = inventory["entries"][0]["id"]
    with pytest.raises(ValueError, match="Duplicate entry"):
        renderer["validate"](inventory)


@pytest.mark.parametrize(
    "field,value",
    [("domain", "new-domain"), ("subsystem", "Unknown"), ("status", "released")],
)
def test_unknown_classification_fails(inventory, field, value):
    inventory["entries"][0][field] = value
    with pytest.raises(ValueError, match="Unknown"):
        renderer["validate"](inventory)


def test_missing_source_fails(inventory):
    inventory["entries"][0]["code"] = ["runtime:does-not-exist.py"]
    with pytest.raises(ValueError, match="Missing source"):
        renderer["validate"](inventory)


def test_repository_escape_fails(inventory):
    with pytest.raises(ValueError, match="escapes repository"):
        renderer["source_path"]("repo:../outside.py", inventory)


def test_existing_code_cannot_be_asserted_without_source(inventory):
    inventory["entries"][0]["code"] = []
    with pytest.raises(ValueError, match="lacks source"):
        renderer["validate"](inventory)


def test_deferred_piece_does_not_imply_implementation(inventory):
    deferred = next(item for item in inventory["entries"] if item["id"] == "MEM-10")
    assert deferred["status"] == "deferred"
    assert deferred["code"] == deferred["tests"] == []
    section = (
        renderer["render_markdown"](inventory)
        .split("### MEM-10:")[1]
        .split("### UI-01:")[0]
    )
    assert "Implementation: **deferred**." in section


def test_unknown_flow_endpoint_fails(inventory):
    inventory["flows"][0]["edges"][0][1] = "MISSING"
    with pytest.raises(ValueError, match="Invalid edge"):
        renderer["validate"](inventory)


def test_data_is_embedded_not_loaded_from_a_service(inventory):
    template = (HERE / "template.html").read_text()
    assert "fetch(" not in template
    assert "<script src=" not in template
    hostile = copy.deepcopy(inventory)
    hostile["entries"][0]["gap"] = "</script><script>alert(1)</script>"
    html = renderer["render_html"](hostile, template)
    assert "</script><script>alert(1)" not in html
    assert "\\u003c/script" in html


@pytest.mark.parametrize(
    "template", ["no marker", "__INVENTORY_DATA____INVENTORY_DATA__"]
)
def test_missing_or_duplicate_data_marker_fails(inventory, template):
    with pytest.raises(ValueError, match="one data marker"):
        renderer["render_html"](inventory, template)
