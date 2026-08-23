from __future__ import annotations

import json
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent_platform_api.testing.run_descriptors import (
    ArtifactDiscoveryContext,
    get_persisted_run_descriptor,
    get_run_descriptor,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlatformTestOrchestrator:
    """Launch tests in-process while persisting durable run state and artifacts."""

    def __init__(self, project_root: Path, *, state_root: Path | None = None):
        self._project_root = Path(project_root).resolve()
        self._log_root = (
            state_root or self._project_root / "data" / "runtime" / "test-runs"
        ).resolve()
        self._log_root.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._runs: dict[str, dict[str, Any]] = {}
        self._load_runs()

    def _load_runs(self) -> None:
        for manifest_path in sorted(self._log_root.glob("*/run.json")):
            try:
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    continue
                run_id = str(payload.get("run_id", "") or "").strip()
                if not run_id or run_id != manifest_path.parent.name:
                    continue

                output_dir = manifest_path.parent.resolve()
                if not output_dir.is_relative_to(self._log_root):
                    continue
                run = {
                    **payload,
                    "run_id": run_id,
                    "output_dir": str(output_dir),
                    "log_file": str(output_dir / "orchestrator.log"),
                    "_process": None,
                }
                if run.get("status") in {"queued", "running"}:
                    run["status"] = "interrupted"
                    run["finished_at"] = _utc_now_iso()
                    run["error"] = (
                        "The API process restarted before this run completed."
                    )
                    self._persist_run(run)
                self._runs[run_id] = run
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue

    @staticmethod
    def _manifest_record(run: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in run.items() if not key.startswith("_")}

    def _persist_run(self, run: dict[str, Any]) -> None:
        output_dir = Path(str(run["output_dir"])).resolve()
        if not output_dir.is_relative_to(self._log_root):
            raise ValueError(
                "Test run output directory must remain inside the runtime test-run directory"
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "run.json"
        temporary_path = output_dir / ".run.json.tmp"
        temporary_path.write_text(
            json.dumps(self._manifest_record(run), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(manifest_path)

    def _build_command(
        self,
        *,
        run_type: str,
        output_dir: Path,
        options: dict[str, Any],
    ) -> list[str]:
        return get_run_descriptor(run_type).build_command(output_dir, options)

    def _public_record(self, run: dict[str, Any]) -> dict[str, Any]:
        artifacts = self._resolve_artifacts(run)
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
            "artifacts": artifacts,
        }

    def _resolve_artifacts(self, run: dict[str, Any]) -> list[dict[str, Any]]:
        output_dir = str(run.get("output_dir", "") or "")
        if not output_dir:
            return []
        log_file = str(run.get("log_file", "") or "")
        context = ArtifactDiscoveryContext(
            output_dir=Path(output_dir),
            log_file=Path(log_file) if log_file else None,
            state_root=self._log_root,
        )
        run_type = str(run.get("run_type", "") or "")
        return get_persisted_run_descriptor(run_type).discover_artifacts(context)

    def create_run(
        self,
        *,
        run_type: str,
        **options: Any,
    ) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        output_dir = (self._log_root / run_id).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        command = self._build_command(
            run_type=run_type,
            output_dir=output_dir,
            options=options,
        )

        log_file = str((output_dir / "orchestrator.log").resolve())

        run: dict[str, Any] = {
            "run_id": run_id,
            "run_type": run_type,
            "status": "queued",
            "command": command,
            "output_dir": str(output_dir),
            "created_at": _utc_now_iso(),
            "started_at": "",
            "finished_at": "",
            "exit_code": None,
            "log_file": log_file,
            "cancel_requested": False,
            "output_tail": [],
            "error": "",
            "_process": None,
        }

        with self._lock:
            self._runs[run_id] = run
            self._persist_run(run)

        worker = threading.Thread(target=self._run_worker, args=(run_id,), daemon=True)
        worker.start()

        return self._public_record(run)

    def _run_worker(self, run_id: str) -> None:
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return
            if run.get("cancel_requested"):
                run["status"] = "cancelled"
                run["finished_at"] = _utc_now_iso()
                self._persist_run(run)
                return
            run["status"] = "running"
            run["started_at"] = _utc_now_iso()
            self._persist_run(run)
            command = list(run["command"])
            log_file = str(run["log_file"])

        try:
            with open(log_file, "w", encoding="utf-8") as log:
                log.write(f"Command: {' '.join(command)}\n")
                log.write(f"Started: {run['started_at']}\n\n")

                process = subprocess.Popen(
                    command,
                    cwd=str(self._project_root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                with self._lock:
                    tracked = self._runs.get(run_id)
                    if not tracked:
                        process.kill()
                        return
                    tracked["_process"] = process

                assert process.stdout is not None
                line_count = 0
                for line in process.stdout:
                    log.write(line)
                    log.flush()

                    clean_line = line.rstrip("\n")
                    with self._lock:
                        tracked = self._runs.get(run_id)
                        if not tracked:
                            continue
                        tail = tracked.setdefault("output_tail", [])
                        tail.append(clean_line)
                        if len(tail) > 200:
                            del tail[:-200]
                        line_count += 1
                        if line_count % 25 == 0:
                            self._persist_run(tracked)

                exit_code = process.wait()

                with self._lock:
                    tracked = self._runs.get(run_id)
                    if not tracked:
                        return
                    tracked["exit_code"] = int(exit_code)
                    tracked["finished_at"] = _utc_now_iso()
                    tracked["_process"] = None
                    if tracked.get("cancel_requested"):
                        tracked["status"] = "cancelled"
                    else:
                        tracked["status"] = "passed" if exit_code == 0 else "failed"
                    self._persist_run(tracked)

        except Exception as exc:
            with self._lock:
                tracked = self._runs.get(run_id)
                if not tracked:
                    return
                tracked["status"] = "error"
                tracked["error"] = str(exc)
                tracked["finished_at"] = _utc_now_iso()
                tracked["_process"] = None
                self._persist_run(tracked)

    def list_runs(self) -> list[dict[str, Any]]:
        with self._lock:
            runs = [self._public_record(run) for run in self._runs.values()]

        runs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return runs

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return None
            return self._public_record(run)

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]] | None:
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return None
            run_snapshot = {
                "run_type": str(run.get("run_type", "") or ""),
                "log_file": str(run.get("log_file", "") or ""),
                "output_dir": str(run.get("output_dir", "") or ""),
            }

        return self._resolve_artifacts(run_snapshot)

    def read_artifact(
        self, run_id: str, artifact_id: str, *, max_lines: int = 400
    ) -> dict[str, Any] | None:
        artifacts = self.list_artifacts(run_id)
        if artifacts is None:
            return None

        target = next(
            (item for item in artifacts if item.get("artifact_id") == artifact_id), None
        )
        if not target:
            return None

        artifact_path = Path(str(target.get("path", ""))).resolve()
        if not artifact_path.is_relative_to(self._log_root):
            return None
        if not artifact_path.exists():
            return {
                "run_id": run_id,
                "artifact": target,
                "content": "",
                "truncated": False,
                "line_count": 0,
            }

        resolved_max_lines = max(1, min(int(max_lines), 2000))
        lines = artifact_path.read_text(encoding="utf-8", errors="replace").splitlines()
        truncated = len(lines) > resolved_max_lines
        if truncated:
            lines = lines[-resolved_max_lines:]

        return {
            "run_id": run_id,
            "artifact": target,
            "content": "\n".join(lines),
            "truncated": truncated,
            "line_count": len(lines),
        }

    def cancel_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return None

            run["cancel_requested"] = True
            process = run.get("_process")
            if process and run.get("status") == "running":
                process.terminate()
            self._persist_run(run)

            return self._public_record(run)

    def shutdown(self) -> None:
        """Persist terminal state and terminate child processes during API shutdown."""
        with self._lock:
            for run in self._runs.values():
                if run.get("status") not in {"queued", "running"}:
                    continue
                run["cancel_requested"] = True
                run["status"] = "cancelled"
                run["finished_at"] = _utc_now_iso()
                run["error"] = (
                    "The run was cancelled because the Agent Platform API shut down."
                )
                process = run.get("_process")
                if process is not None:
                    process.terminate()
                self._persist_run(run)
