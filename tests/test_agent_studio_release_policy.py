from __future__ import annotations

from pathlib import Path

import pytest

from ade_api.features.agent_runtime_v3.errors import RuntimeNotReady
from ade_api.features.agent_runtime_v3.release_policy import (
    ensure_agent_studio_release_ready,
)


def test_development_mode_does_not_require_cutover_evidence() -> None:
    ensure_agent_studio_release_ready("development")


def test_release_mode_fails_closed_without_cutover_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ade_api.platform.project_paths as project_paths

    monkeypatch.setattr(project_paths, "PROJECT_ROOT", tmp_path)

    with pytest.raises(RuntimeNotReady, match="reviewed cutover evidence"):
        ensure_agent_studio_release_ready("release")
