"""Frozen exposed-context annotations, kept outside selector inputs."""

from __future__ import annotations

import json

from .packet import DIRECTORY, checked_bytes, load_inputs


JUDGMENTS_SHA256 = "af4931509e356e45d2151fd0d54e9e0105be7a54131b3571a8b88053e530b817"


def load_judgments() -> dict:
    data = json.loads(checked_bytes(DIRECTORY / "judgments.json", JUDGMENTS_SHA256))
    receipt = json.loads((DIRECTORY / "reports/receipt-2026-09-30.json").read_bytes())
    for report in receipt["reports"]:
        checked_bytes(
            DIRECTORY / "reports" / report["path"], data["report_sha256"][report["id"]]
        )
    _, cases, _ = load_inputs()
    if [case["id"] for case in data["cases"]] != [case["id"] for case in cases]:
        raise ValueError("Judgments must cover the frozen cases in order")
    for case, judgment in zip(cases, data["cases"], strict=True):
        ids = {row["id"] for row in case["exchanges"]}
        for field in ("answer_routes", "visibility", "dependencies", "optional"):
            for item in judgment[field]:
                if not item["sets"]:
                    raise ValueError("At least one explicit alternative is required")
                for alternative in item["sets"]:
                    if (
                        not set(alternative) <= ids
                        or len(set(alternative)) != len(alternative)
                        or len(alternative) > 4
                    ):
                        raise ValueError(
                            "Reference sets require unique, bounded source IDs"
                        )
                if field == "dependencies" and item["trigger"] not in ids:
                    raise ValueError("Dependency trigger is outside the corpus")
        if not set(judgment["unrelated"] + judgment["other_episode"]) <= ids:
            raise ValueError("Relevance classification is outside the corpus")
        if set(judgment["unrelated"]) & set(judgment["other_episode"]):
            raise ValueError("Unrelated and other-episode classes overlap")
    return data


def assess_packet(judgment: dict, admitted: list[str]) -> dict:
    selected = set(admitted)

    def assess(item):
        return {
            **item,
            "supported": any(set(group) <= selected for group in item["sets"]),
            "missing_by_alternative": [
                sorted(set(group) - selected) for group in item["sets"]
            ],
        }

    return {
        "answer_routes": [assess(route) for route in judgment["answer_routes"]],
        "visibility": [assess(item) for item in judgment["visibility"]],
        "dependencies": [
            {**assess(item), "trigger_present": item["trigger"] in selected}
            for item in judgment["dependencies"]
        ],
        "optional": [assess(item) for item in judgment["optional"]],
        "other_episode_admitted": sorted(selected & set(judgment["other_episode"])),
        "unrelated_admitted": sorted(selected & set(judgment["unrelated"])),
        "unresolved": judgment["uncertainty"],
    }
