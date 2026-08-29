from __future__ import annotations

import ast
import ipaddress
import json
import subprocess
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOTS = (
    "apps/ade-web",
    "services/ade-api",
    "services/model-router",
    "packages/model-catalog-contracts",
    "content",
    "config/model-router",
    "workflows",
    "infra",
    "docs",
)
API_FEATURES = (
    "agent_studio",
    "comment_lab",
    "label_lab",
    "prompt_center",
    "schema_center",
    "tool_center",
    "test_center",
    "model_catalog",
)
WEB_FEATURES = (
    "agent-studio",
    "comment-lab",
    "label-lab",
    "prompt-center",
    "schema-center",
    "tool-center",
    "test-center",
    "model-catalog",
)
FORBIDDEN_LEGACY_IDENTIFIERS = (
    "agent_" + "platform_api",
    "frontend" + "-ade",
    "ade_" + "core",
    "AGENT_" + "PLATFORM_",
    "ADE_" + "FRONTEND_",
    "agent-" + "platform-openapi",
)
ARCHITECTURE_SCAN_SUFFIXES = {
    ".env",
    ".json",
    ".js",
    ".md",
    ".mdx",
    ".mjs",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
ARCHITECTURE_SCAN_EXCLUDED_PARTS = {
    ".git",
    ".next",
    ".playwright-cli",
    ".venv",
    "__pycache__",
    "node_modules",
    "outputs",
}
TEXT_ROOTS = (
    PROJECT_ROOT / "apps",
    PROJECT_ROOT / "services",
    PROJECT_ROOT / "packages",
    PROJECT_ROOT / "content",
    PROJECT_ROOT / "config",
    PROJECT_ROOT / "infra",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "workflows",
    PROJECT_ROOT / "docs",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / ".github",
)
TOP_LEVEL_TEXT_FILES = (
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / "MANUAL.md",
    PROJECT_ROOT / ".gitignore",
)
HISTORICAL_ARCHITECTURE_RECORDS = (
    PROJECT_ROOT
    / "docs"
    / "adr"
    / "0006-comprehension-first-service-and-feature-architecture.md",
)
RETIRED_DOCUMENTATION_REFERENCES = (
    "agent_" + "platform_api",
    "Agent Platform API",
    "frontend" + "-ade",
    "ade_" + "core",
    "AGENT_" + "PLATFORM_",
    "ADE_" + "FRONTEND_",
    "agent-" + "platform-openapi",
    "/api/v1",
    "http://127.0.0.1:8083",
    "http://127.0.0.1:8283",
    "http://127.0.0.1:8284",
    "http://127.0.0.1:8290",
    "tests/checks",
    "letta_server",
    "letta_db",
    "ade_frontend",
    "dev_ui",
)


def _architecture_text_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in project_root.rglob("*"):
        is_dotenv = path.name == ".env" or path.name.startswith(".env.")
        if not path.is_file() or (
            path.suffix.lower() not in ARCHITECTURE_SCAN_SUFFIXES and not is_dotenv
        ):
            continue
        if any(part in ARCHITECTURE_SCAN_EXCLUDED_PARTS for part in path.parts):
            continue
        files.append(path)
    return files


def assert_canonical_roots(
    project_root: Path, canonical_roots: Iterable[str] = TARGET_ROOTS
) -> None:
    missing = [root for root in canonical_roots if not (project_root / root).exists()]
    assert missing == [], f"Missing canonical architecture roots: {missing}"


def assert_no_forbidden_legacy_identifiers(
    project_root: Path,
    *,
    forbidden_identifiers: Iterable[str] = FORBIDDEN_LEGACY_IDENTIFIERS,
    excluded_paths: Iterable[Path] = (),
) -> None:
    forbidden = tuple(forbidden_identifiers)
    excluded = {path.resolve() for path in excluded_paths}
    offenders: list[str] = []

    for path in _architecture_text_files(project_root):
        if path.resolve() in excluded:
            continue
        relative_path = path.relative_to(project_root)
        path_text = str(relative_path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        matches = [
            identifier
            for identifier in forbidden
            if identifier in path_text or identifier in content
        ]
        if matches:
            offenders.append(f"{relative_path}: {', '.join(matches)}")

    assert offenders == [], "Forbidden legacy identifiers:\n" + "\n".join(
        sorted(offenders)
    )


def _current_documentation_files(project_root: Path) -> list[Path]:
    files: set[Path] = set()
    documentation_root = project_root / "docs"
    if documentation_root.exists():
        files.update(
            path
            for path in documentation_root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".md", ".mdx"}
        )

    workflows_root = project_root / "workflows"
    if workflows_root.exists():
        files.update(workflows_root.rglob("README.md"))

    files.update(
        path
        for path in (
            project_root / "README.md",
            project_root / "MANUAL.md",
            project_root / "tests" / "README.md",
            project_root / ".github" / "copilot-instructions.md",
        )
        if path.is_file()
    )
    return sorted(files)


def assert_current_documentation_uses_canonical_terms(
    project_root: Path,
    *,
    retired_references: Iterable[str] = RETIRED_DOCUMENTATION_REFERENCES,
    historical_records: Iterable[Path] = (),
) -> None:
    retired = tuple(retired_references)
    excluded = {path.resolve() for path in historical_records}
    offenders: list[str] = []

    for path in _current_documentation_files(project_root):
        if path.resolve() in excluded:
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        matches = [reference for reference in retired if reference in content]
        if matches:
            offenders.append(f"{path.relative_to(project_root)}: {', '.join(matches)}")

    assert offenders == [], "Retired documentation references:\n" + "\n".join(
        sorted(offenders)
    )


def assert_feature_readmes(
    project_root: Path,
    *,
    web_features: Iterable[str] = WEB_FEATURES,
    api_features: Iterable[str] = API_FEATURES,
) -> None:
    missing = [
        f"{feature_root}/{feature}/README.md"
        for feature_root, features in (
            ("apps/ade-web/src/features", web_features),
            ("services/ade-api/src/ade_api/features", api_features),
        )
        for feature in features
        if not (project_root / feature_root / feature / "README.md").is_file()
    ]
    assert missing == [], "Missing feature READMEs:\n" + "\n".join(missing)


def _module_name(source_root: Path, path: Path, package_name: str) -> str:
    relative = path.relative_to(source_root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join((package_name, *parts))


def _resolve_import_from_module(
    *, module_name: str, path: Path, node: ast.ImportFrom
) -> str | None:
    if node.level == 0:
        return node.module

    module_parts = module_name.split(".")
    package_parts = module_parts if path.name == "__init__.py" else module_parts[:-1]
    ancestor_count = node.level - 1
    if ancestor_count > len(package_parts):
        return None
    base_parts = package_parts[: len(package_parts) - ancestor_count]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def _imported_modules(
    *, module_name: str, path: Path, node: ast.stmt, package_name: str
) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []

    resolved = _resolve_import_from_module(
        module_name=module_name,
        path=path,
        node=node,
    )
    if not resolved:
        return []

    modules = [resolved]
    feature_base = f"{package_name}.features"
    if resolved == feature_base:
        modules.extend(f"{resolved}.{alias.name}" for alias in node.names)
    return modules


def _module_owner(module_name: str, package_name: str) -> tuple[str, str | None]:
    feature_prefix = f"{package_name}.features."
    if module_name.startswith(feature_prefix):
        feature_name = module_name[len(feature_prefix) :].split(".", 1)[0]
        return "feature", feature_name
    if module_name == f"{package_name}.platform" or module_name.startswith(
        f"{package_name}.platform."
    ):
        return "platform", None
    if module_name == f"{package_name}.integrations" or module_name.startswith(
        f"{package_name}.integrations."
    ):
        return "integration", None
    return "other", None


def _is_public_feature_import(module_name: str, package_name: str) -> bool:
    feature_prefix = f"{package_name}.features."
    if not module_name.startswith(feature_prefix):
        return False
    return "." not in module_name[len(feature_prefix) :]


def _is_platform_wiring_import(
    *, path: Path, module_name: str, package_name: str
) -> bool:
    if path.name == "dependencies.py":
        return True
    return path.name == "app.py" and _is_public_feature_import(
        module_name, package_name
    )


def assert_python_import_boundaries(
    source_root: Path, *, package_name: str = "ade_api"
) -> None:
    violations: list[str] = []
    for path in source_root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        module_name = _module_name(source_root, path, package_name)
        source_kind, source_feature = _module_owner(module_name, package_name)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for imported_module in _imported_modules(
                module_name=module_name,
                path=path,
                node=node,
                package_name=package_name,
            ):
                target_kind, target_feature = _module_owner(
                    imported_module, package_name
                )
                if (
                    source_kind == "feature"
                    and target_kind == "feature"
                    and source_feature != target_feature
                    and not _is_public_feature_import(imported_module, package_name)
                ):
                    violations.append(
                        f"{path.relative_to(source_root)} imports sibling feature "
                        f"{imported_module}"
                    )
                elif (
                    source_kind == "platform"
                    and target_kind == "feature"
                    and not _is_platform_wiring_import(
                        path=path,
                        module_name=imported_module,
                        package_name=package_name,
                    )
                ):
                    violations.append(
                        f"{path.relative_to(source_root)} imports feature {imported_module}"
                    )
                elif source_kind == "integration" and target_kind == "feature":
                    violations.append(
                        f"{path.relative_to(source_root)} imports feature {imported_module}"
                    )

    assert violations == [], "Python import-boundary violations:\n" + "\n".join(
        sorted(violations)
    )


def test_target_architecture_helpers_detect_missing_canonical_root(
    tmp_path: Path,
) -> None:
    (tmp_path / "apps" / "ade-web").mkdir(parents=True)

    with pytest.raises(AssertionError, match="services/ade-api"):
        assert_canonical_roots(
            tmp_path,
            canonical_roots=("apps/ade-web", "services/ade-api"),
        )


def test_target_architecture_helpers_detect_legacy_identifier_and_honor_exclusion(
    tmp_path: Path,
) -> None:
    legacy_file = tmp_path / "docs" / "migration.md"
    legacy_file.parent.mkdir()
    legacy_file.write_text("Replace LEGACY_NAME during the cutover.", encoding="utf-8")

    with pytest.raises(AssertionError, match="LEGACY_NAME"):
        assert_no_forbidden_legacy_identifiers(
            tmp_path,
            forbidden_identifiers=("LEGACY_NAME",),
        )

    assert_no_forbidden_legacy_identifiers(
        tmp_path,
        forbidden_identifiers=("LEGACY_NAME",),
        excluded_paths=(legacy_file,),
    )


def test_documentation_helper_allows_only_explicit_historical_records(
    tmp_path: Path,
) -> None:
    current = tmp_path / "README.md"
    historical = tmp_path / "docs" / "adr" / "0006-history.md"
    historical.parent.mkdir(parents=True)
    current.write_text("LEGACY_NAME", encoding="utf-8")
    historical.write_text("LEGACY_NAME", encoding="utf-8")

    with pytest.raises(AssertionError, match="README.md"):
        assert_current_documentation_uses_canonical_terms(
            tmp_path,
            retired_references=("LEGACY_NAME",),
            historical_records=(historical,),
        )

    current.write_text("Current architecture", encoding="utf-8")
    assert_current_documentation_uses_canonical_terms(
        tmp_path,
        retired_references=("LEGACY_NAME",),
        historical_records=(historical,),
    )


def test_target_architecture_helpers_require_feature_readmes(tmp_path: Path) -> None:
    web_feature_root = tmp_path / "apps" / "ade-web" / "src" / "features"
    api_feature_root = (
        tmp_path / "services" / "ade-api" / "src" / "ade_api" / "features"
    )
    (web_feature_root / "agent-studio").mkdir(parents=True)
    (api_feature_root / "agent_studio").mkdir(parents=True)

    with pytest.raises(AssertionError, match="README.md"):
        assert_feature_readmes(
            tmp_path,
            web_features=("agent-studio",),
            api_features=("agent_studio",),
        )

    (web_feature_root / "agent-studio" / "README.md").write_text(
        "# Agent Studio\n", encoding="utf-8"
    )
    (api_feature_root / "agent_studio" / "README.md").write_text(
        "# Agent Studio\n", encoding="utf-8"
    )

    assert_feature_readmes(
        tmp_path,
        web_features=("agent-studio",),
        api_features=("agent_studio",),
    )


def test_target_architecture_helpers_enforce_python_import_boundaries(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "ade_api"
    files = {
        "features/agent_studio/service.py": (
            "from ade_api.features.comment_lab.service import CommentingService\n"
            "from ade_api.features.model_catalog import runtime_options\n"
            "from ade_api.platform.settings import Settings\n"
            "from ade_api.integrations.letta.client import LettaClient\n"
        ),
        "integrations/letta/client.py": "from ade_api.features.agent_studio import service\n",
        "platform/app.py": "from ade_api.features.label_lab import router\n",
        "platform/dependencies.py": "from ade_api.features.label_lab import api\n",
        "platform/settings.py": "from ade_api.features.label_lab import api\n",
        "features/comment_lab/service.py": "from .contracts import CommentRequest\n",
    }
    for relative_path, content in files.items():
        path = source_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    with pytest.raises(AssertionError) as exc_info:
        assert_python_import_boundaries(source_root)

    message = str(exc_info.value)
    assert "sibling feature ade_api.features.comment_lab" in message
    assert "integrations/letta/client.py imports feature" in message
    assert "platform/settings.py imports feature" in message


def test_target_architecture_contract_is_enforced() -> None:
    assert_canonical_roots(PROJECT_ROOT)
    assert_no_forbidden_legacy_identifiers(
        PROJECT_ROOT,
        excluded_paths=(*HISTORICAL_ARCHITECTURE_RECORDS, Path(__file__)),
    )
    assert_current_documentation_uses_canonical_terms(
        PROJECT_ROOT,
        historical_records=HISTORICAL_ARCHITECTURE_RECORDS,
    )
    assert_feature_readmes(PROJECT_ROOT)
    assert_python_import_boundaries(
        PROJECT_ROOT / "services" / "ade-api" / "src" / "ade_api"
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
            if path.is_file()
            and path.suffix.lower() in suffixes
            and not any(part in ARCHITECTURE_SCAN_EXCLUDED_PARTS for part in path.parts)
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
        "services/ade-api/src/ade_api/helpers.py",
        "services/ade-api/src/ade_api/runtime.py",
        "services/ade-api/src/ade_api/model_options.py",
        "services/ade-api/src/ade_api/registries/prompt_persona.py",
        "services/ade-api/src/ade_api/services/labeling_provider_client.py",
    )
    assert [path for path in removed if (PROJECT_ROOT / path).exists()] == []


def test_frontend_backend_configuration_stays_server_only() -> None:
    frontend_root = PROJECT_ROOT / "apps/ade-web"
    offenders: list[str] = []
    forbidden = "NEXT_PUBLIC_" + "ADE_API_API_BASE_URL"
    for path in frontend_root.rglob("*"):
        if not path.is_file() or "node_modules" in path.parts or ".next" in path.parts:
            continue
        if path.suffix not in {".ts", ".tsx", ".js", ".mjs", ".json"}:
            continue
        if forbidden in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_removed_ade_api_model_source_config_stays_removed() -> None:
    removed_env_key = "ADE_API_" + "MODEL_SOURCES"
    offenders: list[str] = []
    for path in _text_files():
        if path.name == "test_codebase_guardrails.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if removed_env_key in text:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_ade_api_has_no_direct_provider_catalog_fallback() -> None:
    forbidden = (
        "direct-provider fallback",
        "legacy direct-provider",
        "ModelCatalogService",
        "model_catalog_service",
    )
    offenders: list[str] = []
    for path in (PROJECT_ROOT / "services" / "ade-api" / "src" / "ade_api").rglob(
        "*.py"
    ):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text for marker in forbidden):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_letta_does_not_inherit_direct_lmstudio_provider_config() -> None:
    compose_text = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    letta_service = compose_text.split("\n  letta:", 1)[1].split("\n  ade-api:", 1)[0]
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert 'LMSTUDIO_BASE_URL: ""' in letta_service
    assert "LMSTUDIO_BASE_URL=" not in env_example


def test_compose_project_name_is_canonical() -> None:
    compose_text = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    env_example_lines = (
        (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    )

    assert compose_text.startswith("name: letta-open-ade\n")
    assert "COMPOSE_PROJECT_NAME=letta-open-ade" in env_example_lines


def test_python_service_images_default_to_the_managed_virtualenv() -> None:
    dockerfiles = (
        PROJECT_ROOT / "services" / "ade-api" / "Dockerfile",
        PROJECT_ROOT / "services" / "model-router" / "Dockerfile",
    )

    offenders = [
        str(path.relative_to(PROJECT_ROOT))
        for path in dockerfiles
        if 'PATH="/opt/venv/bin:${PATH}"' not in path.read_text(encoding="utf-8")
    ]

    assert offenders == [], (
        "Python service images must make /opt/venv/bin the default PATH so "
        f"documented exec commands use installed dependencies: {offenders}"
    )


def test_images_installing_workflows_copy_shared_workspace_packages() -> None:
    dockerfiles = (
        PROJECT_ROOT / "services" / "ade-api" / "Dockerfile",
        PROJECT_ROOT / "services" / "model-router" / "Dockerfile",
    )
    required_copy = (
        "COPY packages/agent-runtime-eval-contracts ./packages/agent-runtime-eval-contracts",
        "COPY packages/model-catalog-contracts ./packages/model-catalog-contracts",
    )

    offenders = []
    for path in dockerfiles:
        text = path.read_text(encoding="utf-8")
        if "--package ade-workflows" in text and any(
            statement not in text for statement in required_copy
        ):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == [], (
        "Images installing ade-workflows must copy its workspace dependencies "
        f"before uv sync: {offenders}"
    )


def test_letta_runtime_security_and_image_pins_stay_explicit() -> None:
    compose_text = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8")
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    nltk_seed_script = (PROJECT_ROOT / "scripts" / "seed_nltk_data.sh").read_text(
        encoding="utf-8"
    )

    assert "LETTA_ENCRYPTION_KEY=" in env_example
    assert "letta/letta:0.16.8" in compose_text
    assert "letta/letta:0.16.8" in env_example
    assert "letta/letta:0.16.8" in nltk_seed_script


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
        "apps/ade-web/.next/",
        "apps/ade-web/node_modules/",
        "workflows/evals/comment_persona_eval/outputs/",
        "workflows/evals/chat_memory_eval/outputs/",
        "workflows/evals/provider_model_probe/outputs/",
        "temps/",
        "data/agent_lifecycle/registry.json",
        "data/personas/personas.sqlite3",
        "data/runtime/",
    )
    tracked = [
        line.strip().replace("\\", "/")
        for line in completed.stdout.splitlines()
        if line.strip()
    ]
    offenders = [
        path
        for path in tracked
        if (PROJECT_ROOT / path).exists()
        and any(fragment in path for fragment in forbidden_fragments)
    ]

    assert offenders == []


def test_workflow_specific_config_stays_out_of_root_config() -> None:
    config_dir = PROJECT_ROOT / "config"
    offenders = sorted(path.name for path in config_dir.iterdir() if path.is_file())

    assert offenders == []


def test_tracked_model_router_sources_do_not_embed_machine_specific_ip_addresses() -> (
    None
):
    sources = json.loads(
        (PROJECT_ROOT / "config" / "model-router" / "sources.json").read_text(
            encoding="utf-8"
        )
    )
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
        PROJECT_ROOT / "workflows" / "evals" / "comment_persona_eval",
        PROJECT_ROOT / "workflows" / "evals" / "chat_memory_eval",
        PROJECT_ROOT / "workflows" / "evals" / "provider_model_probe",
    ]
    offenders = [
        str(path.relative_to(PROJECT_ROOT))
        for path in workflows
        if not (path / "README.md").is_file() or not (path / "run.py").is_file()
    ]

    assert offenders == []


def test_docs_do_not_restore_retired_letta_notebooks_or_dev_ui_language() -> None:
    retired_paths = (
        "docs/01_letta_agents_and_memory.py",
        "docs/02_letta_system_instructions_and_tools.py",
        "docs/03_letta_inner_workings_and_tool_calls.py",
        "docs/04_letta_full_prompt_synthesis.py",
        "docs/MemGPT paper.pdf",
        "notebooks/01-doubao-api-smoke.ipynb",
        "notebooks/01_doubao_api_smoke.py",
        "notebooks/02_letta_e2e.py",
    )
    assert [path for path in retired_paths if (PROJECT_ROOT / path).exists()] == []
    assert (PROJECT_ROOT / "docs" / "references.md").is_file()

    offenders: list[str] = []
    for path in (PROJECT_ROOT / "docs").rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".mdx"}:
            continue
        if "Dev UI" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert offenders == []


def test_ci_checks_formatting_without_rewriting_the_stable_base() -> None:
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "verify.yml").read_text(
        encoding="utf-8"
    )

    assert "fetch-depth: 0" in workflow
    assert "scripts/check_python_format.py" in workflow
    assert (
        "ruff format --check ade_api model_router model_catalog_contracts evals scripts tests"
        not in workflow
    )
