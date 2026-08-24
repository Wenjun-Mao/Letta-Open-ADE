from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ade_api.features.test_center.run_descriptors import (
    ArtifactDiscoveryContext,
    get_persisted_run_descriptor,
)


ArtifactRecord = dict[str, Any]


class TestRunArtifactAccess:
    """Discovers and reads only artifacts contained by Test Center run storage."""

    def __init__(self, state_root: Path):
        self._state_root = Path(state_root).resolve()

    def list_artifacts(self, run: Mapping[str, Any]) -> list[ArtifactRecord]:
        output_dir = str(run.get("output_dir", "") or "")
        if not output_dir:
            return []
        log_file = str(run.get("log_file", "") or "")
        context = ArtifactDiscoveryContext(
            output_dir=Path(output_dir),
            log_file=Path(log_file) if log_file else None,
            state_root=self._state_root,
        )
        run_type = str(run.get("run_type", "") or "")
        return get_persisted_run_descriptor(run_type).discover_artifacts(context)

    def read_artifact(
        self,
        *,
        run_id: str,
        run: Mapping[str, Any],
        artifact_id: str,
        max_lines: int,
    ) -> dict[str, Any] | None:
        artifacts = self.list_artifacts(run)
        target = next(
            (item for item in artifacts if item.get("artifact_id") == artifact_id),
            None,
        )
        if not target:
            return None

        artifact_path = Path(str(target.get("path", ""))).resolve()
        if not artifact_path.is_relative_to(self._state_root):
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
