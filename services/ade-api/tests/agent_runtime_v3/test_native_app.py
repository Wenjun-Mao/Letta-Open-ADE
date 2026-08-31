from __future__ import annotations

import ast
import inspect

from fastapi.testclient import TestClient

from ade_api.native_main import create_native_app
from ade_api.platform import dependencies


def test_native_app_exposes_only_liveness_and_v3_routes() -> None:
    app = create_native_app()
    route_paths = {route.path for route in app.routes}

    assert "/health" in route_paths
    assert "/api/v2/health" not in route_paths
    assert "/openapi.json" not in route_paths
    assert all(path == "/health" or path.startswith("/api/v3") for path in route_paths)

    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "runtime": "native"}
        assert client.get("/api/v2/health").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_native_app_keeps_v3_auth_and_never_initializes_v2_services(
    monkeypatch,
) -> None:
    def fail_if_called():
        raise AssertionError("native API must not initialize the v2 service graph")

    monkeypatch.setattr(dependencies, "initialize_dependencies", fail_if_called)
    app = create_native_app()

    with TestClient(app) as client:
        # No configured key must fail closed; it may be 401 (configured keys) or
        # 503 (authentication enabled but no key configured in this test process).
        assert client.get("/api/v3/worker-health").status_code in {401, 503}
        assert client.get("/health").status_code == 200


def test_native_app_source_has_no_letta_or_v2_dependency_wiring() -> None:
    modules = [
        inspect.getmodule(create_native_app),
        __import__(
            "ade_api.features.agent_runtime_v3.application",
            fromlist=["build_agent_runtime_v3_service"],
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

    assert "ade_api.platform.dependencies" not in imported_modules
    assert not any(
        "letta" in module_name.casefold() for module_name in imported_modules
    )
