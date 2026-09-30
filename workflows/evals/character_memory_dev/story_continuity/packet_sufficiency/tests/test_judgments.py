"""Check the non-blind label freeze before any new-control selection."""

from workflows.evals.character_memory_dev.story_continuity.packet_sufficiency.judgments import (
    assess_packet,
    load_judgments,
)


def test_judgments_keep_exposure_and_report_specific_alternatives():
    data = load_judgments()
    assert data["contract"] == "packet-sufficiency-nonblind-v1"
    assert "exposed_context" in data["status"]
    c08 = data["cases"][7]
    assert c08["answer_routes"][1]["reports"] == ["B"]
    assert c08["answer_routes"][1]["condition"]
    assert c08["answer_routes"][0]["sets"] == [["E01", "E06"]]


def test_answer_support_does_not_imply_correction_visibility():
    c01 = load_judgments()["cases"][0]
    result = assess_packet(c01, ["E01"])
    assert result["answer_routes"][0]["supported"]
    assert not result["visibility"][0]["supported"]
    dangling = assess_packet(c01, ["E04"])["dependencies"][0]
    assert dangling["trigger_present"] and not dangling["supported"]


def test_conditional_routes_are_not_promoted_to_common_unconditional_support():
    c08 = load_judgments()["cases"][7]
    routes = assess_packet(c08, ["E02", "E05", "E06"])["answer_routes"]
    assert not routes[0]["supported"]
    assert (
        routes[1]["supported"]
        and routes[1]["condition"]
        and routes[1]["reports"] == ["B"]
    )


def test_empty_history_is_sufficient_only_for_present_choice():
    for case in load_judgments()["cases"]:
        routes = assess_packet(case, [])["answer_routes"]
        assert any(route["supported"] for route in routes) == (case["id"] == "C03")


def test_unrelated_and_other_episode_are_separate():
    c09 = load_judgments()["cases"][8]
    result = assess_packet(c09, ["E02", "E07"])
    assert result["other_episode_admitted"] == ["E02"]
    assert result["unrelated_admitted"] == ["E07"]
