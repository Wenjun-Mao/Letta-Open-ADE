"""Fixed offline diagnostic scope and freeze verification; standard-library only."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from ..correction_dependencies.inputs import (
    DIRECTORY as CORRECTION_DIRECTORY,
    FREEZE_SHA256,
    ROOT,
    checked_bytes,
    load_inputs,
)


DIRECTORY = Path(__file__).resolve().parent
PROTOCOL_COMMIT = "62d461d4e2b6939fc8dff2fff9309c1f542f9189"
PROTOCOL_SHA256 = "4de8c8ad2e7ff4142bbb3b9550965d9338782a0bb8a28ee9920dcda2cec59521"
HISTORICAL_SHA256 = {
    "comparison.json": "63a71bdbc6de1e1cfd69f2f5eaee48e6da562ba49216a66f031048fbca876634",
    "packets.jsonl": "5eadb2b5cf8ad52c4f46691d92b0bae8365b29f7cb7859bf01f0e8ab63e1aa27",
}
ROWS = (
    ("D04/empty", "D04", ()),
    ("D04/literal-four", "D04", ("E07", "E02", "E05", "E04")),
    ("D04/whole-pool", "D04", tuple(f"E{i:02d}" for i in range(1, 9))),
    ("D02/empty", "D02", ()),
    ("D02/original", "D02", ("E01",)),
    ("D02/competing", "D02", ("E01", "E02")),
    ("D02/restored", "D02", ("E01", "E07")),
    ("D02/neighborhood", "D02", ("E02", "E01", "E03", "E04")),
)


def verify_freeze(directory: Path = DIRECTORY) -> dict:
    protocol_path = DIRECTORY / "OFFLINE_PROTOCOL.md"
    raw = checked_bytes(directory / protocol_path.name, PROTOCOL_SHA256)
    committed = subprocess.run(
        ["git", "show", f"{PROTOCOL_COMMIT}:{protocol_path.relative_to(ROOT)}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    if committed != raw:
        raise ValueError("Offline protocol differs from its pre-measurement commit")
    historical = {
        name: checked_bytes(CORRECTION_DIRECTORY / name, expected)
        for name, expected in HISTORICAL_SHA256.items()
    }
    summary = json.loads(historical["comparison.json"])
    for relative, expected in summary["execution_sources"].items():
        checked_bytes(ROOT / relative, expected)
    return {
        "protocol_commit": PROTOCOL_COMMIT,
        "protocol_sha256": hashlib.sha256(raw).hexdigest(),
        "correction_input_manifest_sha256": FREEZE_SHA256,
        "historical_artifacts_sha256": HISTORICAL_SHA256,
    }


def validate_inputs(context: dict, cases: list[dict]) -> None:
    """Reject semantic, identity, topology or count drift before constructing H."""
    expected_context, expected_cases = load_inputs()
    expected_cases = [case for case in expected_cases if case["id"] in {"D02", "D04"}]
    if context != expected_context or cases != expected_cases:
        raise ValueError("Offline diagnostic inputs/scope/count differ from the freeze")


def load_offline_inputs() -> tuple[dict, list[dict], dict]:
    freeze = verify_freeze()
    context, cases = load_inputs()
    cases = [case for case in cases if case["id"] in {"D02", "D04"}]
    validate_inputs(context, cases)
    return context, cases, freeze


def validate_row(key: str, case_id: str, included: list[str]) -> None:
    if (key, case_id, tuple(included)) not in ROWS:
        raise ValueError("Packet row differs from the eight-row offline protocol")
