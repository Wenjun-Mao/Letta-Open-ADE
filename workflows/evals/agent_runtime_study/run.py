from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

WORKFLOW_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WORKFLOW_ROOT.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflows.evals.agent_runtime_study.artifacts import (  # noqa: E402
    StudyArtifactWriter,
)
from workflows.evals.agent_runtime_study.config import (  # noqa: E402
    load_config,
    public_config,
    with_overrides,
)
from workflows.evals.agent_runtime_study.decision import (  # noqa: E402
    build_candidate_decision_evidence,
)
from workflows.evals.agent_runtime_study.letta_baseline import (  # noqa: E402
    LettaBaselineProbe,
)
from workflows.evals.agent_runtime_study.provenance import (  # noqa: E402
    capture_provenance,
    capture_router_catalog,
)
from workflows.evals.agent_runtime_study.retrieval_benchmark import (  # noqa: E402
    run_retrieval_benchmark,
)
from workflows.evals.agent_runtime_study.study import (  # noqa: E402
    printable_summary,
    run_live_study,
)


async def _run(args: argparse.Namespace) -> dict[str, object]:
    config = load_config(Path(args.config))
    config = with_overrides(
        config,
        models=tuple(args.model) or None,
        adapters=tuple(args.adapter) or None,
        case_keys=tuple(args.case) if args.case else None,
        run_live=args.live if args.live else None,
        output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
        timeout_seconds=args.timeout_seconds,
        max_output_tokens=args.max_output_tokens,
    )
    if config.run_live:
        return await run_live_study(config, project_root=PROJECT_ROOT)

    run_id = f"agent-runtime-static-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with StudyArtifactWriter(config.output_dir, run_id) as writer:
        provenance = capture_provenance(PROJECT_ROOT)
        provenance["effective_config"] = public_config(config)
        provenance["model_router_catalog"] = await capture_router_catalog(
            base_url=config.router_v1_base_url,
            api_key=config.router_api_key,
        )
        retrieval = run_retrieval_benchmark()
        candidates = await build_candidate_decision_evidence(WORKFLOW_ROOT)
        letta_baseline = None
        if args.letta_baseline:
            probe = LettaBaselineProbe(
                ade_api_base_url=config.ade_api_base_url,
                ade_api_key=config.ade_api_key,
                timeout_seconds=config.policy.timeout_seconds,
            )
            try:
                letta_baseline = probe.run(model_key=config.models[0])
            finally:
                probe.close()
        summary = {
            "run_id": run_id,
            "kind": "static",
            "provenance": provenance,
            "retrieval_benchmark": retrieval,
            "candidate_evidence": candidates,
            "letta_black_box_baseline": letta_baseline,
            "turns_path": str(writer.turns_path),
            "summary_path": str(writer.summary_path),
            "provenance_path": str(writer.provenance_path),
            "passed": 1 if candidates["selected_candidate"] else 0,
            "total": 1,
        }
        writer.write_provenance(provenance)
        writer.write_summary(summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the reproducible ADE-native agent runtime study."
    )
    parser.add_argument("--config", default=str(WORKFLOW_ROOT / "config.toml"))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument(
        "--adapter",
        action="append",
        choices=("custom_loop", "pydantic_ai"),
        default=[],
    )
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--letta-baseline", action="store_true")
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--max-output-tokens", type=int)
    args = parser.parse_args(argv)
    summary = asyncio.run(_run(args))
    print(printable_summary(summary))
    selected = (
        (summary.get("candidate_evidence") or {}).get("selected_candidate")
        if isinstance(summary.get("candidate_evidence"), dict)
        else None
    )
    if selected:
        print(f"selected_candidate: {selected}")
    return 0 if int(summary.get("passed", 0)) == int(summary.get("total", 1)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
