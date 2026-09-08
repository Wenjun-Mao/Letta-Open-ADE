from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ade_api.features.test_center.artifact_access import TestRunArtifactAccess
from ade_api.features.test_center.process_executor import TestRunProcessExecutor
from ade_api.features.test_center.run_descriptors import (
    RUN_DESCRIPTORS,
    get_run_descriptor,
)
from ade_api.features.test_center.run_store import RunRecord, TestRunStore


class TestRunOrchestrator:
    """Coordinates the three explicit Test Center workflows and their artifacts."""

    def __init__(self, project_root: Path, *, state_root: Path | None = None):
        project_root = Path(project_root).resolve()
        resolved_state_root = (
            state_root or project_root / "data" / "runtime" / "test-runs"
        )
        self._run_store = TestRunStore(resolved_state_root)
        self._artifact_access = TestRunArtifactAccess(self._run_store.state_root)
        self._process_executor = TestRunProcessExecutor(project_root, self._run_store)

    def _build_command(
        self,
        *,
        run_type: str,
        output_dir: Path,
        options: dict[str, Any],
    ) -> list[str]:
        return get_run_descriptor(run_type).build_command(output_dir, options)

    def _resolve_artifacts(self, run: dict[str, Any]) -> list[dict[str, Any]]:
        return self._artifact_access.list_artifacts(run)

    def _public_record(self, run: RunRecord) -> dict[str, Any]:
        return {
            "run_id": run["run_id"],
            "run_type": run["run_type"],
            "status": run["status"],
            "command": list(run["command"]),
            "created_at": run["created_at"],
            "started_at": run.get("started_at", ""),
            "finished_at": run.get("finished_at", ""),
            "exit_code": run.get("exit_code"),
            "log_file": run.get("log_file", ""),
            "cancel_requested": bool(run.get("cancel_requested", False)),
            "output_tail": list(run.get("output_tail", [])),
            "error": run.get("error", ""),
            "artifacts": self._resolve_artifacts(run),
        }

    def create_run(
        self,
        *,
        run_type: str,
        **options: Any,
    ) -> dict[str, Any]:
        run_id, output_dir = self._run_store.allocate_output_directory()
        descriptor = get_run_descriptor(run_type)
        command = descriptor.build_command(output_dir, options)
        environment = descriptor.build_environment(options, os.environ)
        run = self._run_store.create_run(
            run_id=run_id,
            run_type=run_type,
            output_dir=output_dir,
            command=command,
            options=options,
        )
        self._process_executor.set_environment(run_id, environment)
        self._process_executor.start(run_id)
        return self._public_record(run)

    def list_runs(self) -> list[dict[str, Any]]:
        runs = [
            self._public_record(run)
            for run in self._run_store.list_snapshots()
            if run.get("run_type") in RUN_DESCRIPTORS
        ]
        runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return runs

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run = self._run_store.get_snapshot(run_id)
        return (
            self._public_record(run)
            if run and run.get("run_type") in RUN_DESCRIPTORS
            else None
        )

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]] | None:
        run = self._run_store.get_snapshot(run_id)
        return (
            self._resolve_artifacts(run)
            if run and run.get("run_type") in RUN_DESCRIPTORS
            else None
        )

    def read_artifact(
        self, run_id: str, artifact_id: str, *, max_lines: int = 400
    ) -> dict[str, Any] | None:
        run = self._run_store.get_snapshot(run_id)
        if not run or run.get("run_type") not in RUN_DESCRIPTORS:
            return None
        return self._artifact_access.read_artifact(
            run_id=run_id,
            run=run,
            artifact_id=artifact_id,
            max_lines=max_lines,
        )

    def cancel_run(self, run_id: str) -> dict[str, Any] | None:
        existing = self._run_store.get_snapshot(run_id)
        if not existing or existing.get("run_type") not in RUN_DESCRIPTORS:
            return None
        if not self._process_executor.cancel(run_id):
            return None
        run = self._run_store.get_snapshot(run_id)
        return (
            self._public_record(run)
            if run and run.get("run_type") in RUN_DESCRIPTORS
            else None
        )

    def shutdown(self) -> None:
        self._process_executor.shutdown()
