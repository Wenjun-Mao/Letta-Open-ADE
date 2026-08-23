from __future__ import annotations

import os
import subprocess
import sys

from agent_platform_api.dependencies import build_application_services
from agent_platform_api.settings import AgentPlatformSettings


def test_importing_app_does_not_create_runtime_state(tmp_path) -> None:
    runtime_dir = tmp_path / "runtime"
    persona_db = runtime_dir / "personas" / "personas.sqlite3"
    env = {
        **os.environ,
        "AGENT_PLATFORM_RUNTIME_DATA_DIR": str(runtime_dir),
        "AGENT_PLATFORM_PERSONA_DB_PATH": str(persona_db),
        "AGENT_PLATFORM_PERSONA_SEED_JSONL_PATH": str(tmp_path / "missing-seed.jsonl"),
    }

    result = subprocess.run(
        [sys.executable, "-c", "import agent_platform_api.app"],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not runtime_dir.exists()


def test_building_application_services_initializes_runtime_state_without_sdk_retries(tmp_path) -> None:
    settings = AgentPlatformSettings(
        runtime_data_dir=str(tmp_path / "runtime"),
        persona_db_path=str(tmp_path / "runtime" / "personas" / "personas.sqlite3"),
        persona_seed_jsonl_path=str(tmp_path / "missing-seed.jsonl"),
    )

    services = build_application_services(settings=settings, project_root=tmp_path)

    assert (tmp_path / "runtime" / "personas" / "personas.sqlite3").is_file()
    assert services.client.max_retries == 0
