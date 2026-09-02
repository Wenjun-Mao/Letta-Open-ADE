from __future__ import annotations

import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Callable
from uuid import uuid4

import httpx


def verify_legacy_web(
    *,
    project_root: Path,
    legacy_revision: str,
    compose_network: str,
    legacy_api_key: str,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
    client: httpx.Client,
    sleep: Callable[[float], None],
) -> tuple[bool, bool]:
    suffix = uuid4().hex[:12]
    image = f"ade-agent-studio-rollback:{legacy_revision[:12]}-{suffix}"
    container = f"ade-agent-studio-rollback-{suffix}"
    image_built = False
    container_started = False
    try:
        with tempfile.TemporaryDirectory(prefix="ade-v2-rollback-") as temporary:
            root = Path(temporary)
            archive = root / "legacy-web.tar"
            _run_command(
                command_runner,
                [
                    "git",
                    "archive",
                    "--format=tar",
                    f"--output={archive}",
                    legacy_revision,
                    "apps/ade-web",
                ],
                cwd=project_root,
                error_code="legacy_web_archive_failed",
            )
            with tarfile.open(archive) as bundle:
                bundle.extractall(root, filter="data")
            _run_command(
                command_runner,
                [
                    "docker",
                    "build",
                    "--tag",
                    image,
                    "--file",
                    str(root / "apps/ade-web/Dockerfile"),
                    str(root / "apps/ade-web"),
                ],
                cwd=project_root,
                error_code="legacy_web_build_failed",
            )
            image_built = True
        environment = {**os.environ, "ADE_API_ADMIN_KEY": legacy_api_key}
        _run_command(
            command_runner,
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                container,
                "--network",
                compose_network,
                "--publish",
                "127.0.0.1::3000",
                "--env",
                "ADE_API_ADMIN_KEY",
                "--env",
                "ADE_API_BASE_URL=http://ade-api:8000",
                image,
            ],
            cwd=project_root,
            env=environment,
            error_code="legacy_web_start_failed",
        )
        container_started = True
        port_result = _run_command(
            command_runner,
            ["docker", "port", container, "3000/tcp"],
            cwd=project_root,
            error_code="legacy_web_port_failed",
        )
        host_port = _published_port(port_result.stdout)
        for _ in range(60):
            try:
                response = client.get(
                    f"http://127.0.0.1:{host_port}/agent-studio",
                    follow_redirects=True,
                )
                if 200 <= response.status_code < 300:
                    return image_built, True
            except httpx.HTTPError:
                pass
            sleep(2)
        return image_built, False
    finally:
        if container_started:
            command_runner(
                ["docker", "rm", "--force", container],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
        if image_built:
            command_runner(
                ["docker", "image", "rm", "--force", image],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )


def _run_command(
    runner: Callable[..., subprocess.CompletedProcess[str]],
    command: list[str],
    *,
    cwd: Path,
    error_code: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = runner(
        command,
        cwd=cwd,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(error_code)
    return completed


def _published_port(output: str) -> int:
    address = output.strip().splitlines()[-1] if output.strip() else ""
    try:
        port = int(address.rsplit(":", 1)[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError("legacy_web_port_invalid") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("legacy_web_port_invalid")
    return port
