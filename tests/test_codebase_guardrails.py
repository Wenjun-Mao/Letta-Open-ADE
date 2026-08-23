from __future__ import annotations

import ipaddress
import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEXT_ROOTS = (
    PROJECT_ROOT / "agent_platform_api",
    PROJECT_ROOT / "ade_core",
    PROJECT_ROOT / "model_router",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "evals",
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / ".github",
)
TOP_LEVEL_TEXT_FILES = (
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "MANUAL.md",
    PROJECT_ROOT / ".gitignore",
)


def _text_files() -> list[Path]:
    suffixes = {".py", ".md", ".yml", ".yaml", ".toml", ".json"}
    files: list[Path] = []
    for root in TEXT_ROOTS:
        if not root.exists():
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in suffixes and "__pycache__" not in path.parts
        )
    files.extend(path for path in TOP_LEVEL_TEXT_FILES if path.is_file())
    return files


def test_no_utils_imports_reintroduced() -> None:
    offenders: list[str] = []
    for path in _text_files():
        if path.name == "test_codebase_guardrails.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "from utils" in text or "import utils" in text:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_removed_catch_all_facades_stay_removed() -> None:
    removed = (
        "agent_platform_api/helpers.py",
        "agent_platform_api/runtime.py",
        "agent_platform_api/model_options.py",
        "agent_platform_api/registries/prompt_persona.py",
        "agent_platform_api/services/labeling_provider_client.py",
    )
    assert [path for path in removed if (PROJECT_ROOT / path).exists()] == []


def test_frontend_backend_configuration_stays_server_only() -> None:
    frontend_root = PROJECT_ROOT / "frontend-ade"
    offenders: list[str] = []
    forbidden = "NEXT_PUBLIC_" + "AGENT_PLATFORM_API_BASE_URL"
    for path in frontend_root.rglob("*"):
        if not path.is_file() or "node_modules" in path.parts or ".next" in path.parts:
            continue
        if path.suffix not in {".ts", ".tsx", ".js", ".mjs", ".json"}:
            continue
        if forbidden in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_removed_agent_platform_model_source_config_stays_removed() -> None:
    removed_env_key = "AGENT_PLATFORM_" + "MODEL_SOURCES"
    offenders: list[str] = []
    for path in _text_files():
        if path.name == "test_codebase_guardrails.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if removed_env_key in text:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_agent_platform_has_no_direct_provider_catalog_fallback() -> None:
    forbidden = (
        "direct-provider fallback",
        "legacy direct-provider",
        "ModelCatalogService",
        "model_catalog_service",
    )
    offenders: list[str] = []
    for path in (PROJECT_ROOT / "agent_platform_api").rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text for marker in forbidden):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_letta_does_not_inherit_direct_lmstudio_provider_config() -> None:
    compose_text = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    letta_service = compose_text.split("\n  letta_server:", 1)[1].split("\n  agent_platform_api:", 1)[0]
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert 'LMSTUDIO_BASE_URL: ""' in letta_service
    assert "LMSTUDIO_BASE_URL=" not in env_example


def test_compose_project_name_is_canonical() -> None:
    compose_text = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    env_example_lines = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()

    assert compose_text.startswith("name: letta-open-ade\n")
    assert "COMPOSE_PROJECT_NAME=letta-open-ade" in env_example_lines


def test_no_tracked_generated_or_stale_artifacts() -> None:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    forbidden_fragments = (
        "__pycache__/",
        ".pyc",
        "frontend-ade/.next/",
        "frontend-ade/node_modules/",
        "evals/comment_persona_eval/outputs/",
        "evals/chat_memory_eval/outputs/",
        "evals/provider_model_probe/outputs/",
        "temps/",
        "notebooks/zz",
        "data/agent_lifecycle/registry.json",
        "data/personas/personas.sqlite3",
        "data/runtime/",
    )
    tracked = [line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()]
    offenders = [
        path
        for path in tracked
        if (PROJECT_ROOT / path).exists() and any(fragment in path for fragment in forbidden_fragments)
    ]

    assert offenders == []


def test_workflow_specific_config_stays_out_of_root_config() -> None:
    allowed = {
        "model_router_sources.json",
        "model_router_sources.local.json",
        "model_router_model_profiles.json",
    }
    config_dir = PROJECT_ROOT / "config"
    offenders = sorted(
        path.name
        for path in config_dir.iterdir()
        if path.is_file() and path.name not in allowed
    )

    assert offenders == []


def test_tracked_model_router_sources_do_not_embed_machine_specific_ip_addresses() -> None:
    sources = json.loads((PROJECT_ROOT / "config" / "model_router_sources.json").read_text(encoding="utf-8"))
    offenders: list[str] = []
    for source in sources:
        hostname = urlparse(str(source.get("base_url", ""))).hostname or ""
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            continue
        if not address.is_loopback:
            offenders.append(f"{source.get('id')}: {hostname}")

    assert offenders == []


def test_docs_do_not_reference_removed_comment_eval_paths() -> None:
    forbidden = (
        "scripts/comment_persona_eval.py",
        "config/comment_persona_eval.toml",
        "temps/comment_persona_eval",
        "scripts/probe_provider_models.py",
    )
    offenders: list[str] = []
    for path in _text_files():
        if path.name == "test_codebase_guardrails.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text for marker in forbidden):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_eval_workflows_are_self_documenting() -> None:
    workflows = [
        PROJECT_ROOT / "evals" / "comment_persona_eval",
        PROJECT_ROOT / "evals" / "chat_memory_eval",
        PROJECT_ROOT / "evals" / "provider_model_probe",
    ]
    offenders = [
        str(path.relative_to(PROJECT_ROOT))
        for path in workflows
        if not (path / "README.md").is_file() or not (path / "run.py").is_file()
    ]

    assert offenders == []
