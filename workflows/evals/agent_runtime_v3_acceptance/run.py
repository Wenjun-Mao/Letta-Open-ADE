from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import agent_runtime_eval_contracts  # noqa: E402
from agent_runtime_eval_contracts import load_cases  # noqa: E402

from workflows.evals.agent_runtime_v3_acceptance.artifacts import RoundArtifactWriter  # noqa: E402
from workflows.evals.agent_runtime_v3_acceptance.cleanup import (  # noqa: E402
    CleanupScope,
    ScopedPostgresCleanup,
)
from workflows.evals.agent_runtime_v3_acceptance.client import RuntimeV3Client  # noqa: E402
from workflows.evals.agent_runtime_v3_acceptance.config import (  # noqa: E402
    AcceptanceConfig,
    load_config,
    public_config,
    with_overrides,
)
from workflows.evals.agent_runtime_v3_acceptance.proposal import (  # noqa: E402
    build_promotion_proposal,
)
from workflows.evals.agent_runtime_v3_acceptance.runner import (  # noqa: E402
    QualificationRound,
    ResourceScope,
    run_llama_compatibility_round,
    run_primary_rounds,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ADE v3 black-box acceptance matrix."
    )
    parser.add_argument("--config", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--conversation-model-key", default="")
    parser.add_argument("--reviewer-model-key", default="")
    parser.add_argument("--embedding-model-key", default="")
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--retry-count", type=int)
    parser.add_argument(
        "--include-llama-compatibility",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    return parser.parse_args(argv)


async def run_acceptance(config: AcceptanceConfig) -> dict[str, Any]:
    if not config.database_url:
        raise RuntimeError(
            "live acceptance requires database_url for fail-closed cleanup"
        )
    cases = tuple(load_cases())
    canonical_case_keys = tuple(str(getattr(case, "key")) for case in cases)
    if not canonical_case_keys or len(canonical_case_keys) != len(
        set(canonical_case_keys)
    ):
        raise RuntimeError("shared canonical case matrix is empty or non-unique")
    run_id = f"agent-runtime-v3-{datetime.now(UTC).strftime('%Y%m%dt%H%M%sz')}"
    writer = RoundArtifactWriter(config.output_dir, run_id)
    client = RuntimeV3Client(config.api_base_url, config.api_key)
    resource_scopes: list[ResourceScope] = []
    try:
        primary = await run_primary_rounds(
            client=client,
            cases=cases,
            canonical_case_keys=canonical_case_keys,
            namespace=run_id,
            rounds=config.rounds,
            conversation_model_key=config.conversation_model_key,
            reviewer_model_key=config.reviewer_model_key,
            embedding_model_key=config.embedding_model_key,
            timeout_seconds=config.timeout_seconds,
            retry_count=config.retry_count,
            resource_scope_sink=resource_scopes,
            on_round_complete=lambda result: _write_rounds(writer, (result,))[0],
        )
        materialized_primary = primary
        compatibility = None
        if config.include_llama_compatibility:
            try:
                compatibility = await run_llama_compatibility_round(
                    client=client,
                    cases=cases,
                    namespace=run_id,
                    conversation_model_key=config.llama_compatibility_model_key,
                    reviewer_model_key=config.reviewer_model_key,
                    embedding_model_key=config.embedding_model_key,
                    timeout_seconds=config.timeout_seconds,
                    retry_count=config.retry_count,
                    resource_scope_sink=resource_scopes,
                    on_round_complete=lambda result: _write_rounds(writer, (result,))[
                        0
                    ],
                )
            except Exception as exc:
                compatibility = {
                    "kind": "llama-compatibility",
                    "nonblocking_error": type(exc).__name__,
                }
        provenance_path, provenance_sha256 = writer.write_provenance(
            _provenance(
                config,
                run_id,
                canonical_case_keys,
                materialized_primary,
                compatibility
                if isinstance(compatibility, QualificationRound)
                else None,
            )
        )
        proposal = build_promotion_proposal(
            output_dir=config.output_dir,
            run_id=run_id,
            rounds=materialized_primary,
            canonical_case_keys=canonical_case_keys,
            required_rounds=3,
            provenance_sha256=provenance_sha256,
        )
        return {
            "run_id": run_id,
            "provenance_path": str(provenance_path),
            "primary_rounds": [_round_summary(item) for item in materialized_primary],
            "llama_compatibility": _round_summary(compatibility)
            if isinstance(compatibility, QualificationRound)
            else compatibility,
            "promotion_proposal": str(proposal.path) if proposal else None,
            "eligible": proposal is not None,
        }
    finally:
        await client.aclose()
        if resource_scopes:
            if not config.database_url:
                raise RuntimeError(
                    "live acceptance created resources but database cleanup is not configured"
                )
            cleaner = ScopedPostgresCleanup(
                database_url=config.database_url,
                output_dir=config.output_dir,
                cleanup_owner=config.cleanup_owner,
            )
            cleaner.cleanup(
                CleanupScope(
                    run_id=run_id,
                    definition_keys=tuple(
                        key
                        for scope in resource_scopes
                        for key in scope.definition_keys
                    ),
                    subject_external_keys=tuple(
                        key
                        for scope in resource_scopes
                        for key in scope.subject_external_keys
                    ),
                )
            )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(Path(args.config) if args.config else None)
    config = with_overrides(
        config,
        output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
        conversation_model_key=args.conversation_model_key or None,
        reviewer_model_key=args.reviewer_model_key or None,
        embedding_model_key=args.embedding_model_key or None,
        rounds=args.rounds,
        timeout_seconds=args.timeout_seconds,
        retry_count=args.retry_count,
        include_llama_compatibility=args.include_llama_compatibility,
    )
    result = asyncio.run(run_acceptance(config))
    print(result)
    return 0 if result["eligible"] else 1


def _write_rounds(
    writer: RoundArtifactWriter, rounds: tuple[QualificationRound, ...]
) -> tuple[QualificationRound, ...]:
    results: list[QualificationRound] = []
    for round_result in rounds:
        events = [
            {
                "run_id": str(getattr(event, "run_id", "")),
                "sequence": int(getattr(event, "sequence", 0)),
                "event_type": str(getattr(event, "event_type", "")),
                "attempt": getattr(event, "attempt", None),
                "payload": getattr(event, "payload", {}),
            }
            for case in round_result.cases
            for event in case.events
        ]
        artifact = writer.write_round(
            round_result.index, _round_summary(round_result), events
        )
        results.append(replace(round_result, artifact_sha256=artifact.sha256))
    return tuple(results)


def _round_summary(round_result: QualificationRound) -> dict[str, Any]:
    return {
        "index": round_result.index,
        "kind": round_result.kind,
        "execution_mode": round_result.execution_mode,
        "complete_matrix": round_result.complete_matrix,
        "passed": round_result.passed,
        "case_keys": list(round_result.case_keys),
        "deployment_fingerprints": round_result.deployment_fingerprints,
        "deployment_snapshots": [
            snapshot
            for case in round_result.cases
            for snapshot in case.resources.deployment_snapshots
        ],
        "artifact_sha256": round_result.artifact_sha256,
        "cases": [
            {
                "case_key": case.case_key,
                "score": case.score,
                "infrastructure": case.infrastructure,
            }
            for case in round_result.cases
        ],
    }


def _provenance(
    config: AcceptanceConfig,
    run_id: str,
    canonical_case_keys: tuple[str, ...],
    primary_rounds: tuple[QualificationRound, ...],
    compatibility_round: QualificationRound | None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "agent-runtime-v3-acceptance-provenance",
        "captured_at": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "git_revision": _git_revision(),
        "effective_config": public_config(config),
        "canonical_case_keys": list(canonical_case_keys),
        "canonical_case_keys_sha256": _sha256_text("\n".join(canonical_case_keys)),
        "agent_runtime_eval_contracts_version": getattr(
            agent_runtime_eval_contracts, "__version__", None
        ),
        "primary_rounds": [_round_summary(item) for item in primary_rounds],
        "llama_compatibility": (
            _round_summary(compatibility_round)
            if compatibility_round is not None
            else None
        ),
    }


def _git_revision() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
