from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RunRecord = dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TestRunStore:
    """Owns Test Center run records and their durable manifest files."""

    def __init__(self, state_root: Path):
        self._state_root = Path(state_root).resolve()
        self._state_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._runs: dict[str, RunRecord] = {}
        self._load_runs()

    @property
    def state_root(self) -> Path:
        return self._state_root

    def allocate_output_directory(self) -> tuple[str, Path]:
        run_id = str(uuid.uuid4())
        output_dir = (self._state_root / run_id).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        return run_id, output_dir

    def create_run(
        self,
        *,
        run_id: str,
        run_type: str,
        output_dir: Path,
        command: list[str],
        options: dict[str, Any] | None = None,
    ) -> RunRecord:
        resolved_output_dir = output_dir.resolve()
        self._assert_output_directory(resolved_output_dir)
        run: RunRecord = {
            "run_id": run_id,
            "run_type": run_type,
            "options": dict(options or {}),
            "status": "queued",
            "command": command,
            "output_dir": str(resolved_output_dir),
            "created_at": utc_now_iso(),
            "started_at": "",
            "finished_at": "",
            "exit_code": None,
            "log_file": str((resolved_output_dir / "orchestrator.log").resolve()),
            "cancel_requested": False,
            "output_tail": [],
            "error": "",
            "_process": None,
        }
        with self._lock:
            self._runs[run_id] = run
            self.persist(run)
        return self.copy_record(run)

    @contextmanager
    def locked_run(self, run_id: str) -> Iterator[RunRecord | None]:
        """Yield a mutable record while holding the store's lifecycle lock."""

        with self._lock:
            yield self._runs.get(run_id)

    def get_snapshot(self, run_id: str) -> RunRecord | None:
        with self._lock:
            run = self._runs.get(run_id)
            return self.copy_record(run) if run else None

    def list_snapshots(self) -> list[RunRecord]:
        with self._lock:
            return [self.copy_record(run) for run in self._runs.values()]

    @staticmethod
    def copy_record(run: RunRecord) -> RunRecord:
        snapshot = dict(run)
        snapshot["command"] = list(run.get("command", []))
        snapshot["options"] = dict(run.get("options", {}))
        snapshot["output_tail"] = list(run.get("output_tail", []))
        snapshot["evaluation_decisions"] = [
            dict(decision)
            for decision in run.get("evaluation_decisions", [])
            if isinstance(decision, dict)
        ]
        return snapshot

    def persist(self, run: RunRecord) -> None:
        """Atomically persist a record while the caller holds ``locked_run``."""

        output_dir = Path(str(run["output_dir"])).resolve()
        self._assert_output_directory(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "run.json"
        temporary_path = output_dir / ".run.json.tmp"
        temporary_path.write_text(
            json.dumps(self._manifest_record(run), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(manifest_path)

    def _load_runs(self) -> None:
        for manifest_path in sorted(self._state_root.glob("*/run.json")):
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    continue
                run_id = str(payload.get("run_id", "") or "").strip()
                if not run_id or run_id != manifest_path.parent.name:
                    continue

                output_dir = manifest_path.parent.resolve()
                self._assert_output_directory(output_dir)
                run: RunRecord = {
                    **payload,
                    "run_id": run_id,
                    "output_dir": str(output_dir),
                    "log_file": str(output_dir / "orchestrator.log"),
                    "_process": None,
                }
                if not isinstance(run.get("options"), dict):
                    run["options"] = {}
                if run.get("status") in {"queued", "running"}:
                    run["status"] = "interrupted"
                    run["finished_at"] = utc_now_iso()
                    run["error"] = (
                        "The API process restarted before this run completed."
                    )
                    self.persist(run)
                self._runs[run_id] = run
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue

    def _assert_output_directory(self, output_dir: Path) -> None:
        if not output_dir.is_relative_to(self._state_root):
            raise ValueError(
                "Test run output directory must remain inside the runtime test-run directory"
            )

    @staticmethod
    def _manifest_record(run: RunRecord) -> RunRecord:
        return {key: value for key, value in run.items() if not key.startswith("_")}
