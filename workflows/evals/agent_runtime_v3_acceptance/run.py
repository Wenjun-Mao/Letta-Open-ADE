from __future__ import annotations

import argparse
import asyncio
import os
import re
import signal
import subprocess
import sys
from dataclasses import asdict, replace
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import agent_runtime_eval_contracts  # noqa: E402
from agent_runtime_eval_contracts import (  # noqa: E402
    FixtureError,
    load_cases,
    select_cases,
    study_cases_path,
)

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
from workflows.evals.agent_runtime_v3_acceptance.policy import (  # noqa: E402
    production_policy_hashes,
)
from workflows.evals.agent_runtime_v3_acceptance.runner import (  # noqa: E402
    QualificationRound,
    ResourceScope,
    run_llama_compatibility_round,
    run_primary_rounds,
)


class AcceptanceCancelled(RuntimeError):
    pass


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
    parser.add_argument("--case-key", dest="case_keys", action="append", default=[])
    parser.add_argument(
        "--include-llama-compatibility",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    return parser.parse_args(argv)


def _new_run_id(
    *, now: datetime | None = None, random_suffix: str | None = None
) -> str:
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    suffix = (random_suffix or uuid4().hex[:8]).lower()
    return f"agent-runtime-v3-{timestamp.strftime('%Y%m%dt%H%M%Sz')}-{suffix}"


async def run_acceptance(config: AcceptanceConfig) -> dict[str, Any]:
    if not config.database_url:
        raise RuntimeError(
            "live acceptance requires database_url for fail-closed cleanup"
        )
    canonical_cases = tuple(load_cases(study_cases_path()))
    canonical_case_keys = tuple(str(getattr(case, "key")) for case in canonical_cases)
    if not canonical_case_keys or len(canonical_case_keys) != len(
        set(canonical_case_keys)
    ):
        raise RuntimeError("shared canonical case matrix is empty or non-unique")
    diagnostic = bool(config.case_keys)
    try:
        cases = select_cases(canonical_cases, config.case_keys)
    except FixtureError as exc:
        raise RuntimeError(f"invalid diagnostic case selection: {exc}") from exc
    if diagnostic:
        selected_case_keys = tuple(str(getattr(case, "key")) for case in cases)
        expected_order = tuple(
            key for key in canonical_case_keys if key in set(config.case_keys)
        )
        if selected_case_keys != expected_order:
            raise RuntimeError(
                "diagnostic case selection must use canonical case order"
            )
    run_id = _new_run_id()
    source_revision = _source_revision()
    source_dirty = _source_dirty()
    source_fingerprint = _source_fingerprint()
    policy_hashes = production_policy_hashes()
    writer = RoundArtifactWriter(config.output_dir, run_id)
    client = RuntimeV3Client(config.api_base_url, config.api_key)
    resource_scopes: list[ResourceScope] = []
    try:
        health = await client.get_worker_health()
        preflight_passed = _worker_preflight_passed(
            health,
            source_revision=source_revision,
            source_dirty=source_dirty,
            source_fingerprint=source_fingerprint,
            diagnostic=diagnostic,
        )
        preflight = writer.write_preflight(
            {
                "schema_version": 1,
                "kind": "agent-runtime-v3-worker-preflight",
                "run_id": run_id,
                "passed": preflight_passed,
                "source_identity": {
                    "revision": source_revision,
                    "dirty": source_dirty,
                    "fingerprint": source_fingerprint,
                },
                "health": health,
            }
        )
        if not preflight_passed:
            return {
                "run_id": run_id,
                "preflight_path": str(preflight.path),
                "preflight_sha256": preflight.sha256,
                "provenance_path": None,
                "primary_rounds": [],
                "llama_compatibility": None,
                "promotion_proposal": None,
                "eligible": False,
                "passed": False,
            }
        primary = await run_primary_rounds(
            client=client,
            cases=cases,
            canonical_case_keys=canonical_case_keys,
            namespace=run_id,
            rounds=1 if diagnostic else config.rounds,
            conversation_model_key=config.conversation_model_key,
            reviewer_model_key=config.reviewer_model_key,
            embedding_model_key=config.embedding_model_key,
            timeout_seconds=config.timeout_seconds,
            retry_count=config.retry_count,
            resource_scope_sink=resource_scopes,
            on_round_complete=lambda result: _write_rounds(writer, (result,))[0],
            diagnostic=diagnostic,
        )
        materialized_primary = primary
        compatibility = None
        if config.include_llama_compatibility and not diagnostic:
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
                tuple(str(getattr(case, "key")) for case in cases),
                materialized_primary,
                compatibility
                if isinstance(compatibility, QualificationRound)
                else None,
                source_revision=source_revision,
                source_dirty=source_dirty,
                source_fingerprint=source_fingerprint,
                policy_hashes=policy_hashes,
                preflight_sha256=preflight.sha256,
            )
        )
        proposal = (
            None
            if diagnostic
            else build_promotion_proposal(
                output_dir=config.output_dir,
                run_id=run_id,
                rounds=materialized_primary,
                canonical_case_keys=canonical_case_keys,
                required_rounds=3,
                provenance_sha256=provenance_sha256,
                preflight_sha256=preflight.sha256,
                source_revision=source_revision,
                source_dirty=source_dirty,
                source_fingerprint=source_fingerprint,
                policy_hashes=policy_hashes,
                qualification_config=_qualification_config(config),
            )
        )
        return {
            "run_id": run_id,
            "preflight_path": str(preflight.path),
            "preflight_sha256": preflight.sha256,
            "provenance_path": str(provenance_path),
            "primary_rounds": [_round_summary(item) for item in materialized_primary],
            "llama_compatibility": _round_summary(compatibility)
            if isinstance(compatibility, QualificationRound)
            else compatibility,
            "promotion_proposal": str(proposal.path) if proposal else None,
            "eligible": proposal is not None,
            "passed": bool(materialized_primary)
            and all(item.passed for item in materialized_primary),
        }
    finally:
        await _close_client_and_cleanup(client, config, run_id, resource_scopes)


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
        case_keys=tuple(args.case_keys) if args.case_keys else None,
    )
    try:
        result = asyncio.run(_run_interruptible(config))
    except AcceptanceCancelled:
        print("Acceptance run cancelled after scoped cleanup.", file=sys.stderr)
        return 130
    except KeyboardInterrupt:
        print("Acceptance run cancelled before startup completed.", file=sys.stderr)
        return 130
    print(result)
    if config.case_keys:
        return 0 if result["passed"] else 1
    return 0 if result["eligible"] else 1


