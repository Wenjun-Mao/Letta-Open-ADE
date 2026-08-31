from __future__ import annotations

from pathlib import Path
from typing import Any

from ade_api.features.test_center.artifact_access import TestRunArtifactAccess
from ade_api.features.test_center.chat_memory_evaluations import (
    ChatMemoryEvaluationReader,
)
from ade_api.features.test_center.chat_memory_evaluation_comparisons import (
    build_chat_memory_evaluation_comparison,
)
from ade_api.features.test_center.chat_memory_evaluation_decisions import (
    ChatMemoryEvaluationDecisionConflict,
    append_evaluation_decision,
)
from ade_api.features.test_center.process_executor import TestRunProcessExecutor
from ade_api.features.test_center.run_descriptors import get_run_descriptor
from ade_api.features.test_center.run_store import RunRecord, TestRunStore


class TestRunOrchestrator:
    """Feature-facing coordinator for Test Center test runs."""

    def __init__(self, project_root: Path, *, state_root: Path | None = None):
        project_root = Path(project_root).resolve()
        resolved_state_root = (
            state_root or project_root / "data" / "runtime" / "test-runs"
        )
        self._run_store = TestRunStore(resolved_state_root)
        self._artifact_access = TestRunArtifactAccess(self._run_store.state_root)
        self._chat_memory_evaluations = ChatMemoryEvaluationReader(
            self._run_store.state_root
        )
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
        command = self._build_command(
            run_type=run_type,
            output_dir=output_dir,
            options=options,
        )
        run = self._run_store.create_run(
            run_id=run_id,
            run_type=run_type,
            output_dir=output_dir,
            command=command,
            options=options,
        )
        self._process_executor.start(run_id)
        return self._public_record(run)

    def list_runs(self) -> list[dict[str, Any]]:
        runs = [self._public_record(run) for run in self._run_store.list_snapshots()]
        runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return runs

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run = self._run_store.get_snapshot(run_id)
        return self._public_record(run) if run else None

    def list_chat_memory_evaluations(self) -> list[dict[str, Any]]:
        runs = [
            run
            for run in self._run_store.list_snapshots()
            if run.get("run_type") == "chat_memory_eval"
        ]
        runs.sort(key=lambda run: str(run.get("created_at", "")), reverse=True)
        items = [self._chat_memory_evaluations.list_item(run) for run in runs]
        preferred_run_id = self._preferred_verified_baseline_run_id(items)
        for item in items:
            item["preferred_baseline"] = item.get("run_id") == preferred_run_id
        return items

    def get_chat_memory_evaluation(self, run_id: str) -> dict[str, Any] | None:
        run = self._run_store.get_snapshot(run_id)
        if not run or run.get("run_type") != "chat_memory_eval":
            return None
        preferred_run_id = self._preferred_verified_baseline_run_id(
            self.list_chat_memory_evaluations()
        )
        return self._chat_memory_evaluations.detail(
            run,
            preferred_baseline=(run_id == preferred_run_id),
        )

    def compare_chat_memory_evaluations(
        self, baseline_run_id: str, candidate_run_id: str
    ) -> dict[str, Any] | None:
        baseline = self.get_chat_memory_evaluation(baseline_run_id)
        candidate = self.get_chat_memory_evaluation(candidate_run_id)
        if baseline is None or candidate is None:
            return None
        return build_chat_memory_evaluation_comparison(baseline, candidate)

    def record_chat_memory_evaluation_decision(
        self,
        run_id: str,
        *,
        outcome: str,
        expected_provenance_sha256: str,
        expected_evidence_sha256: str,
        baseline_run_id: str | None = None,
        expected_baseline_provenance_sha256: str | None = None,
        expected_baseline_evidence_sha256: str | None = None,
        note: str = "",
    ) -> dict[str, Any] | None:
        if baseline_run_id == run_id:
            raise ChatMemoryEvaluationDecisionConflict(
                "A candidate cannot be compared with itself"
            )
        detail = self.get_chat_memory_evaluation(run_id)
        if detail is None:
            return None
        baseline_provenance_sha256: str | None = None
        baseline_evidence_sha256: str | None = None
        if baseline_run_id is not None:
            baseline = self.get_chat_memory_evaluation(baseline_run_id)
            if baseline is None:
                raise ChatMemoryEvaluationDecisionConflict(
                    "The selected baseline run does not exist"
                )
            if baseline.get("provenance_detail") is None:
                raise ChatMemoryEvaluationDecisionConflict(
                    "The selected baseline has no immutable provenance"
                )
            baseline_provenance_sha256 = str(
                baseline["provenance_detail"]["provenance_sha256"]
            )
            if expected_baseline_provenance_sha256 != baseline_provenance_sha256:
                raise ChatMemoryEvaluationDecisionConflict(
                    "Baseline evidence changed after it was reviewed; refresh before deciding"
                )
            baseline_evidence_sha256 = str(baseline.get("evidence_sha256") or "")
            if expected_baseline_evidence_sha256 != baseline_evidence_sha256:
                raise ChatMemoryEvaluationDecisionConflict(
                    "Baseline output evidence changed after it was reviewed; refresh before deciding"
                )
        elif (
            expected_baseline_provenance_sha256 is not None
            or expected_baseline_evidence_sha256 is not None
        ):
            raise ChatMemoryEvaluationDecisionConflict(
                "Baseline provenance/evidence cannot be supplied without a baseline run"
            )
        return append_evaluation_decision(
            run_store=self._run_store,
            run_id=run_id,
            detail=detail,
            outcome=outcome,
            expected_provenance_sha256=expected_provenance_sha256,
            expected_evidence_sha256=expected_evidence_sha256,
            baseline_run_id=baseline_run_id,
            baseline_provenance_sha256=baseline_provenance_sha256,
            baseline_evidence_sha256=baseline_evidence_sha256,
            note=note,
        )

    @staticmethod
    def _preferred_verified_baseline_run_id(
        items: list[dict[str, Any]],
    ) -> str | None:
        promoted = [
            item
            for item in items
            if item.get("ready") is True
            and isinstance(item.get("decision"), dict)
            and item["decision"].get("outcome") == "promote"
        ]
        if not promoted:
            return None
        promoted.sort(
            key=lambda item: (
                str(item["decision"].get("recorded_at", "")),
                str(item["decision"].get("decision_id", "")),
            ),
            reverse=True,
        )
        return str(promoted[0].get("run_id", "")) or None

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]] | None:
        run = self._run_store.get_snapshot(run_id)
        return self._resolve_artifacts(run) if run else None

    def read_artifact(
        self, run_id: str, artifact_id: str, *, max_lines: int = 400
    ) -> dict[str, Any] | None:
        run = self._run_store.get_snapshot(run_id)
        if not run:
            return None
        return self._artifact_access.read_artifact(
            run_id=run_id,
            run=run,
            artifact_id=artifact_id,
            max_lines=max_lines,
        )

    def cancel_run(self, run_id: str) -> dict[str, Any] | None:
        if not self._process_executor.cancel(run_id):
            return None
        run = self._run_store.get_snapshot(run_id)
        return self._public_record(run) if run else None

    def shutdown(self) -> None:
        self._process_executor.shutdown()
