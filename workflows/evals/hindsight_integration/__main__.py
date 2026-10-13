"""Local assessment artifact CLI. Deliberately has no live-execution command."""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from .casebook import FIXTURES, actor_material, build_lock, load_suite
from .models import Observation, Review, RuntimeBinding
from .offline import dry_run, scripted_runtime
from .records import model_from_json, read_json, write_new
from .report import write_report
from .reviews import record_review, review_template
from .runs import case_for, load_run, prepare_run, record_capture, start_attempt


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("validate-cases")
    freeze = commands.add_parser("freeze-cases")
    freeze.add_argument("--fixtures", type=Path, default=FIXTURES)
    freeze.add_argument("--out", type=Path, required=True)
    schema = commands.add_parser("schema")
    schema.add_argument("name", choices=["runtime", "observation", "review"])
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument(
        "--mode",
        choices=["offline_scripted", "live_capture"],
        default="offline_scripted",
    )
    prepare.add_argument("--runtime", type=Path)
    prepare.add_argument("--repeats", type=int, default=1)
    prepare.add_argument("--case", action="append", dest="cases")
    start = commands.add_parser("start")
    start.add_argument("--run", type=Path, required=True)
    start.add_argument("--case", required=True)
    start.add_argument("--repeat", type=int, required=True)
    actor = commands.add_parser("actor-input")
    actor.add_argument("--run", type=Path, required=True)
    actor.add_argument("--case", required=True)
    actor.add_argument("--out", type=Path, required=True)
    for name in ("capture", "review"):
        command = commands.add_parser(name)
        command.add_argument("--attempt", type=Path, required=True)
        command.add_argument("--input", type=Path, required=True)
    template = commands.add_parser("review-template")
    template.add_argument("--attempt", type=Path, required=True)
    template.add_argument("--out", type=Path, required=True)
    report = commands.add_parser("report")
    report.add_argument("--run", type=Path, required=True)
    report.add_argument("--out", type=Path, required=True)
    rehearsal = commands.add_parser("dry-run")
    rehearsal.add_argument("--out", type=Path, required=True)
    return cli


def dispatch(args: argparse.Namespace) -> dict:
    match args.command:
        case "validate-cases":
            suite = load_suite()
            return {
                "suite": suite["revision"],
                "sha256": suite["sha256"],
                "cases": len(suite["cases"]),
                "authored_examples": len(suite["calibration"]),
            }
        case "freeze-cases":
            write_new(args.out, build_lock(args.fixtures))
        case "schema":
            return {
                "runtime": RuntimeBinding,
                "observation": Observation,
                "review": Review,
            }[args.name].model_json_schema()
        case "prepare":
            if args.mode == "live_capture" and args.runtime is None:
                raise ValueError(
                    "Live capture requires explicit, pre-frozen runtime bindings"
                )
            runtime = (
                model_from_json(RuntimeBinding, read_json(args.runtime))
                if args.runtime
                else scripted_runtime()
            )
            prepare_run(
                args.out,
                run_id=args.run_id,
                mode=args.mode,
                runtime=runtime,
                repeats=args.repeats,
                case_ids=args.cases,
            )
        case "start":
            return {"attempt": str(start_attempt(args.run, args.case, args.repeat))}
        case "actor-input":
            run, _ = load_run(args.run)
            write_new(args.out, actor_material(case_for(run, args.case)))
        case "capture":
            issues = record_capture(
                args.attempt, model_from_json(Observation, read_json(args.input))
            )
            return {"stored": True, "mechanical_issues": issues}
        case "review-template":
            write_new(args.out, review_template(args.attempt))
        case "review":
            record_review(args.attempt, model_from_json(Review, read_json(args.input)))
        case "report":
            report = write_report(args.run, args.out)
            return {
                "mode": report["mode"],
                "planned_attempts": len(report["attempts"]),
                "report": str(args.out),
            }
        case "dry-run":
            report = dry_run(args.out)
            return {
                "mode": report["mode"],
                "planned_attempts": len(report["attempts"]),
                "report": str(args.out / "report"),
            }
    return {"written": True}


def main() -> int:
    args = parser().parse_args()
    try:
        result = dispatch(args)
    except ValidationError as error:
        # Pydantic's default text includes rejected input values, possibly secrets.
        print(
            json.dumps(
                {
                    "error": "Invalid evidence schema",
                    "fields": [list(item["loc"]) for item in error.errors()],
                }
            )
        )
        return 2
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("mechanical_issues") else 0


if __name__ == "__main__":
    raise SystemExit(main())
