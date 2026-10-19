"""Actual application dependency construction against private staged content."""

from ade_api.platform.dependencies import build_application_services
from ade_api.platform.project_paths import PROJECT_ROOT
from ade_api.platform.settings import AdeApiSettings
from content.prompts.system.chat.chat_v20261019 import PROMPT
from workflows.evals.hindsight_integration.runtime_assets import (
    require_runtime_assets,
    seed_runtime_assets,
)


def test_application_startup_assets_live_in_the_private_runtime_copy(tmp_path):
    activation = tmp_path / "activation"
    (activation / "runtime-data").mkdir(mode=0o700, parents=True)
    seed_runtime_assets(activation, PROJECT_ROOT / "content")
    root = activation / "runtime-data"
    services = build_application_services(
        settings=AdeApiSettings(
            _env_file=None,
            runtime_data_dir=str(root),
            persona_db_path=str(root / "personas/personas.sqlite3"),
            persona_seed_jsonl_path=str(root / "content/personas/personas.jsonl"),
        ),
        project_root=root,
    )
    try:
        assert (
            services.prompt_persona_registry.get_template("prompt", "chat_v20261019")[
                "content"
            ]
            == PROMPT
        )
        assert services.prompt_persona_registry.persona_archive_dir.is_dir()
        assert services.label_schema_registry.archive_dir.is_dir()
        assert (root / "personas/personas.sqlite3").is_file()
        require_runtime_assets(activation)
    finally:
        services.test_orchestrator.shutdown()
