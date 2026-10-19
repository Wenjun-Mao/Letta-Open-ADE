"""Build command/source/resource guards without building or contacting a provider."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from .. import build_images
from ..provision import prepare_environment
from .test_provision import lease


def setup(tmp_path, monkeypatch):
    root = tmp_path / "activation"
    lease(root)
    credentials = tmp_path / "credentials.env"
    credentials.write_text("DEEPSEEK_API_KEY=synthetic-private\n")
    environment = tmp_path / "private/candidate.env"
    prepare_environment(
        activation_root=root,
        environment_path=environment,
        existing_credentials=credentials,
        database_image="sha256:" + "b" * 64,
        source_fingerprint="c" * 64,
    )
    project = tmp_path / ("a" * 40)
    project.mkdir()
    monkeypatch.setattr(build_images.time, "time", lambda: 100)
    monkeypatch.setattr(
        build_images,
        "resources",
        lambda _: {"available_ram": 20 * 1024**3, "free_disk": 50 * 1024**3},
    )
    monkeypatch.setattr(
        build_images,
        "DockerOperations",
        lambda: SimpleNamespace(snapshot=lambda ids=None: [], owned=lambda lease: []),
    )
    return root, environment, project


def test_builds_are_serial_bounded_and_source_bound_without_global_builder_change(
    tmp_path, monkeypatch
):
    root, environment, project = setup(tmp_path, monkeypatch)
    monkeypatch.setenv("DOCKER_BUILDKIT", "unchanged")
    calls = []

    def run(command, **kw):
        calls.append((command, kw))
        assert kw["env"]["DOCKER_BUILDKIT"] == "0"
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(build_images.subprocess, "run", run)
    monkeypatch.setattr(
        build_images.subprocess,
        "check_output",
        lambda command, **kw: (
            "sha256:" + hashlib.sha256(command[3].encode()).hexdigest()
        ),
    )
    result = build_images.build_images(root, environment, project_root=project)
    assert [row["role"] for row in result] == [
        "budget",
        "runner",
        "router",
        "api",
        "web",
    ]
    assert len(calls) == 5
    for command, kw in calls:
        assert command[0] == "timeout" and "1200s" in command
        assert command[command.index("--cpu-quota") + 1] == "300000"
        assert command[command.index("--cpuset-cpus") + 1] == "0-2"
        assert command[command.index("--memory") + 1] == "3g"
        assert "ADE_SOURCE_FINGERPRINT=" + "c" * 64 in command
        assert "synthetic-private" not in str(command)
    assert "--no-cache" in calls[0][0]
    assert build_images.os.environ["DOCKER_BUILDKIT"] == "unchanged"
    assert (
        json.loads((root / "images.json").read_bytes())["source_fingerprint"]
        == "c" * 64
    )


def test_failed_budget_build_prevents_all_product_image_builds(tmp_path, monkeypatch):
    root, environment, project = setup(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(
        build_images.subprocess,
        "run",
        lambda command, **kw: calls.append(command) or SimpleNamespace(returncode=1),
    )
    with pytest.raises(RuntimeError, match="budget_build_failed"):
        build_images.build_images(root, environment, project_root=project)
    assert len(calls) == 1
    assert not (root / "images.json").exists()
    assert (
        json.loads((root / "builds/budget.result.json").read_bytes())["returncode"] == 1
    )


def test_primary_checkout_cannot_be_mislabeled_as_a_clean_staged_release(
    tmp_path, monkeypatch
):
    root, environment, project = setup(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="immutable staged"):
        build_images.build_images(root, environment, project_root=project.parent)
