from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any


WORKFLOW_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = WORKFLOW_ROOT.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflows.evals.agent_runtime_parity.config import (  # noqa: E402
    ConfigError,
    load_config,
    with_overrides,
)
from workflows.evals.agent_runtime_parity.workflow import run_parity  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Letta-v2 versus ADE-native-v3 product parity evaluation."
    )
    parser.add_argument("--config", default=str(WORKFLOW_ROOT / "config.toml"))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--rounds", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--retry-count", type=int, default=None)
    parser.add_argument("--fixture-path", default="")
    parser.add_argument("--prompt-key", default="")
    parser.add_argument("--persona-key", default="")
    parser.add_argument("--legacy-api-base-url", default="")
    parser.add_argument("--native-api-base-url", default="")
    parser.add_argument("--legacy-api-key", default="")
    parser.add_argument("--native-api-key", default="")
    parser.add_argument("--database-url", default="")
    parser.add_argument("--legacy-model", default="")
    parser.add_argument("--legacy-embedding", default="")
    parser.add_argument("--native-conversation-model", default="")
    parser.add_argument("--native-reviewer-model", default="")
    parser.add_argument("--native-embedding-model", default="")
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> Any:
    overrides: dict[str, object] = {}
    for field in (
        "output_dir",
        "fixture_path",
        "prompt_key",
        "persona_key",
        "legacy_api_base_url",
        "native_api_base_url",
        "legacy_api_key",
        "native_api_key",
        "database_url",
        "legacy_model",
        "legacy_embedding",
        "native_conversation_model",
        "native_reviewer_model",
        "native_embedding_model",
    ):
        value = getattr(args, field)
        if value:
            overrides[field] = value
    for field in ("rounds", "timeout_seconds", "retry_count"):
        value = getattr(args, field)
        if value is not None:
            overrides[field] = value
    return with_overrides(load_config(Path(args.config)), **overrides)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = config_from_args(args)
        summary = asyncio.run(run_parity(config, run_id=args.run_id or None))
    except ConfigError as exc:
        raise SystemExit(f"configuration error: {exc}") from exc
    print(
        f"parity run {summary['run_id']}: pass={summary['pass']} "
        f"rounds={summary['rounds_passed']}/{summary['rounds_requested']}"
    )
    for name, path in summary["artifact_paths"].items():
        print(f"{name}: {path}")
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
