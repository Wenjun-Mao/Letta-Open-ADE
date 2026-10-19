"""Resolve synthetic candidate config through Compose; never start a container."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from ..provision import prepare_environment
from .test_provision import lease


pytestmark = pytest.mark.skipif(
    shutil.which("docker") is None, reason="Compose CLI unavailable"
)


def test_full_stack_configuration_is_isolated_private_and_within_recorded_envelope(
    tmp_path,
):
    root = tmp_path / "activation"
    lease(root)
    credentials = tmp_path / "existing.env"
    credentials.write_text(
        "DEEPSEEK_API_KEY=synthetic-only\nDGX_EMBEDDING_API_KEY=synthetic-only\n"
    )
    environment = tmp_path / "private/candidate.env"
    prepare_environment(
        activation_root=root,
        environment_path=environment,
        existing_credentials=credentials,
        database_image="sha256:" + "b" * 64,
        source_fingerprint="c" * 64,
    )
    compose = Path(__file__).resolve().parents[1] / "compose.yaml"
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(environment),
            "-f",
            str(compose),
            "--profile",
            "product",
            "--profile",
            "tools",
            "config",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    resolved = json.loads(result.stdout)
    services = resolved["services"]
    assert set(services) == {
        "db",
        "model-router",
        "hindsight",
        "ade-db",
        "ade-migrate",
        "ade-api",
        "ade-worker",
        "fault-proxy",
        "ade-web",
        "runner",
    }
    assert sum(float(service["cpus"]) for service in services.values()) <= 3
    assert (
        sum(int(service["mem_limit"]) for service in services.values()) <= 14 * 1024**3
    )
    assert all(
        not service.get("privileged") and service.get("network_mode") != "host"
        for service in services.values()
    )
    assert all(
        port["host_ip"] == "127.0.0.1"
        for service in services.values()
        for port in service.get("ports", [])
    )
    assert all(not volume.get("external") for volume in resolved["volumes"].values())
    api, worker = services["ade-api"], services["ade-worker"]
    assert (
        api["environment"]["ADE_API_AGENT_RUNTIME_WORKSPACE_KEY"]
        == worker["environment"]["ADE_API_AGENT_RUNTIME_WORKSPACE_KEY"]
    )
    assert api["environment"]["ADE_API_AUTH_ENABLED"] == "true"
    assert "ade_integration_app:" in api["environment"]["ADE_API_DATABASE_URL"]
    assert "@ade-db:" in api["environment"]["ADE_API_DATABASE_URL"]
    assert "@db:" in services["hindsight"]["environment"]["HINDSIGHT_API_DATABASE_URL"]
    assert (
        services["ade-migrate"]["environment"]["ADE_PG_OWNER_ROLE"]
        == "ade_integration_owner"
    )
    assert (
        api["environment"]["ADE_API_MODEL_ROUTER_BASE_URL"]
        == "http://model-router:8010"
    )
    assert (
        worker["environment"]["ADE_API_MODEL_ROUTER_BASE_URL"]
        == "http://fault-proxy:8020/router"
    )
    assert (
        worker["environment"]["ADE_API_HINDSIGHT_BASE_URL"]
        == "http://fault-proxy:8020/hindsight"
    )
    assert (
        services["ade-web"]["environment"]["ADE_API_ADMIN_KEY"]
        == api["environment"]["ADE_API_OPERATOR_KEY"]
    )
    assert (
        services["ade-web"]["environment"]["ADE_API_ADMIN_KEY"]
        != api["environment"]["ADE_API_ADMIN_KEY"]
    )
    api_capture = next(
        volume
        for volume in api["volumes"]
        if volume["target"] == "/product-observations"
    )
    worker_capture = next(
        volume
        for volume in worker["volumes"]
        if volume["target"] == "/product-observations"
    )
    assert api_capture["read_only"] is True and not worker_capture.get(
        "read_only", False
    )
    assert (
        api_capture["source"]
        == worker_capture["source"]
        == str(root / "product-observations")
    )
    assert api["build"]["args"]["ADE_SOURCE_FINGERPRINT"] == "c" * 64
    assert not any(
        "docker.sock" in str(volume)
        for service in services.values()
        for volume in service.get("volumes", [])
    )
