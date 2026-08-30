from __future__ import annotations

import hashlib
import json
import re
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
    source_revision: str | None,
    source_dirty: bool | None,
    policy_hashes: dict[str, str],
    qualification_config: dict[str, Any],
) -> PromotionProposal | None:
    if not _is_full_matrix_qualification_config(qualification_config):
        return None
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
    bindings = _deployment_bindings(rounds)
    if set(bindings) != {"conversation", "reviewer", "retriever"}:
        return None
    if not source_revision or not re.fullmatch(r"[0-9a-f]{40,64}", source_revision):
        return None
    if source_dirty is not False:
        return None
    if (
        int(qualification_config.get("rounds") or 0) != 3
        or float(qualification_config.get("timeout_seconds") or 0) != 180.0
        or int(qualification_config.get("retry_count", -1)) != 0
    ):
        return None
    if set(policy_hashes) != {"prompt", "tool", "schema", "retrieval"} or any(
        not re.fullmatch(r"[0-9a-f]{64}", digest) for digest in policy_hashes.values()
    ):
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
        "source_revision": source_revision,
        "source_dirty": source_dirty,
        "policy_hashes": dict(sorted(policy_hashes.items())),
        "qualification_config": qualification_config,
        "deployment_fingerprints": fingerprints[0],
        "deployment_bindings": bindings,
    }
    digest = hashlib.sha256(_canonical_bytes(material)).hexdigest()
    payload = {**material, "proposal_sha256": digest}
    root = output_dir / run_id
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"promotion-proposal-{digest}.json"
    path.write_bytes(_canonical_bytes(payload))
    return PromotionProposal(path=path, payload=payload)


def _is_full_matrix_qualification_config(config: dict[str, Any]) -> bool:
    required_keys = {
        "conversation_model_key",
        "reviewer_model_key",
        "embedding_model_key",
        "rounds",
        "timeout_seconds",
        "retry_count",
        "case_keys",
    }
    return set(config) == required_keys and config.get("case_keys") == []


def _deployment_bindings(rounds: tuple[object, ...]) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    inconsistent: set[str] = set()
    for round_result in rounds:
        for case in tuple(getattr(round_result, "cases", ())):
            resources = getattr(case, "resources", None)
            for snapshot in tuple(getattr(resources, "deployment_snapshots", ())):
                role = str(snapshot.get("role") or "")
                binding = {
                    "deployment_id": str(snapshot.get("deployment_id") or ""),
                    "route_alias": str(snapshot.get("route_alias") or ""),
                    "fingerprint_sha256": str(snapshot.get("fingerprint") or ""),
                }
                if not role or any(not value for value in binding.values()):
                    continue
                prior = bindings.setdefault(role, binding)
                if prior != binding:
                    inconsistent.add(role)
    return {
        role: binding
        for role, binding in sorted(bindings.items())
        if role not in inconsistent
    }


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
