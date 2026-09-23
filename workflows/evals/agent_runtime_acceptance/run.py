from __future__ import annotations

import argparse
import asyncio
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import agent_runtime_eval_contracts  # noqa: E402
from ade_api.features.agent_runtime.request_budget import budget_ledger  # noqa: E402
from ade_api.platform.settings import get_settings  # noqa: E402
from agent_runtime_eval_contracts import (  # noqa: E402
    FixtureError,
    load_cases,
    select_cases,
    study_cases_path,
)

from workflows.evals.agent_runtime_acceptance.artifacts import RoundArtifactWriter  # noqa: E402
from workflows.evals.agent_runtime_acceptance.round_artifacts import (  # noqa: E402
    _round_summary,
    _write_rounds,
)
from workflows.evals.agent_runtime_acceptance.client import RuntimeClient  # noqa: E402
from workflows.evals.agent_runtime_acceptance.config import (  # noqa: E402
    AcceptanceConfig,
    QUALIFIED_AGENT_TOOL_NAMES,
    load_config,
    public_config,
    with_overrides,
)
from workflows.evals.agent_runtime_acceptance.proposal import (  # noqa: E402
    build_promotion_proposal,
)
from workflows.evals.agent_runtime_acceptance.policy import (  # noqa: E402
    production_policy_hashes,
)
from workflows.evals.agent_runtime_acceptance.preflight import (  # noqa: E402
    budget_preflight_passed,
    worker_preflight_passed,
)
from workflows.evals.agent_runtime_acceptance.runner import (  # noqa: E402
    QualificationRound,
    EvaluationSessionScope,
    run_llama_compatibility_round,
    run_primary_rounds,
)


