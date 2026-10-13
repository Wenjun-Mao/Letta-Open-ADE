"""Evidence-bound human reviews with an append-only correction history."""

from pathlib import Path

from .models import LENSES, Review
from .records import load_sealed, seal, write_new
from .runs import load_capture


def _validate_review(path: Path, review: Review) -> None:
    run, _, _, capture, capture_hash, issues = load_capture(path)
    if review.capture_sha256 != capture_hash:
        raise ValueError("Review belongs to a different capture")
    if review.kind == "scripted_example" and run.mode != "offline_scripted":
        raise ValueError("Scripted judgments cannot qualify live evidence")
    reply = capture.observation.reply
    for judgment in review.judgments.values():
        if issues and judgment.result != "cannot_assess":
            raise ValueError(
                "Resolve evidence limitations before semantic qualification"
            )
        if reply and (not judgment.quote.strip() or judgment.quote not in reply):
            raise ValueError(
                "Each lens requires an exact quote from the captured reply"
            )
        if not reply and (judgment.quote or judgment.result != "cannot_assess"):
            raise ValueError(
                "A missing reply requires an empty quote and cannot_assess"
            )


def load_reviews(path: Path) -> list[tuple[Review, str]]:
    history: list[tuple[Review, str]] = []
    for index, file in enumerate(sorted(path.glob("review-*.json")), start=1):
        review, review_hash = load_sealed(file, "assessment-review", Review)
        if file.name != f"review-{index:04d}.json" or review.revision != index:
            raise ValueError("Non-contiguous review history")
        if review.supersedes_sha256 != (history[-1][1] if history else None):
            raise ValueError("Review does not supersede the preceding judgment")
        _validate_review(path, review)
        history.append((review, review_hash))
    return history


def review_template(path: Path) -> dict:
    _, _, _, _, capture_hash, _ = load_capture(path)
    history = load_reviews(path)
    return {
        "schema_version": 1,
        "capture_sha256": capture_hash,
        "revision": len(history) + 1,
        "supersedes_sha256": history[-1][1] if history else None,
        "change_reason": None,
        "reviewer": "",
        "kind": "human",
        "judgments": {
            lens: {"result": None, "quote": "", "rationale": ""} for lens in LENSES
        },
    }


def record_review(path: Path, review: Review) -> None:
    history = load_reviews(path)
    if review.revision != len(history) + 1:
        raise ValueError("Review revision is not the next append-only slot")
    if review.supersedes_sha256 != (history[-1][1] if history else None):
        raise ValueError("Review correction requires the preceding review hash")
    _validate_review(path, review)
    write_new(
        path / f"review-{review.revision:04d}.json", seal("assessment-review", review)
    )
