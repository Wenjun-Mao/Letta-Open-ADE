from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .qualification import is_eligible_primary_matrix


@dataclass(frozen=True)
class PromotionProposal:
    path: Path
    payload: dict[str, Any]


def build_promotion_proposal(
    *,
    output_dir: Path,
    run_id: str,
    rounds: tuple[object, ...],
    canonical_case_keys: tuple[str, ...],
    required_rounds: int,
    provenance_sha256: str,
) -> PromotionProposal | None:
    if not is_eligible_primary_matrix(
        rounds,
        canonical_case_keys=canonical_case_keys,
        required_rounds=required_rounds,
    ):
        return None
    fingerprints = [
        dict(getattr(round_result, "deployment_fingerprints", {}))
        for round_result in rounds
    ]
    if len({json.dumps(value, sort_keys=True) for value in fingerprints}) != 1:
        return None
    material = {
        "schema_version": 1,
        "kind": "agent-runtime-v3-promotion-proposal",
        "run_id": run_id,
        "apply_owner": "coordinator",
        "apply_status": "proposal-only",
        "manifest_mutation": "forbidden-in-executor-slice",
        "canonical_case_keys": list(canonical_case_keys),
        "required_primary_rounds": required_rounds,
        "round_artifact_sha256s": [
            str(getattr(item, "artifact_sha256")) for item in rounds
        ],
        "provenance_sha256": provenance_sha256,
        "deployment_fingerprints": fingerprints[0],
    }
    digest = hashlib.sha256(_canonical_bytes(material)).hexdigest()
    payload = {**material, "proposal_sha256": digest}
    root = output_dir / run_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"promotion-proposal-{digest}.json"
    path.write_bytes(_canonical_bytes(payload))
    return PromotionProposal(path=path, payload=payload)


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