async def _run_interruptible(config: AcceptanceConfig) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    if task is None:
        raise RuntimeError("acceptance runner has no active asyncio task")
    cancellation_requested = False
    previous_handlers: dict[signal.Signals, Any] = {}

    def request_cancellation(_signum: int, _frame: object) -> None:
        nonlocal cancellation_requested
        if cancellation_requested:
            return
        cancellation_requested = True
        loop.call_soon_threadsafe(task.cancel)

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.signal(signum, request_cancellation)
    try:
        return await run_acceptance(config)
    except asyncio.CancelledError as exc:
        if cancellation_requested:
            raise AcceptanceCancelled from exc
        raise
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


async def _close_client_and_cleanup(
    client: RuntimeV3Client,
    config: AcceptanceConfig,
    run_id: str,
    resource_scopes: list[ResourceScope],
) -> None:
    try:
        await client.aclose()
    finally:
        if not resource_scopes:
            return
        if not config.database_url:
            raise RuntimeError(
                "live acceptance created resources but database cleanup is not configured"
            )
        cleaner = ScopedPostgresCleanup(
            database_url=config.database_url,
            output_dir=config.output_dir,
        )
        cleaner.cleanup(
            CleanupScope(
                run_id=run_id,
                definition_keys=tuple(
                    key for scope in resource_scopes for key in scope.definition_keys
                ),
                subject_external_keys=tuple(
                    key
                    for scope in resource_scopes
                    for key in scope.subject_external_keys
                ),
            )
        )


def _write_rounds(
    writer: RoundArtifactWriter, rounds: tuple[QualificationRound, ...]
) -> tuple[QualificationRound, ...]:
    results: list[QualificationRound] = []
    for round_result in rounds:
        events = [
            {
                "event_id": str(getattr(event, "event_id", "")),
                "run_id": str(getattr(event, "run_id", "")),
                "sequence": int(getattr(event, "sequence", 0)),
                "event_type": str(getattr(event, "event_type", "")),
                "attempt": getattr(event, "attempt", None),
                "correlation_id": str(getattr(event, "correlation_id", "")),
                "causation_id": getattr(event, "causation_id", None),
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
                "turns": [asdict(item) for item in case.turns],
                "tools": [asdict(item) for item in case.tools],
                "facts": [asdict(item) for item in case.facts],
                "setup_run_ids": list(case.setup_run_ids),
                "resources": {
                    "definition_keys": list(case.resources.definition_keys),
                    "subject_external_keys": list(case.resources.subject_external_keys),
                },
            }
            for case in round_result.cases
        ],
    }


