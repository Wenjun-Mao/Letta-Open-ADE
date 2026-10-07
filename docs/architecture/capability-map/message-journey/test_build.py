"""Offline generation and inert-data tests for the moving chart."""

from pathlib import Path
import runpy


HERE = Path(__file__).resolve().parent
builder = runpy.run_path(str(HERE / "build.py"))


def test_generated_presentation_matches_source_and_has_no_network_dependencies():
    figure, evidence, inventory = builder["review"]["load"]()
    builder["review"]["validate"](figure, evidence, inventory)
    fragment = builder["fragment"](figure)
    assert (HERE / "ade-message-journey.html").read_text() == builder["standalone"](
        fragment
    )
    assert len(fragment.encode()) < 1_000_000
    assert "<!doctype" not in fragment
    assert "fetch(" not in fragment
    assert "<script src=" not in fragment
    assert "XMLHttpRequest" not in fragment
    assert "Copyright (c) 2025 Vectorize AI Inc." in fragment
    assert "\n<section id=" in fragment


def test_figure_strings_cannot_break_out_of_data_script():
    figure, _, _ = builder["review"]["load"]()
    figure["title"] = "</script><script>alert(1)</script>"
    fragment = builder["fragment"](figure)
    assert "</script><script>alert(1)" not in fragment
    assert "\\u003c/script" in fragment


def test_example_strings_are_escaped_independently_of_the_source_figure():
    figure, _, _ = builder["review"]["load"]()
    fragment = builder["fragment"](
        figure, {"caption": "</script><script>alert(2)</script>"}
    )
    assert "</script><script>alert(2)" not in fragment
    assert "\\u003c/script" in fragment
