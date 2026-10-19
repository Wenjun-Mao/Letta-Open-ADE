"""Historical native trials cannot be re-enabled in the fresh Hindsight runtime."""

import pytest
from fastapi.testclient import TestClient

import ade_api.platform.app as app_module
import ade_api.platform.auth as auth_module
from ade_api.platform.settings import AdeApiSettings


@pytest.mark.parametrize("legacy_toggle", [False, True])
@pytest.mark.parametrize("runtime_mode", ["development", "release"])
def test_history_trial_routes_remain_retired(monkeypatch, legacy_toggle, runtime_mode):
    settings = AdeApiSettings(
        _env_file=None,
        auth_enabled=True,
        operator_key="operator-test",
        agent_runtime_enabled=True,
        agent_runtime_mode=runtime_mode,
        history_trial_enabled=legacy_toggle,
    )
    monkeypatch.setattr(app_module, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)
    app = app_module.create_app()
    assert not any(
        route.path.startswith("/api/v3/history-trial") for route in app.routes
    )
    with TestClient(app) as client:
        for method, path in (
            ("GET", "/api/v3/history-trial/options"),
            ("POST", "/api/v3/history-trial/sessions"),
            ("POST", "/api/v3/history-trial/definitions/root/versions"),
            ("GET", "/api/v3/history-trial/subjects/subject/memories"),
        ):
            response = client.request(
                method, path, headers={"Authorization": "Bearer operator-test"}
            )
            assert response.status_code == 404