class AcceptanceCancelled(RuntimeError):
    pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ADE Agent Runtime black-box acceptance matrix."
    )
    parser.add_argument("--config", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--conversation-model-key", default="")
    parser.add_argument("--reviewer-model-key", default="")
    parser.add_argument("--embedding-model-key", default="")
    parser.add_argument("--prompt-key", default="")
    parser.add_argument("--persona-key", default="")
    parser.add_argument("--rounds", type=int)
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--retry-count", type=int)
    parser.add_argument("--case-key", dest="case_keys", action="append", default=[])
    parser.add_argument("--diagnostic-fixture", default="")
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
    return f"agent-runtime-{timestamp.strftime('%Y%m%dt%H%M%Sz')}-{suffix}"


async def run_acceptance(
    config: AcceptanceConfig, diagnostic_fixture: Path | None = None
) -> dict[str, Any]:
    canonical_cases = tuple(load_cases(study_cases_path()))
    canonical_case_keys = tuple(str(getattr(case, "key")) for case in canonical_cases)
    if not canonical_case_keys or len(canonical_case_keys) != len(
        set(canonical_case_keys)
    ):
        raise RuntimeError("shared canonical case matrix is empty or non-unique")
    diagnostic = bool(config.case_keys or diagnostic_fixture)
    try:
        fixture_cases = (
            load_cases(diagnostic_fixture) if diagnostic_fixture else canonical_cases
        )
        cases = select_cases(fixture_cases, config.case_keys)
    except FixtureError as exc:
        raise RuntimeError(f"invalid diagnostic case selection: {exc}") from exc
    if diagnostic:
        selected_case_keys = tuple(str(getattr(case, "key")) for case in cases)
        expected_order = tuple(
            str(getattr(case, "key"))
            for case in fixture_cases
            if not config.case_keys
            or str(getattr(case, "key")) in set(config.case_keys)
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
    client = RuntimeClient(config.api_base_url, config.api_key)
    session_scopes: list[EvaluationSessionScope] = []
    try:
        health = await client.get_worker_health()
        budget_verified = budget_preflight_passed(
            health, diagnostic=diagnostic, retry_count=config.retry_count
        )
        preflight_passed = (
            worker_preflight_passed(
                health,
                source_revision=source_revision,
                source_dirty=source_dirty,
                source_fingerprint=source_fingerprint,
                diagnostic=diagnostic,
            )
            and budget_verified
        )
        preflight = writer.write_preflight(
            {
                "schema_version": 1,
                "kind": "agent-runtime-worker-preflight",
                "run_id": run_id,
                "passed": preflight_passed,
                "source_identity": {
                    "revision": source_revision,
                    "dirty": source_dirty,
                    "fingerprint": source_fingerprint,
                },
                "health": health,
                "budget_verified": budget_verified,
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
        ledger = budget_ledger(get_settings())
        budget_exhausted = ledger.exhausted if ledger is not None else None
        primary = await run_primary_rounds(
            client=client,
            cases=cases,
            canonical_case_keys=canonical_case_keys,
            namespace=run_id,
            rounds=1 if diagnostic else config.rounds,
            conversation_model_key=config.conversation_model_key,
            reviewer_model_key=config.reviewer_model_key,
            embedding_model_key=config.embedding_model_key,
            prompt_key=config.prompt_key,
            persona_key=config.persona_key,
            timeout_seconds=config.timeout_seconds,
            retry_count=config.retry_count,
            session_scope_sink=session_scopes,
            on_round_complete=lambda result: _write_rounds(writer, (result,))[0],
            diagnostic=diagnostic,
            budget_exhausted=budget_exhausted,
        )
        materialized_primary = primary
        compatibility = None
        if (
            config.include_llama_compatibility
            and not diagnostic
            and (budget_exhausted is None or not budget_exhausted())
        ):
            try:
                compatibility = await run_llama_compatibility_round(
                    client=client,
                    cases=cases,
                    namespace=run_id,
                    conversation_model_key=config.llama_compatibility_model_key,
                    reviewer_model_key=config.reviewer_model_key,
                    embedding_model_key=config.embedding_model_key,
                    prompt_key=config.prompt_key,
                    persona_key=config.persona_key,
                    timeout_seconds=config.timeout_seconds,
                    retry_count=config.retry_count,
                    session_scope_sink=session_scopes,
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
                agent_bundle=_agent_bundle(config),
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
        await _close_client_and_purge(client, session_scopes)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(Path(args.config) if args.config else None)
    config = with_overrides(
        config,
        output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
        conversation_model_key=args.conversation_model_key or None,
        reviewer_model_key=args.reviewer_model_key or None,
        embedding_model_key=args.embedding_model_key or None,
        prompt_key=args.prompt_key or None,
        persona_key=args.persona_key or None,
        rounds=args.rounds,
        timeout_seconds=args.timeout_seconds,
        retry_count=args.retry_count,
        include_llama_compatibility=args.include_llama_compatibility,
        case_keys=tuple(args.case_keys) if args.case_keys else None,
    )
    try:
        result = asyncio.run(
            _run_interruptible(
                config,
                Path(args.diagnostic_fixture).resolve()
                if args.diagnostic_fixture
                else None,
            )
        )
    except AcceptanceCancelled:
        print(
            "Acceptance run cancelled after evaluation-session cleanup.",
            file=sys.stderr,
        )
        return 130
    except KeyboardInterrupt:
        print("Acceptance run cancelled before startup completed.", file=sys.stderr)
        return 130
    print(result)
    if config.case_keys or args.diagnostic_fixture:
        return 0 if result["passed"] else 1
    return 0 if result["eligible"] else 1


async def _run_interruptible(
    config: AcceptanceConfig, diagnostic_fixture: Path | None = None
) -> dict[str, Any]:
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
        if diagnostic_fixture is None:
            return await run_acceptance(config)
        return await run_acceptance(config, diagnostic_fixture)
    except asyncio.CancelledError as exc:
        if cancellation_requested:
            raise AcceptanceCancelled from exc
        raise
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


async def _close_client_and_purge(
    client: RuntimeClient,
    session_scopes: list[EvaluationSessionScope],
) -> None:
    try:
        session_ids = tuple(
            dict.fromkeys(
                conversation_id
                for scope in session_scopes
                for conversation_id in scope.conversation_ids
            )
        )
        for conversation_id in reversed(session_ids):
            await client.purge_evaluation_session(conversation_id)
    finally:
        await client.aclose()


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
        "kind": "agent-runtime-acceptance-provenance",
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
        "prompt_key": config.prompt_key,
        "persona_key": config.persona_key,
        "rounds": config.rounds,
        "timeout_seconds": config.timeout_seconds,
        "retry_count": config.retry_count,
        "case_keys": list(config.case_keys),
    }


def _agent_bundle(config: AcceptanceConfig) -> dict[str, object]:
    return {
        "prompt_key": config.prompt_key,
        "persona_key": config.persona_key,
        "tool_names": list(QUALIFIED_AGENT_TOOL_NAMES),
    }


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