def _provenance(
    config: AcceptanceConfig,
    run_id: str,
    canonical_case_keys: tuple[str, ...],
    executed_case_keys: tuple[str, ...],
    primary_rounds: tuple[QualificationRound, ...],
    compatibility_round: QualificationRound | None,
    *,
    source_revision: str | None,
    source_dirty: bool | None,
    source_fingerprint: str | None,
    policy_hashes: dict[str, str],
    preflight_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "agent-runtime-v3-acceptance-provenance",
        "captured_at": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "source_revision": source_revision,
        "source_dirty": source_dirty,
        "source_fingerprint": source_fingerprint,
        "policy_hashes": dict(sorted(policy_hashes.items())),
        "preflight_sha256": preflight_sha256,
        "effective_config": public_config(config),
        "canonical_case_keys": list(canonical_case_keys),
        "canonical_case_keys_sha256": _sha256_text("\n".join(canonical_case_keys)),
        "executed_case_keys": list(executed_case_keys),
        "agent_runtime_eval_contracts_version": _contracts_version(),
        "primary_rounds": [_round_summary(item) for item in primary_rounds],
        "llama_compatibility": (
            _round_summary(compatibility_round)
            if compatibility_round is not None
            else None
        ),
    }


def _qualification_config(config: AcceptanceConfig) -> dict[str, Any]:
    return {
        "conversation_model_key": config.conversation_model_key,
        "reviewer_model_key": config.reviewer_model_key,
        "embedding_model_key": config.embedding_model_key,
        "rounds": config.rounds,
        "timeout_seconds": config.timeout_seconds,
        "retry_count": config.retry_count,
        "case_keys": list(config.case_keys),
    }


def _worker_preflight_passed(
    health: dict[str, Any],
    *,
    source_revision: str | None,
    source_dirty: bool | None,
    source_fingerprint: str | None,
    diagnostic: bool,
) -> bool:
    return (
        source_revision is not None
        and re.fullmatch(r"[0-9a-f]{40,64}", source_revision) is not None
        and source_dirty is not None
        and (diagnostic or source_dirty is False)
        and source_fingerprint is not None
        and re.fullmatch(r"[0-9a-f]{64}", source_fingerprint) is not None
        and health.get("http_status") == 200
        and health.get("status") == "ready"
        and health.get("database_ready") is True
        and health.get("worker_ready") is True
        and isinstance(health.get("matching_build_worker_count"), int)
        and not isinstance(health.get("matching_build_worker_count"), bool)
        and health["matching_build_worker_count"] >= 1
        and health.get("source_revision") == source_revision
        and health.get("source_dirty") is source_dirty
        and health.get("source_fingerprint") == source_fingerprint
    )


def _source_revision() -> str | None:
    configured = str(os.getenv("ADE_SOURCE_REVISION") or "").strip().casefold()
    if configured:
        return configured
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _source_dirty() -> bool | None:
    configured = str(os.getenv("ADE_SOURCE_DIRTY") or "").strip().casefold()
    if configured in {"0", "false", "no"}:
        return False
    if configured in {"1", "true", "yes"}:
        return True
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return bool(output.strip())


def _source_fingerprint() -> str | None:
    configured = str(os.getenv("ADE_SOURCE_FINGERPRINT") or "").strip().casefold()
    if configured:
        return configured
    script = PROJECT_ROOT / "scripts" / "source_fingerprint.py"
    if not script.is_file():
        return None
    try:
        return subprocess.check_output(
            [sys.executable, os.fspath(script), "--root", os.fspath(PROJECT_ROOT)],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _contracts_version() -> str | None:
    try:
        return version("agent-runtime-eval-contracts")
    except PackageNotFoundError:
        return getattr(agent_runtime_eval_contracts, "__version__", None)


if __name__ == "__main__":
    raise SystemExit(main())
