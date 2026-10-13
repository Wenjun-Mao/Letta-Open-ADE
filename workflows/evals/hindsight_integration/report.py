"""All-attempt reporting, never an averaged character-quality score."""

from collections import Counter
from pathlib import Path

from .models import LENSES, RESULTS
from .records import digest, seal, write_bytes_new, write_new
from .reviews import load_reviews
from .runs import attempt_path, load_attempt, load_capture, load_run


def build_report(root: Path) -> dict:
    run, run_hash = load_run(root)
    expected = {
        attempt_path(root, case.case_id, repeat)
        for case in run.cases
        for repeat in range(1, run.repeats + 1)
    }
    if (root / "attempts").exists() and set((root / "attempts").iterdir()) - expected:
        raise ValueError("Unexpected attempt outside the frozen schedule")
    rows = []
    scopes: dict[str, list[str]] = {}
    for case in run.cases:
        for repeat in range(1, run.repeats + 1):
            path = attempt_path(root, case.case_id, repeat)
            row = {
                "attempt": path.name,
                "case_id": case.case_id,
                "family": case.family,
                "history_kind": case.history_kind,
                "repeat": repeat,
                "state": "not_run",
                "mechanical_issues": [],
                "judgments": None,
                "review_history": [],
            }
            rows.append(row)
            if not path.exists():
                continue
            load_attempt(path)
            row["state"] = "incomplete"
            if not (path / "capture.json").exists():
                if list(path.glob("review-*.json")):
                    raise ValueError("Review exists without its capture")
                continue
            _, _, _, capture, capture_hash, issues = load_capture(path)
            observation = capture.observation
            row.update(
                state="captured_unreviewed",
                capture_sha256=capture_hash,
                execution_status=observation.status,
                stage=observation.stage,
                error=observation.error,
                mechanical_issues=issues,
                limitations=observation.limitations,
                reply=observation.reply,
            )
            for scope in {
                digest(s)
                for s in (observation.source_scope, observation.target_scope)
                if s
            }:
                scopes.setdefault(scope, []).append(path.name)
            history = load_reviews(path)
            if history:
                review, review_hash = history[-1]
                row.update(
                    state="reviewed",
                    review_sha256=review_hash,
                    reviewer=review.reviewer,
                    review_kind=review.kind,
                    judgments={
                        lens: item.model_dump()
                        for lens, item in review.judgments.items()
                    },
                    review_history=[
                        {"sha256": sha, **item.model_dump(mode="json")}
                        for item, sha in history
                    ],
                )
    reused = {
        attempt
        for attempts in scopes.values()
        if len(attempts) > 1
        for attempt in attempts
    }
    for row in rows:
        if row["attempt"] in reused:
            row["mechanical_issues"].append(
                "relationship_scope_reused_between_attempts"
            )
        row["assessable"] = row["state"] == "reviewed" and not row["mechanical_issues"]
    summaries = {}
    for family in sorted({case.family for case in run.cases}):
        selected = [row for row in rows if row["family"] == family]
        summaries[family] = {
            "independent_cases": len({row["case_id"] for row in selected}),
            "planned_attempts": len(selected),
            "attempt_states": dict(Counter(row["state"] for row in selected)),
            "mechanically_invalid_captures": sum(
                bool(row["mechanical_issues"]) for row in selected
            ),
            "assessable_reviewed_attempts": sum(row["assessable"] for row in selected),
            "lenses": {
                lens: {
                    "result_counts": {
                        result: sum(
                            row["assessable"]
                            and row["judgments"][lens]["result"] == result
                            for row in selected
                        )
                        for result in RESULTS
                    },
                    "denominator": sum(row["assessable"] for row in selected),
                }
                for lens in LENSES
            },
        }
    return {
        "schema_version": 1,
        "run_id": run.run_id,
        "run_sha256": run_hash,
        "mode": run.mode,
        "suite_revision": run.suite_revision,
        "suite_sha256": run.suite_sha256,
        "evaluator_revision": run.evaluator_revision,
        "evaluator_files_sha256": run.evaluator_files_sha256,
        "limitations": [
            "No overall score or numeric pass threshold; three lenses remain separate.",
            "Repeated attempts are not independent cases; empty denominators are not passes.",
            "Controlled histories test response behavior, not product establishment of that history.",
            "Q04 creation alone does not establish later continuity of a newly created episode.",
            "Captures are operator declarations with drift checks, not external authenticity proofs.",
        ]
        + (
            ["SCRIPTED OFFLINE MECHANICS ONLY: no model-quality evidence."]
            if run.mode == "offline_scripted"
            else []
        ),
        "families": summaries,
        "repeat_consistency": {
            case.case_id: {
                lens: [
                    row["judgments"][lens]["result"] if row["assessable"] else None
                    for row in rows
                    if row["case_id"] == case.case_id
                ]
                for lens in LENSES
            }
            for case in run.cases
        },
        "attempts": rows,
    }


def report_markdown(report: dict) -> str:
    lines = [
        "# Character Assessment Report",
        "",
        f"Mode: `{report['mode']}`.",
        f"Run: `{report['run_id']}`; suite: `{report['suite_revision']}`.",
        "",
        *[f"- {item}" for item in report["limitations"]],
        "",
        "## Coverage",
        "",
        "| Promise | Independent cases | Planned attempts | Assessable reviews | Invalid captures |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for family, summary in report["families"].items():
        lines.append(
            f"| {family} | {summary['independent_cases']} | {summary['planned_attempts']} | "
            f"{summary['assessable_reviewed_attempts']} | {summary['mechanically_invalid_captures']} |"
        )
    lines += [
        "",
        "## Per-Lens Results",
        "",
        "Counts include only reviewed, mechanically eligible captures; zero is not a pass.",
        "",
        "| Promise | Lens | Meets | Partly meets | Fails | Cannot assess | Denominator |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for family, summary in report["families"].items():
        for lens, result in summary["lenses"].items():
            counts = " | ".join(
                str(result["result_counts"][label]) for label in RESULTS
            )
            lines.append(f"| {family} | {lens} | {counts} | {result['denominator']} |")
    lines += ["", "## Attempts", ""]
    for row in report["attempts"]:
        lines += [
            f"### {row['attempt']}",
            "",
            f"State: {row['state']}; history: {row['history_kind']}.",
        ]
        if row["mechanical_issues"]:
            lines.append(
                "Mechanical issues: " + ", ".join(row["mechanical_issues"]) + "."
            )
        if row.get("error"):
            lines.append(f"Execution stopped at {row['stage']}: {row['error']}")
        for limitation in row.get("limitations", []):
            lines.append(f"Limitation: {limitation}")
        if row["judgments"]:
            lines.append(
                f"Reviewer: {row['reviewer']} ({row['review_kind']}); revisions: {len(row['review_history'])}."
            )
            for lens, judgment in row["judgments"].items():
                lines += [
                    f"- {lens}: **{judgment['result']}**. Quote: {judgment['quote']!r}. {judgment['rationale']}"
                ]
            for old in row["review_history"][1:]:
                lines.append(
                    f"Review correction {old['revision']}: {old['change_reason']}"
                )
        lines.append("")
    return "\n".join(lines)


def write_report(root: Path, output: Path) -> dict:
    report = build_report(root)
    output.mkdir(parents=True, exist_ok=False)
    write_new(output / "report.json", seal("assessment-report", report))
    write_bytes_new(output / "report.md", report_markdown(report).encode("utf-8"))
    return report
