"""Freeze plans and journal attempts before accepting local capture artifacts."""

from __future__ import annotations

import subprocess
from pathlib import Path

from agent_runtime_eval_contracts.qualification import policy_bundle_hash

from .casebook import PROJECT_ROOT, WORKFLOW_ROOT, load_suite
from .checks import mechanical_issues, reject_sensitive_fields
from .models import Attempt, Capture, Case, Mode, Observation, Run, RuntimeBinding
from .records import digest, load_sealed, seal, utc_now, write_new


def prepare_run(
    root: Path,
    *,
    run_id: str,
    mode: Mode,
    runtime: RuntimeBinding,
    repeats: int = 1,
    case_ids: list[str] | None = None,
) -> Run:
    suite = load_suite()
    selected = list(suite["cases"]) if case_ids is None else case_ids
    if (
        not selected
        or len(set(selected)) != len(selected)
        or set(selected) - set(suite["cases"])
    ):
        raise ValueError("Select unique, known case IDs")
    if runtime.persona_text != suite["persona"]["content"]:
        raise ValueError(
            "Runtime persona differs from the frozen starter persona; review a new suite"
        )
    reject_sensitive_fields(runtime.model_dump(mode="json"))
    files = [
        str(path.relative_to(WORKFLOW_ROOT))
        for path in sorted(WORKFLOW_ROOT.rglob("*"))
        if path.is_file()
        and "outputs" not in path.parts
        and "__pycache__" not in path.parts
        and path.suffix in {".py", ".json", ".md"}
    ]
    run = Run(
        run_id=run_id,
        mode=mode,
        prepared_at=utc_now(),
        suite_revision=suite["revision"],
        suite_sha256=suite["sha256"],
        repeats=repeats,
        runtime=runtime,
        evaluator_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True
        ).strip(),
        evaluator_files_sha256=policy_bundle_hash(WORKFLOW_ROOT, files).removeprefix(
            "sha256:"
        ),
        cases=[suite["cases"][case_id] for case_id in selected],
    )
    root.mkdir(parents=True, exist_ok=False)
    write_new(root / "run.json", seal("assessment-run", run))
    return run


def load_run(root: Path) -> tuple[Run, str]:
    return load_sealed(root / "run.json", "assessment-run", Run)


def case_for(run: Run, case_id: str) -> Case:
    for case in run.cases:
        if case.case_id == case_id:
            return case
    raise ValueError("Case is not in this frozen run")


def attempt_path(root: Path, case_id: str, repeat: int) -> Path:
    run, _ = load_run(root)
    case_for(run, case_id)
    if type(repeat) is not int or not 1 <= repeat <= run.repeats:
        raise ValueError("Repeat is outside the frozen run schedule")
    return root / "attempts" / f"{case_id}-r{repeat:03d}"


def start_attempt(root: Path, case_id: str, repeat: int) -> Path:
    run, run_hash = load_run(root)
    case = case_for(run, case_id)
    path = attempt_path(root, case_id, repeat)
    attempt = Attempt(
        run_sha256=run_hash,
        case_sha256=digest(case),
        case_id=case_id,
        repeat=repeat,
        started_at=utc_now(),
    )
    path.mkdir(parents=True, exist_ok=False)
    write_new(path / "attempt.json", seal("assessment-attempt", attempt))
    return path


def load_attempt(path: Path) -> tuple[Run, Case, Attempt, str]:
    root = path.parent.parent
    run, run_hash = load_run(root)
    attempt, attempt_hash = load_sealed(
        path / "attempt.json", "assessment-attempt", Attempt
    )
    case = case_for(run, attempt.case_id)
    if attempt.run_sha256 != run_hash or attempt.case_sha256 != digest(case):
        raise ValueError("Attempt belongs to a changed/different run or case")
    if path != attempt_path(root, attempt.case_id, attempt.repeat):
        raise ValueError("Attempt path does not match its frozen schedule")
    if attempt.started_at < run.prepared_at:
        raise ValueError("Attempt predates the frozen run")
    return run, case, attempt, attempt_hash


def record_capture(path: Path, observation: Observation) -> list[str]:
    run, case, attempt, attempt_hash = load_attempt(path)
    if observation.mode != run.mode:
        raise ValueError("Scripted and live evidence cannot be relabeled or mixed")
    reject_sensitive_fields(observation.model_dump(mode="json"))
    capture = Capture(
        attempt_sha256=attempt_hash,
        captured_at=utc_now(),
        observation=observation,
    )
    # Keep structurally representable failures, including bad scope and incomplete
    # captures. Their issues are reported, never discarded to improve a score.
    write_new(path / "capture.json", seal("assessment-capture", capture))
    return mechanical_issues(run, case, attempt, capture)


def load_capture(path: Path) -> tuple[Run, Case, Attempt, Capture, str, list[str]]:
    run, case, attempt, attempt_hash = load_attempt(path)
    capture, capture_hash = load_sealed(
        path / "capture.json", "assessment-capture", Capture
    )
    if capture.attempt_sha256 != attempt_hash or capture.observation.mode != run.mode:
        raise ValueError("Capture belongs to a different attempt or evidence mode")
    reject_sensitive_fields(capture.model_dump(mode="json"))
    return (
        run,
        case,
        attempt,
        capture,
        capture_hash,
        mechanical_issues(run, case, attempt, capture),
    )
