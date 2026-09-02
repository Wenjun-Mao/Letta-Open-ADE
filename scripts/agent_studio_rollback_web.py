from __future__ import annotations

import os
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import httpx


@dataclass(frozen=True)
class LegacyWebApiVerification:
    """Evidence that the legacy Next.js proxy completed a disposable v2 lifecycle."""

    api_read_passed: bool = False
    api_write_passed: bool = False
    api_cleanup_passed: bool = False


@dataclass(frozen=True)
class LegacyWebVerification:
    image_built: bool = False
    page_loaded: bool = False
    api_read_passed: bool = False
    api_write_passed: bool = False
    api_cleanup_passed: bool = False

    @property
    def smoke_passed(self) -> bool:
        return (
            self.image_built
            and self.page_loaded
            and self.api_read_passed
            and self.api_write_passed
            and self.api_cleanup_passed
        )


def verify_legacy_web(
    *,
    project_root: Path,
    legacy_revision: str,
    compose_network: str,
    legacy_api_key: str,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
    client: httpx.Client,
    sleep: Callable[[float], None],
) -> LegacyWebVerification:
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
                    api_verification = exercise_legacy_agent_studio_proxy(
                        client=client,
                        legacy_web_base_url=f"http://127.0.0.1:{host_port}",
                        agent_name=f"ade-rollback-web-{suffix}",
                        memory_marker=f"rollback rehearsal {suffix}",
                    )
                    return LegacyWebVerification(
                        image_built=image_built,
                        page_loaded=True,
                        api_read_passed=api_verification.api_read_passed,
                        api_write_passed=api_verification.api_write_passed,
                        api_cleanup_passed=api_verification.api_cleanup_passed,
                    )
            except httpx.HTTPError:
                pass
            sleep(2)
        return LegacyWebVerification(image_built=image_built)
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


def exercise_legacy_agent_studio_proxy(
    *,
    client: httpx.Client,
    legacy_web_base_url: str,
    agent_name: str,
    memory_marker: str,
) -> LegacyWebApiVerification:
    """Run an isolated v2 Agent Studio lifecycle through the legacy web proxy.

    The browser-facing route owns the authorization header, so this deliberately
    sends no API key from the rehearsal process. Every request must traverse the
    exact legacy `/api/v2/...` Next.js proxy before it reaches the retained v2 API.
    """

    agent_id = ""
    api_read_passed = False
    api_write_passed = False
    api_cleanup_passed = False
    try:
        options = _proxy_json(
            client,
            legacy_web_base_url,
            "GET",
            "/api/v2/model-catalog/options?scenario=chat",
        )
        create_payload = _legacy_agent_create_payload(options, agent_name)
        created = _proxy_json(
            client,
            legacy_web_base_url,
            "POST",
            "/api/v2/agent-studio/agents",
            payload=create_payload,
        )
        agent_id = _required_text(created, "id")
        before = _proxy_json(
            client,
            legacy_web_base_url,
            "GET",
            f"/api/v2/agent-studio/agents/{agent_id}/persistent-state?limit=1",
        )
        if _memory_block_value(before, "human") is None:
            raise RuntimeError("legacy_web_proxy_read_invalid")
        api_read_passed = True

        updated = _proxy_json(
            client,
            legacy_web_base_url,
            "PATCH",
            f"/api/v2/agent-studio/agents/{agent_id}/memory/human",
            payload={"value": memory_marker},
        )
        if updated.get("value_after") != memory_marker:
            raise RuntimeError("legacy_web_proxy_write_invalid")
        after = _proxy_json(
            client,
            legacy_web_base_url,
            "GET",
            f"/api/v2/agent-studio/agents/{agent_id}/persistent-state?limit=1",
        )
        if _memory_block_value(after, "human") != memory_marker:
            raise RuntimeError("legacy_web_proxy_write_not_persisted")
        api_write_passed = True
    except (httpx.HTTPError, RuntimeError, TypeError, ValueError):
        # The receipt intentionally records booleans, never upstream details or keys.
        pass
    finally:
        if agent_id:
            try:
                purged = _proxy_json(
                    client,
                    legacy_web_base_url,
                    "DELETE",
                    f"/api/v2/agent-studio/agents/{agent_id}/purge",
                )
                api_cleanup_passed = (
                    purged.get("ok") is True and purged.get("id") == agent_id
                )
            except (httpx.HTTPError, RuntimeError, TypeError, ValueError):
                pass
    return LegacyWebApiVerification(
        api_read_passed=api_read_passed,
        api_write_passed=api_write_passed,
        api_cleanup_passed=api_cleanup_passed,
    )


def _proxy_json(
    client: httpx.Client,
    base_url: str,
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.request(
        method,
        f"{base_url.rstrip('/')}{path}",
        json=payload,
        follow_redirects=True,
    )
    if not 200 <= response.status_code < 300:
        raise RuntimeError("legacy_web_proxy_request_failed")
    decoded = response.json()
    if not isinstance(decoded, dict):
        raise RuntimeError("legacy_web_proxy_response_invalid")
    return decoded


def _legacy_agent_create_payload(
    options: dict[str, Any], agent_name: str
) -> dict[str, Any]:
    model = _first_option_key(options, "models")
    prompt_key = _selected_option_key(options, "prompts", "prompt_key")
    persona_key = _selected_option_key(options, "personas", "persona_key")
    payload: dict[str, Any] = {
        "scenario": "chat",
        "name": agent_name,
        "model": model,
        "prompt_key": prompt_key,
        "persona_key": persona_key,
    }
    embedding = _selected_option_key(
        options,
        "embeddings",
        "embedding",
        required=False,
    )
    if embedding is not None:
        payload["embedding"] = embedding
    return payload


def _first_option_key(options: dict[str, Any], collection: str) -> str:
    entries = options.get(collection)
    if not isinstance(entries, list):
        raise RuntimeError("legacy_web_proxy_options_invalid")
    for entry in entries:
        if isinstance(entry, dict):
            value = entry.get("key")
            if isinstance(value, str) and value.strip():
                return value
    raise RuntimeError("legacy_web_proxy_options_invalid")


def _selected_option_key(
    options: dict[str, Any],
    collection: str,
    default_field: str,
    *,
    required: bool = True,
) -> str | None:
    entries = options.get(collection)
    defaults = options.get("defaults")
    if not isinstance(entries, list) or not isinstance(defaults, dict):
        if required:
            raise RuntimeError("legacy_web_proxy_options_invalid")
        return None
    available = {
        value
        for entry in entries
        if isinstance(entry, dict)
        for value in [entry.get("key")]
        if isinstance(value, str) and value.strip()
    }
    selected = defaults.get(default_field)
    if isinstance(selected, str) and selected in available:
        return selected
    if required:
        raise RuntimeError("legacy_web_proxy_options_invalid")
    return None


def _required_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("legacy_web_proxy_response_invalid")
    return value


def _memory_block_value(state: dict[str, Any], label: str) -> str | None:
    blocks = state.get("memory_blocks")
    if not isinstance(blocks, list):
        return None
    for block in blocks:
        if isinstance(block, dict) and block.get("label") == label:
            value = block.get("value")
            return value if isinstance(value, str) else None
    return None


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
