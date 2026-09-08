from __future__ import annotations

import ast
import inspect

from fastapi.testclient import TestClient

from ade_api.platform.app import create_app


def test_unified_app_exposes_product_and_agent_runtime_routes() -> None:
    app = create_app()
    route_paths = {route.path for route in app.routes}

    assert "/api/v2/health" in route_paths
    assert "/api/v2/comment-lab/generations" in route_paths
    assert "/api/v3/agent-studio/options" in route_paths
    assert not any(path.startswith("/api/v2/agent-studio") for path in route_paths)
    assert not any(path.startswith("/api/v2/tool-center") for path in route_paths)

    with TestClient(app) as client:
        assert client.get("/api/v2/health").status_code == 200
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/api/v2/agent-studio/agents").status_code == 404
        assert client.get("/api/v2/tool-center/runtime-tools").status_code == 404


def test_unified_app_keeps_agent_runtime_auth() -> None:
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/v3/worker-health").status_code in {401, 503}
        assert client.get("/api/v2/health").status_code == 200


def test_unified_app_source_has_no_letta_dependency_wiring() -> None:
    modules = [
        inspect.getmodule(create_app),
        __import__(
            "ade_api.features.agent_runtime.application",
            fromlist=["build_agent_runtime_service"],
        ),
    ]
    imported_modules: set[str] = set()
    for inspected in modules:
        module = ast.parse(inspect.getsource(inspected))
        imported_modules.update(
            alias.name
            for node in ast.walk(module)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        imported_modules.update(
            node.module or ""
            for node in ast.walk(module)
            if isinstance(node, ast.ImportFrom)
        )

    assert not any(
        "letta" in module_name.casefold() for module_name in imported_modules
    )
