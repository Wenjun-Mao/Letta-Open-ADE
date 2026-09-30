"""Narrow, explicit evaluator-only continuation; never a runtime baseline rebind."""

PREFIX = "workflows/evals/character_memory_dev/story_continuity/"
ANNOTATION_FILES = {
    PREFIX + name
    for name in (
        "annotation_amendment.py",
        "native_artifacts.py",
        "native.py",
        "native_sequence.py",
    )
}
CONTRACT = "pc11-agent-annotation-amendment-v1"


def validate_continuation(original: dict, current: dict) -> None:
    mutable = {"source_revision", "source_files", "source_fingerprint"}
    if {k: v for k, v in original.items() if k not in mutable} != {
        k: v for k, v in current.items() if k not in mutable
    }:
        raise ValueError(
            "Annotation amendment cannot change runtime/configuration/schedule"
        )
    before, after = original["source_files"], current["source_files"]
    changed = {
        path for path in set(before) | set(after) if before.get(path) != after.get(path)
    }
    if not changed or not changed <= ANNOTATION_FILES or set(before) - set(after):
        raise ValueError("Annotation amendment changes non-annotation source")
    if original["source_revision"] == current["source_revision"]:
        raise ValueError("Annotation amendment requires a new clean committed runner")


def validate_record(
    record: dict, original: dict, current: dict, original_hash: str
) -> None:
    if (
        record.get("contract") != CONTRACT
        or record.get("reviewer_kind") != "agent"
        or record.get("effective_before_turn") != 2
        or record.get("original_preparation_sha256") != original_hash
        or record.get("continued_preparation") != current
        or not record.get("user_approval")
    ):
        raise ValueError("Invalid or stale annotation-only continuation receipt")
    validate_continuation(original, current)
