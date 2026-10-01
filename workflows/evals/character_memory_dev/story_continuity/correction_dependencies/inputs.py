"""Frozen pre-selection transcripts and author labels; standard-library only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[4]
FREEZE_SHA256 = "902c6c72ceb2e15e52737e5550bbee054ee7be76cdee25cfddd6d9ce9edb062b"
VARIANTS = ("self_contained", "antecedent_dependent")


def checked_bytes(path: Path, expected: str) -> bytes:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"Frozen correction-dependency input differs: {path.name}")
    return raw


def frozen_inputs(directory: Path) -> dict[str, bytes]:
    freeze = json.loads(checked_bytes(directory / "freeze.json", FREEZE_SHA256))
    if freeze["contract"] != "correction-dependencies-input-v1":
        raise ValueError("Unknown correction-dependency contract")
    for relative, expected in freeze["runtime_sources"].items():
        checked_bytes(ROOT / relative, expected)
    for relative, expected in freeze["historical_artifacts"].items():
        checked_bytes(ROOT / relative, expected)
    return {
        name: checked_bytes(directory / spec["path"], spec["sha256"])
        for name, spec in freeze["inputs"].items()
    }


def expand_cases(context: dict, corpus: dict) -> list[dict]:
    if (
        context["contract"] != "correction-dependencies-input-v1"
        or corpus["contract"] != "correction-dependencies-input-v1"
    ):
        raise ValueError("Unknown input context")
    if any(context[key] for key in ("local_suffix", "saved_facts", "related_entities")):
        raise ValueError("This controlled study requires empty saved/local context")
    families = corpus["families"]
    if [family["id"] for family in families] != ["P01", "P02", "P03"]:
        raise ValueError("Exactly three ordered episode families are required")
    if [family["dimension"] for family in families] != [
        "day",
        "location",
        "carried_item",
    ]:
        raise ValueError("The frozen episode dimensions differ")
    cases = []
    for index, family in enumerate(families):
        if not isinstance(family["query"], str) or not family["query"].strip():
            raise ValueError("Current question must be nonempty")
        rows = family["exchanges"]
        if [row["id"] for row in rows] != [f"E{i:02d}" for i in range(1, 9)]:
            raise ValueError("Each family requires eight complete ordered windows")
        for offset, variant in enumerate(VARIANTS, 1):
            sources = []
            for order, row in enumerate(rows, 1):
                expected = {
                    "id",
                    "user",
                    "assistant_variants" if order == 7 else "assistant",
                }
                if set(row) != expected:
                    raise ValueError("Only the correction can have variant text")
                if order == 7:
                    if set(row["assistant_variants"]) != set(VARIANTS):
                        raise ValueError("Exactly two correction variants are required")
                    assistant = row["assistant_variants"][variant]
                else:
                    assistant = row["assistant"]
                if not all(
                    isinstance(text, str) and text.strip()
                    for text in (row["user"], assistant)
                ):
                    raise ValueError("Complete nonempty U/A text is required")
                sources.append(
                    {
                        "id": row["id"],
                        "user": row["user"],
                        "assistant": assistant,
                        "user_at": f"2026-09-29T12:{order:02d}:00+00:00",
                        "at": f"2026-09-29T12:{order:02d}:01+00:00",
                        "user_sequence": order * 2 - 1,
                        "assistant_sequence": order * 2,
                    }
                )
            if len({(row["user"], row["assistant"]) for row in sources}) != 8:
                raise ValueError("Distinct source pairs are required")
            if len({row["assistant"] for row in sources[1:5]}) != 4:
                raise ValueError("Mistaken retellings cannot be exact copies")
            cases.append(
                {
                    "id": f"D{index * 2 + offset:02d}",
                    "conversation_id": f"synthetic-archive-{family['id']}",
                    "query": family["query"],
                    "exchanges": sources,
                }
            )
        if cases[-2]["exchanges"][6] == cases[-1]["exchanges"][6]:
            raise ValueError("The two correction texts must differ")
    return cases


def load_inputs(directory: Path = DIRECTORY) -> tuple[dict, list[dict]]:
    raw = frozen_inputs(directory)
    context, corpus = json.loads(raw["context"]), json.loads(raw["corpus"])
    return context, expand_cases(context, corpus)


def validate_judgments(data: dict, cases: list[dict]) -> list[dict]:
    if data["contract"] != "correction-dependencies-judgments-v1":
        raise ValueError("Unknown annotation contract")
    if data["annotation_kind"] != "nonblind_author_agent_before_new_case_scoring":
        raise ValueError("Author exposure must remain explicit")
    if [row["id"] for row in data["families"]] != ["P01", "P02", "P03"]:
        raise ValueError("Annotations must cover three ordered pairs")
    expanded = []
    for index, family in enumerate(data["families"]):
        pair = cases[index * 2 : index * 2 + 2]
        if family["cases"] != dict(
            zip(VARIANTS, [case["id"] for case in pair], strict=True)
        ):
            raise ValueError("Annotation case mapping differs")
        for variant, case in zip(VARIANTS, pair, strict=True):
            sources = {row["id"]: row for row in case["exchanges"]}
            for quote in family["quotes"]:
                if quote.get("variant", variant) != variant:
                    continue
                if (
                    quote["role"] not in {"user", "assistant"}
                    or quote["source"] not in sources
                ):
                    raise ValueError("Quote source/role is outside the corpus")
                if sources[quote["source"]][quote["role"]] != quote["text"]:
                    raise ValueError(
                        "Annotation quote differs from the complete source"
                    )
            value = family["restored_value"]
            if (
                not value
                or value in case["query"]
                or any(value in row["user"] for row in sources.values())
            ):
                raise ValueError("Restored answer leaks into current/user text")
            named_sources = {
                row["id"] for row in sources.values() if value in row["assistant"]
            }
            expected = {"E01", "E07"} if variant == "self_contained" else {"E01"}
            if named_sources != expected:
                raise ValueError(
                    "Restored answer must occur only in its declared sources"
                )
            groups = [
                *family["answer_routes"][variant],
                *family["correction_explanation"][variant],
                *family["correction_intent"],
                *family["mistaken_retelling"],
                *family["optional_detail"],
            ]
            for group in groups:
                if (
                    not group
                    or len(set(group)) != len(group)
                    or len(group) > 4
                    or not set(group) <= sources.keys()
                ):
                    raise ValueError(
                        "References require unique bounded complete sources"
                    )
            categories = family["unrelated"] + family["other_episode"]
            if (
                len(set(categories)) != len(categories)
                or not set(categories) <= sources.keys()
            ):
                raise ValueError("Admission classes must be disjoint corpus sources")
            dependency = family["dependency"]
            if (
                dependency["trigger"] not in sources
                or dependency["antecedent"] not in sources
            ):
                raise ValueError("Dependency source is outside the corpus")
            for challenge in family["deletion_challenges"]:
                if (
                    not set(challenge["sources"]) <= sources.keys()
                    or challenge["remove"] not in challenge["sources"]
                    or not challenge["loss"].strip()
                ):
                    raise ValueError(
                        "Deletion challenge must name a source and lost claim"
                    )
            expanded.append(
                {
                    **family,
                    "case_id": case["id"],
                    "variant": variant,
                    "answer_routes": family["answer_routes"][variant],
                    "correction_explanation": family["correction_explanation"][variant],
                }
            )
    return expanded


def load_judgments(directory: Path = DIRECTORY) -> dict:
    raw = frozen_inputs(directory)
    data = json.loads(raw["judgments"])
    _, cases = load_inputs(directory)
    return {**data, "cases": validate_judgments(data, cases)}
