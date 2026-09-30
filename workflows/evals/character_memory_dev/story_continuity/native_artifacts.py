"""Immutable private receipts and clean source binding for a single native probe."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from .annotation import check_annotation, freeze_annotation
from .schedule import ROOT, prepare

OUTPUTS = ROOT / "workflows/evals/character_memory_dev/outputs"


def write_once(path: Path, value: dict) -> None:
    # Exclusive creation prevents a restart from silently replacing prior evidence.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def clean_preparation() -> dict:
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise ValueError("Commit the reviewed iteration before native dispatch")
    return prepare()


def check_preparation(directory: Path) -> dict:
    expected = read(directory / "preparation.json")
    if clean_preparation() != expected:
        raise ValueError("Source/configuration changed after native freeze")
    return expected


def require_output_directory(directory: Path) -> Path:
    directory = directory.absolute()
    if directory.parent != OUTPUTS or directory.is_symlink():
        raise ValueError("Native evidence must use a direct, nonsymlink outputs child")
    if not directory.name.startswith("pc11-native-"):
        raise ValueError("Native output name must start with pc11-native-")
    if directory.resolve().parent != OUTPUTS.resolve():
        raise ValueError("Native output escapes the ignored workflow directory")
    return directory


def delivered_reply(record: dict) -> str:
    run_id = record["readback"]["run"]["id"]
    replies = [
        message["content"]
        for message in record["readback"]["state"]["messages"]
        if message["run_id"] == run_id and message["role"] == "assistant"
    ]
    return replies[0] if len(replies) == 1 else ""


def annotation_for(directory: Path, number: int, result: dict) -> dict | None:
    path = directory / f"annotation-{number:02d}.json"
    if not path.exists():
        return None
    record = read(path)
    if record["reviewer_kind"] != "human" or not record["reviewer"].strip():
        raise ValueError("A human annotation is required, not an agent-generated score")
    if record["usable"]:
        check_annotation(
            record,
            expected_sha256=record["sha256"],
            run_id=result["readback"]["run"]["id"],
            reply=delivered_reply(result),
        )
    elif not record.get("rationale", "").strip():
        raise ValueError("Unusable annotation requires a reason")
    return record


def annotate(directory: Path, number: int, supplied: dict) -> dict:
    if number not in {1, 3}:
        raise ValueError("Only origin and elaboration are annotation gates")
    result = read(directory / f"turn-{number:02d}.json")
    later = [directory / f"turn-{n:02d}.intent.json" for n in range(number + 1, 11)]
    if any(path.exists() for path in later):
        raise ValueError("Cannot annotate after a later dispatch intent")
    if (
        supplied.get("reviewer_kind") != "human"
        or not supplied.get("reviewer", "").strip()
    ):
        raise ValueError("Identify the human who supplied this annotation")
    if not isinstance(supplied.get("usable"), bool):
        raise ValueError("Human must explicitly classify whether details are usable")
    record = {
        "reviewer_kind": "human",
        "reviewer": supplied["reviewer"],
        "usable": supplied["usable"],
        "rationale": supplied["rationale"],
        "run_id": result["readback"]["run"]["id"],
    }
    if supplied["usable"]:
        record.update(
            freeze_annotation(
                run_id=record["run_id"],
                reply=delivered_reply(result),
                committed=result["validation"]["disposition"] == "committed",
                at_turn=number,
                observed_turns=[number],
                quotes=supplied["quotes"],
                rationale=supplied["rationale"],
                replacement_suggestion=supplied.get("replacement_suggestion"),
            )
        )
    elif not supplied["rationale"].strip():
        raise ValueError("Unusable origin/detail requires a human rationale")
    write_once(directory / f"annotation-{number:02d}.json", record)
    return record
