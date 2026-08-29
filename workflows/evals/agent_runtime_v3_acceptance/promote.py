from __future__ import annotations

import argparse
import json
from pathlib import Path

from .policy import PROJECT_ROOT
from .promotion_review import PromotionReviewError, review_promotion


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review or explicitly apply an Agent Runtime v3 promotion proposal."
    )
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "config/model-router/deployment-manifest.json",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = review_promotion(
            proposal_path=args.proposal.resolve(),
            manifest_path=args.manifest.resolve(),
            project_root=PROJECT_ROOT,
            apply=bool(args.apply),
        )
    except PromotionReviewError as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "valid": True,
                "applied": result.applied,
                "proposal_sha256": result.proposal_sha256,
                "source_revision": result.source_revision,
                "deployment_ids": list(result.deployment_ids),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
