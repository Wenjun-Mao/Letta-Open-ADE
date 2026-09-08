"""Small, durable guardrails for the ADE steady-state architecture.

These checks protect the contracts that make the repository easier to reason
about. They intentionally avoid asserting an exhaustive file inventory: a
feature may grow internally without changing the service topology, ownership,
or public runtime boundary.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_SOURCE_ROOT = PROJECT_ROOT / "services" / "ade-api" / "src" / "ade_api"
COMPOSE_SERVICES = {
    "postgres",
    "model-router",
    "ade-api",
    "ade-runtime-migrate",
    "ade-runtime-worker",
    "ade-web",
}
CURRENT_API_FEATURES = {
    "agent_runtime",
    "comment_lab",
    "label_lab",
    "model_catalog",
    "prompt_center",
    "schema_center",
    "test_center",
}
CURRENT_WEB_FEATURES = {
    "agent-studio",
    "comment-lab",
    "label-lab",
    "model-catalog",
    "prompt-center",
    "schema-center",
    "test-center",
}
LEGACY_FEATURE_DIRECTORIES = (
    "services/ade-api/src/ade_api/features/agent_studio",
    "services/ade-api/src/ade_api/features/tool_center",
    "services/ade-api/src/ade_api/integrations/letta",
    "apps/ade-web/src/features/tool-center",
)
LEGACY_ENV_PREFIXES = (
    "LETTA_",
    "REDIS_",
    "ADE_NATIVE_",
    "AGENT_RUNTIME_V3_",
)
RETIRED_WORKFLOW_DIRECTORIES = (
    "workflows/evals/agent_runtime_parity",
    "workflows/evals/agent_runtime_study",
)


def _compose_config() -> dict[str, object]:
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            ".env.example",
            "config",
            "--format",
            "json",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _python_files(root: Path) -> Iterable[Path]:
    return (
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts and "tests" not in path.parts
    )


def _module_name(source_root: Path, path: Path) -> str:
    relative = path.relative_to(source_root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(("ade_api", *parts))


def _resolve_from_import(
    module_name: str, path: Path, node: ast.ImportFrom
) -> str | None:
    if node.level == 0:
        return node.module

    module_parts = module_name.split(".")
    package_parts = module_parts if path.name == "__init__.py" else module_parts[:-1]
    if node.level - 1 > len(package_parts):
        return None
    resolved = package_parts[: len(package_parts) - (node.level - 1)]
    if node.module:
        resolved.extend(node.module.split("."))
    return ".".join(resolved)


def _imported_modules(module_name: str, path: Path, node: ast.stmt) -> Iterable[str]:
    if isinstance(node, ast.Import):
        yield from (alias.name for alias in node.names)
        return
    if not isinstance(node, ast.ImportFrom):
        return

    resolved = _resolve_from_import(module_name, path, node)
    if not resolved:
        return
    yield resolved
    if resolved == "ade_api.features":
        yield from (f"{resolved}.{alias.name}" for alias in node.names)


def _feature_owner(module_name: str) -> str | None:
    prefix = "ade_api.features."
    if not module_name.startswith(prefix):
        return None
    return module_name[len(prefix) :].split(".", 1)[0]


def _imports_legacy_runtime_package(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules = (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported_modules = (node.module,)
        else:
            continue
        if any(
            module.split(".", 1)[0] in {"letta", "letta_client", "redis"}
            for module in imported_modules
        ):
            return True
    return False


def test_compose_has_one_steady_state_stack() -> None:
    services = _compose_config()["services"]
    assert set(services) == COMPOSE_SERVICES

    api = services["ade-api"]
    worker = services["ade-runtime-worker"]
    migration = services["ade-runtime-migrate"]
    web = services["ade-web"]

    assert set(api["depends_on"]) == {
        "model-router",
        "ade-runtime-migrate",
        "ade-runtime-worker",
    }
    assert set(worker["depends_on"]) == {"model-router", "ade-runtime-migrate"}
    assert set(migration["depends_on"]) == {"postgres"}
    assert set(web["depends_on"]) == {"ade-api"}
    assert api["build"]["args"] == worker["build"]["args"] == migration["build"]["args"]


def test_web_has_one_server_side_api_base_url() -> None:
    services = _compose_config()["services"]
    web_environment = services["ade-web"]["environment"]
    assert web_environment["ADE_API_BASE_URL"] == "http://ade-api:8000"
    assert [key for key in web_environment if "API_BASE_URL" in key] == [
        "ADE_API_BASE_URL"
    ]

    proxy = (
        PROJECT_ROOT
        / "apps"
        / "ade-web"
        / "src"
        / "shared"
        / "api"
        / "server"
        / "ade-api-proxy.ts"
    ).read_text(encoding="utf-8")
    assert 'const API_BASE_URL_ENV = "ADE_API_BASE_URL"' in proxy
    assert "ADE_NATIVE_API_BASE_URL" not in proxy
    assert "NEXT_PUBLIC_ADE_API_BASE_URL" not in proxy


def test_legacy_runtime_components_are_absent() -> None:
    missing = [
        relative_path
        for relative_path in LEGACY_FEATURE_DIRECTORIES
        if (PROJECT_ROOT / relative_path).exists()
    ]
    assert missing == [], f"Removed legacy components remain: {missing}"

    compose = (PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8").casefold()
    assert "letta:" not in compose
    assert "redis:" not in compose
    assert "ade-native-api:" not in compose
    assert "native_main" not in compose


def test_production_sources_have_no_letta_redis_or_v3_internal_wiring() -> None:
    offenders: list[str] = []
    v3_identifier = re.compile(r"\\bagent_runtime_v3\\b")
    for path in _python_files(API_SOURCE_ROOT):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if _imports_legacy_runtime_package(path) or v3_identifier.search(text):
            offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == [], "Legacy runtime wiring remains:\n" + "\n".join(
        sorted(offenders)
    )


def test_deployment_configuration_has_no_legacy_runtime_environment() -> None:
    files = (
        PROJECT_ROOT / "compose.yaml",
        PROJECT_ROOT / ".env.example",
        PROJECT_ROOT / "Makefile",
        PROJECT_ROOT / "services" / "ade-api" / "Dockerfile",
        PROJECT_ROOT / "apps" / "ade-web" / "Dockerfile",
    )
    offenders: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        matches = [prefix for prefix in LEGACY_ENV_PREFIXES if prefix in text]
        if matches:
            offenders.append(f"{path.relative_to(PROJECT_ROOT)}: {', '.join(matches)}")
    assert offenders == [], "Legacy environment names remain:\n" + "\n".join(offenders)


def test_retired_transition_workflows_and_entrypoints_are_absent() -> None:
    remaining = [
        relative_path
        for relative_path in RETIRED_WORKFLOW_DIRECTORIES
        if (PROJECT_ROOT / relative_path).exists()
    ]
    assert remaining == [], f"Retired workflows remain: {remaining}"

    makefile = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8").casefold()
    assert "agent-studio-rollback" not in makefile
    assert "agent-studio-cutover" not in makefile
    assert "agent-runtime-parity" not in makefile


def test_runtime_exposes_product_sessions_not_generic_resource_crud() -> None:
    runtime_api = (API_SOURCE_ROOT / "features" / "agent_runtime" / "api.py").read_text(
        encoding="utf-8"
    )
    generic_paths = (
        '"/definitions"',
        '"/subjects"',
        '"/conversations"',
        '"/memories"',
    )
    assert not any(path in runtime_api for path in generic_paths)
    assert '"/evaluation-sessions"' in runtime_api
    assert '"/conversations/{conversation_id}/turns"' in runtime_api


def test_only_current_features_are_wired_into_the_ade_api() -> None:
    app_source = (API_SOURCE_ROOT / "platform" / "app.py").read_text(encoding="utf-8")
    for feature in CURRENT_API_FEATURES:
        assert (API_SOURCE_ROOT / "features" / feature).is_dir()
    for feature in CURRENT_WEB_FEATURES:
        assert (
            PROJECT_ROOT / "apps" / "ade-web" / "src" / "features" / feature
        ).is_dir()

    assert "tool_center" not in app_source
    assert "agent_studio" not in app_source
    assert "letta" not in app_source.casefold()
    assert "agent_runtime_router" in app_source


def test_features_do_not_reach_into_sibling_implementations() -> None:
    violations: list[str] = []
    for path in _python_files(API_SOURCE_ROOT):
        module_name = _module_name(API_SOURCE_ROOT, path)
        source_feature = _feature_owner(module_name)
        if source_feature is None:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for imported_module in _imported_modules(module_name, path, node):
                target_feature = _feature_owner(imported_module)
                if target_feature and target_feature != source_feature:
                    suffix = imported_module[len("ade_api.features.") :]
                    if "." in suffix:
                        violations.append(
                            f"{path.relative_to(API_SOURCE_ROOT)} imports {imported_module}"
                        )
    assert violations == [], (
        "Feature implementation boundary violations:\n" + "\n".join(sorted(violations))
    )


def test_test_center_stays_admin_gated_and_workflow_scope_is_current() -> None:
    api = (API_SOURCE_ROOT / "features" / "test_center" / "api.py").read_text(
        encoding="utf-8"
    )
    descriptors = (
        API_SOURCE_ROOT / "features" / "test_center" / "run_descriptors.py"
    ).read_text(encoding="utf-8")
    assert "from ade_api.platform.auth import require_admin" in api
    assert "APIRouter(dependencies=[Depends(require_admin)])" in api
    assert "agent_runtime_parity" not in descriptors
    assert "rollback" not in descriptors.casefold()
    assert "cutover" not in descriptors.casefold()


def test_model_router_source_catalog_is_portable_for_containers() -> None:
    sources = json.loads(
        (PROJECT_ROOT / "config" / "model-router" / "sources.json").read_text(
            encoding="utf-8"
        )
    )
    hostnames = [
        urlparse(str(source.get("base_url", ""))).hostname or "" for source in sources
    ]
    assert not [
        hostname for hostname in hostnames if hostname.casefold().endswith(".local")
    ]
    assert not [
        hostname
        for hostname in hostnames
        if hostname.replace(".", "").isdigit() and not hostname.startswith("127.")
    ]
