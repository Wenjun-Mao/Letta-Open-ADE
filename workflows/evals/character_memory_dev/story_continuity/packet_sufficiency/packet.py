"""Hash-bound, allowlisted review inputs; no selection or runtime imports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[4]
FREEZE_SHA256 = "5d1b78ad0a3c369ae88cf124656b96186a7d440ed84453b0525c41805fd7601d"


def checked_bytes(path: Path, expected: str) -> bytes:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"Frozen audit input differs: {path.name}")
    return raw


def load_inputs(directory: Path = DIRECTORY) -> tuple[dict, list[dict], str]:
    freeze = json.loads(checked_bytes(directory / "freeze.json", FREEZE_SHA256))
    if freeze["contract"] != "packet-sufficiency-input-v1":
        raise ValueError("Unknown audit contract")
    inputs = {
        name: checked_bytes(directory / spec["path"], spec["sha256"])
        for name, spec in freeze["inputs"].items()
    }
    for path, digest in freeze["runtime_sources"].items():
        checked_bytes(ROOT / path, digest)
    historical = json.loads(inputs["historical"])["cases"]
    controls = json.loads(inputs["controls"])["cases"]
    mapping = json.loads(inputs["mapping"])
    corpora = {"historical": historical, "controls": controls}
    expected = {(kind, case["id"]) for kind, cases in corpora.items() for case in cases}
    mapped = [(entry["fixture"], entry["id"]) for entry in mapping.values()]
    if len(historical) != 8 or len(controls) != 2:
        raise ValueError("Audit requires eight retained cases and two controls")
    if len(mapped) != len(set(mapped)) or set(mapped) != expected:
        raise ValueError("Neutral mapping must cover every case exactly once")
    if list(mapping) != [f"C{index:02d}" for index in range(1, 11)]:
        raise ValueError("Neutral case IDs differ")
    cases = []
    for neutral_id, entry in mapping.items():
        original = next(
            case for case in corpora[entry["fixture"]] if case["id"] == entry["id"]
        )
        rows = original["exchanges"]
        if len({row[0] for row in rows}) != len(rows):
            raise ValueError("Repeated source ID")
        if any(
            len(row) != 3 or not all(isinstance(s, str) and s for s in row)
            for row in rows
        ):
            raise ValueError("Expected nonempty complete exchange text")
        # Copy only transcript fields. Author labels and even case names stay out.
        cases.append(
            {
                "id": neutral_id,
                "query": original["query"],
                "exchanges": [
                    {
                        "id": f"E{index:02d}",
                        "at": f"2026-09-{index:02d}T12:00:00+00:00",
                        "user": user,
                        "assistant": assistant,
                    }
                    for index, (_, user, assistant) in enumerate(rows, 1)
                ],
            }
        )
    return json.loads(inputs["context"]), cases, inputs["rubric"].decode()


def render_packet(directory: Path = DIRECTORY) -> str:
    context, cases, rubric = load_inputs(directory)
    parts = [rubric.rstrip(), "## Complete Declared Context", "```json"]
    parts.extend([json.dumps(context, ensure_ascii=False, indent=2), "```"])
    for case in cases:
        parts.extend([f"## {case['id']}", f"Current question: {case['query']}"])
        for exchange in case["exchanges"]:
            parts.extend(
                [
                    f"### {case['id']}/{exchange['id']} | {exchange['at']}",
                    f"User: {exchange['user']}",
                    f"Assistant: {exchange['assistant']}",
                ]
            )
    return "\n\n".join(parts) + "\n"


if __name__ == "__main__":
    print(render_packet(), end="")
