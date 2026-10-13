"""Frozen Mandarin cases and evaluator-only calibration material."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import Field

from .models import Case, Family, Identifier, Judgment, LENSES, Record, Text
from .records import digest, model_from_json, read_json

WORKFLOW_ROOT = Path(__file__).resolve().parent
FIXTURES = WORKFLOW_ROOT / "fixtures"
PROJECT_ROOT = WORKFLOW_ROOT.parents[2]


class Calibration(Record):
    example_id: Identifier
    case_id: Identifier
    reply: Text
    judgments: dict[str, Judgment]


class CaseFile(Record):
    family: Family
    cases: list[Case] = Field(min_length=1)


class Catalog(Record):
    schema_version: int
    suite_revision: Text
    case_files: list[Text] = Field(min_length=1)
    persona_file: Text
    calibration_file: Text


def _local_file(root: Path, name: str) -> Path:
    path = root / name
    if Path(name).name != name or path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular fixture in {root}: {name}")
    return path


def build_lock(root: Path = FIXTURES) -> dict:
    catalog = model_from_json(Catalog, read_json(root / "catalog.json"))
    names = [
        "catalog.json",
        *catalog.case_files,
        catalog.persona_file,
        catalog.calibration_file,
    ]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate fixture file")
    files = {
        name: hashlib.sha256(_local_file(root, name).read_bytes()).hexdigest()
        for name in sorted(names)
    }
    payload = {
        "schema_version": 1,
        "suite_revision": catalog.suite_revision,
        "files": files,
    }
    return {**payload, "sha256": digest(payload)}


def load_suite(root: Path = FIXTURES) -> dict:
    lock = read_json(root / "lock.json")
    if lock != build_lock(root):
        raise ValueError(
            "Frozen fixture bytes changed; review a new suite revision and lock"
        )
    catalog = model_from_json(Catalog, read_json(root / "catalog.json"))
    if catalog.schema_version != 1:
        raise ValueError("Unsupported case catalog version")
    cases: dict[str, Case] = {}
    for name in catalog.case_files:
        group = model_from_json(CaseFile, read_json(_local_file(root, name)))
        for case in group.cases:
            if case.family != group.family or case.case_id in cases:
                raise ValueError("Mismatched family or duplicate case ID")
            cases[case.case_id] = case
    if {case.family for case in cases.values()} != {"Q01", "Q02", "Q03", "Q04", "Q05"}:
        raise ValueError("The starter suite must cover all five promises")
    persona = read_json(_local_file(root, catalog.persona_file))
    if set(persona) != {"key", "source", "content", "content_sha256"}:
        raise ValueError("Malformed persona snapshot")
    if not isinstance(persona["content"], str) or not persona["content"].strip():
        raise ValueError("Empty persona snapshot")
    if (
        hashlib.sha256(persona["content"].encode()).hexdigest()
        != persona["content_sha256"]
    ):
        raise ValueError("Persona content/hash mismatch")
    raw_examples = read_json(_local_file(root, catalog.calibration_file))
    if (
        set(raw_examples) != {"status", "examples"}
        or raw_examples["status"] != "authored_not_observed"
    ):
        raise ValueError("Calibration must be explicitly authored, not model evidence")
    examples = {}
    for raw in raw_examples["examples"]:
        example = model_from_json(Calibration, raw)
        if example.case_id not in cases or example.example_id in examples:
            raise ValueError("Unknown calibration case or duplicate example ID")
        if set(example.judgments) != set(LENSES):
            raise ValueError("Calibration requires all three lenses")
        if any(
            not item.quote or item.quote not in example.reply
            for item in example.judgments.values()
        ):
            raise ValueError("Calibration quote must occur in its authored reply")
        examples[example.example_id] = example
    if {cases[item.case_id].family for item in examples.values()} != {
        case.family for case in cases.values()
    }:
        raise ValueError("Calibration examples must cover all five promises")
    return {
        "revision": catalog.suite_revision,
        "sha256": lock["sha256"],
        "cases": cases,
        "persona": persona,
        "calibration": examples,
    }


def actor_material(case: Case) -> dict:
    """Only scripted dialogue and scope; expected meanings never enter model input."""
    return {
        "language": case.language,
        "source_scope": case.source_scope.model_dump(),
        "target_scope": case.target_scope.model_dump(),
        "history_kind": case.history_kind,
        "history": [message.model_dump() for message in case.history],
        "prompt": case.prompt,
    }
