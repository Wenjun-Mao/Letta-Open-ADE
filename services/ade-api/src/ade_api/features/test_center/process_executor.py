from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from ade_api.features.test_center.run_store import TestRunStore, utc_now_iso


class TestRunProcessExecutor:
    """Executes Test Center subprocesses and updates their stored lifecycle state."""

    def __init__(self, project_root: Path, run_store: TestRunStore):
        self._project_root = Path(project_root).resolve()
        self._run_store = run_store

    def start(self, run_id: str) -> None:
        worker = threading.Thread(target=self._run_worker, args=(run_id,), daemon=True)
        worker.start()

    def cancel(self, run_id: str) -> bool:
        with self._run_store.locked_run(run_id) as run:
            if not run:
                return False
            run["cancel_requested"] = True
            process = run.get("_process")
            if process and run.get("status") == "running":
                process.terminate()
            self._run_store.persist(run)
            return True

    def shutdown(self) -> None:
        """Persist terminal state and terminate child processes during API shutdown."""

        for run in self._run_store.list_snapshots():
            if run.get("status") not in {"queued", "running"}:
                continue
            with self._run_store.locked_run(str(run["run_id"])) as tracked:
                if not tracked or tracked.get("status") not in {"queued", "running"}:
                    continue
                tracked["cancel_requested"] = True
                tracked["status"] = "cancelled"
                tracked["finished_at"] = utc_now_iso()
                tracked["error"] = "The run was cancelled because ADE API shut down."
                process = tracked.get("_process")
                if process is not None:
                    process.terminate()
                self._run_store.persist(tracked)

    def _run_worker(self, run_id: str) -> None:
        with self._run_store.locked_run(run_id) as run:
            if not run:
                return
            if run.get("cancel_requested"):
                run["status"] = "cancelled"
                run["finished_at"] = utc_now_iso()
                self._run_store.persist(run)
                return
            run["status"] = "running"
            run["started_at"] = utc_now_iso()
            self._run_store.persist(run)
            command = list(run["command"])
            log_file = str(run["log_file"])
            started_at = str(run["started_at"])

        try:
            with open(log_file, "w", encoding="utf-8") as log:
                log.write(f"Command: {' '.join(command)}\n")
                log.write(f"Started: {started_at}\n\n")

                process = subprocess.Popen(
                    command,
                    cwd=str(self._project_root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                with self._run_store.locked_run(run_id) as tracked:
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
                    with self._run_store.locked_run(run_id) as tracked:
                        if not tracked:
                            continue
                        tail = tracked.setdefault("output_tail", [])
                        tail.append(clean_line)
                        if len(tail) > 200:
                            del tail[:-200]
                        line_count += 1
                        if line_count % 25 == 0:
                            self._run_store.persist(tracked)

                exit_code = process.wait()

                with self._run_store.locked_run(run_id) as tracked:
                    if not tracked:
                        return
                    tracked["exit_code"] = int(exit_code)
                    tracked["finished_at"] = utc_now_iso()
                    tracked["_process"] = None
                    if tracked.get("cancel_requested"):
                        tracked["status"] = "cancelled"
                    else:
                        tracked["status"] = "passed" if exit_code == 0 else "failed"
                    self._run_store.persist(tracked)

        except Exception as exc:
            with self._run_store.locked_run(run_id) as tracked:
                if not tracked:
                    return
                tracked["status"] = "error"
                tracked["error"] = str(exc)
                tracked["finished_at"] = utc_now_iso()
                tracked["_process"] = None
                self._run_store.persist(tracked)
