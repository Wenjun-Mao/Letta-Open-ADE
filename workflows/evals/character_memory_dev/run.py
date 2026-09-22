"""Run with python -m workflows.evals.character_memory_dev.run."""

import argparse
import json
import subprocess
from pathlib import Path
from uuid import uuid4

from .json_contract import loads
from .luna import generate
from .tasks import TASKS, build_prompt, validate_result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, choices=["luna-subscription"])
    parser.add_argument("--task", required=True, choices=TASKS)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path(__file__).parent / "outputs" / str(uuid4())
    try:
        data = loads(args.input.read_text(encoding="utf-8"))
        prompt = build_prompt(args.task, data)
        raw = generate(prompt, output, timeout_seconds=args.timeout_seconds)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Failed: {exc}; requested artifacts: {output}")
        return 1
    try:
        result = validate_result(args.task, raw, data)
    except (ValueError, TypeError, KeyError) as exc:
        (output / "validation.json").write_text(
            json.dumps({"valid": False, "error": str(exc)}) + "\n"
        )
        print(f"Invalid task output: {exc}; artifacts: {output}")
        return 1
    (output / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "validation.json").write_text(
        json.dumps({"valid": True, "task": args.task, "advisory_only": True}) + "\n"
    )
    print(f"Development output validated: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
