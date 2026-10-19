"""Same-image workspace fixture has exact ownership, bounded resources and no ports."""

import json
from types import SimpleNamespace

import pytest

from .. import isolation_host as host


def fixture(tmp_path, monkeypatch, *, quota=150_000_000, fail_start=False):
    root = tmp_path / "private/activations/activation"
    root.mkdir(parents=True)
    output = root / "evidence/isolation-01"
    output.mkdir(parents=True)
    environment = tmp_path / "private/config/activation.env"
    environment.parent.mkdir()
    rows = [
        {
            "id": "api-id",
            "name": "/owned-api",
            "state": "running",
            "networks": {"owned_default": {}},
            "image": "sha256:" + "a" * 64,
        }
    ]
    calls = []

    class Docker:
        def owned(self, lease):
            return rows

        def _run(self, command):
            calls.append(command)
            if command[:2] == ["inspect", "--format"]:
                if command[2] == "{{.HostConfig.NanoCpus}}":
                    return str(quota)
                return json.dumps(
                    {"User": "1000:1000", "Env": ["ADE_API_OPERATOR_KEY=secret-test"]}
                )
            if command[0] == "create":
                rows.append(
                    {
                        "id": "secondary-id",
                        "name": "/" + command[command.index("--name") + 1],
                        "state": "created",
                    }
                )
                return "secondary-id"
            if command[0] == "start":
                if fail_start:
                    rows[1]["state"] = "running"
                    raise RuntimeError("controlled_lost_start_ack")
                rows[1]["state"] = "running"
                return "secondary-id"
            raise AssertionError(command)

        def stop(self, identity):
            calls.append(["stop", identity])
            rows[1]["state"] = "exited"

    control = SimpleNamespace(
        root=root,
        output=output,
        environment=environment,
        workspace="primary-workspace",
        fence=lambda: None,
        lease=SimpleNamespace(
            project="owned", activation_id="activation", source_revision="a" * 40
        ),
        docker=Docker(),
        current=lambda name: rows[0],
    )
    monkeypatch.setattr(host, "seed_runtime_assets", lambda *args: {"sha256": "b" * 64})
    return host.IsolationAPI(control), rows, calls


def test_secondary_uses_exact_image_owned_labels_and_outside_root_secret_file(
    tmp_path, monkeypatch
):
    api, rows, calls = fixture(tmp_path, monkeypatch)
    receipt = api.start()
    command = next(row for row in calls if row[0] == "create")
    assert command[-1] == "sha256:" + "a" * 64
    assert "--publish" not in command and "-p" not in command
    assert "io.ade.integration.activation=activation" in command
    assert "com.docker.compose.project=owned" in command
    assert "secret-test" not in json.dumps(calls)
    assert receipt["workspace_key"] == "primary-workspace-isolation-01-isolation"
    private = next(api.controls.environment.parent.glob("*-api.env"))
    assert not private.is_relative_to(api.controls.root)
    assert private.stat().st_mode & 0o777 == 0o600
    assert "ADE_API_OPERATOR_KEY=secret-test" in private.read_text()
    assert (
        "secret-test"
        not in (api.controls.output / "secondary-api-start.json").read_text()
    )
    api.stop()
    assert rows[1]["state"] == "exited"
    assert calls[-1] == ["stop", "secondary-id"]


@pytest.mark.parametrize("quota", [0, 3_000_000_000])
def test_unbounded_or_excess_cpu_refused_before_creating_any_resource(
    tmp_path, monkeypatch, quota
):
    api, rows, calls = fixture(tmp_path, monkeypatch, quota=quota)
    with pytest.raises(ValueError, match="cpu_reserve"):
        api.start()
    assert len(rows) == 1 and not list(
        api.controls.environment.parent.glob("*-api.env")
    )
    assert not any(command[0] == "create" for command in calls)


def test_partial_start_can_stop_only_registered_secondary_identity(
    tmp_path, monkeypatch
):
    api, rows, calls = fixture(tmp_path, monkeypatch, fail_start=True)
    with pytest.raises(RuntimeError):
        api.start()
    api.stop()
    assert calls[-1] == ["stop", "secondary-id"]
    assert rows[0]["state"] == "running"
