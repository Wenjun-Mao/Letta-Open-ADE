from __future__ import annotations

import importlib.metadata
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import httpx


UPSTREAM_REFERENCES = {
    "memgpt_paper": "https://arxiv.org/abs/2310.08560",
    "letta_repository": "https://github.com/letta-ai/letta",
    "letta_0_16_8_release": "https://github.com/letta-ai/letta/releases/tag/v0.16.8",
    "letta_agents_api": "https://docs.letta.com/api/resources/agents",
    "letta_memory_blocks": "https://docs.letta.com/api/typescript/resources/agents/subresources/blocks",
    "letta_code_prompt": "https://github.com/letta-ai/letta-code/blob/main/src/agent/prompts/letta.md",
    "pydantic_ai_2_35_1": "https://pypi.org/project/pydantic-ai/2.35.1/",
    "pydantic_ai_agents": "https://pydantic.dev/docs/ai/core-concepts/agents/",
    "pydantic_ai_history": "https://pydantic.dev/docs/ai/core-concepts/message-history/",
    "pydantic_ai_openai": "https://pydantic.dev/docs/ai/models/openai/",
}


def _run(command: list[str], *, cwd: Path) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc), "command": command}
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "command": command,
    }


def capture_provenance(project_root: Path) -> dict[str, Any]:
    compose_text = (project_root / "compose.yaml").read_text(encoding="utf-8")
    match = re.search(r"LETTA_SERVER_IMAGE:-([^}]+)", compose_text)
    pinned_image = match.group(1) if match else "unknown"
    image_inspect = _run(
        [
            "docker",
            "image",
            "inspect",
            pinned_image,
            "--format",
            "{{json .}}",
        ],
        cwd=project_root,
    )
    image_payload: dict[str, Any] = {}
    if image_inspect.get("ok"):
        try:
            parsed = json.loads(str(image_inspect.get("stdout") or "{}"))
            image_payload = {
                "id": parsed.get("Id"),
                "repo_digests": parsed.get("RepoDigests"),
                "created": parsed.get("Created"),
            }
        except json.JSONDecodeError:
            image_payload = {"raw": image_inspect.get("stdout")}
    runtime_version = _run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "letta",
            "python",
            "-c",
            "import letta; print(letta.__version__)",
        ],
        cwd=project_root,
    )
    git_revision = _run(["git", "rev-parse", "HEAD"], cwd=project_root)
    git_status = _run(["git", "status", "--short"], cwd=project_root)
    try:
        pydantic_ai_version = importlib.metadata.version("pydantic-ai-slim")
    except importlib.metadata.PackageNotFoundError:
        pydantic_ai_version = "not-installed"
    return {
        "repository_revision": git_revision.get("stdout"),
        "repository_status": git_status.get("stdout"),
        "source_hashes": {
            "study_tree_sha256": _tree_hash(
                project_root / "workflows" / "evals" / "agent_runtime_study"
            ),
            "fixture_sha256": _file_hash(
                project_root
                / "workflows"
                / "evals"
                / "agent_runtime_study"
                / "fixtures"
                / "study_cases.json"
            ),
            "uv_lock_sha256": _file_hash(project_root / "uv.lock"),
            "chat_prompt_sha256": _file_hash(
                project_root
                / "content"
                / "prompts"
                / "system"
                / "chat"
                / "chat_v20260516.py"
            ),
            "persona_registry_sha256": _file_hash(
                project_root / "content" / "personas" / "personas.jsonl"
            ),
        },
        "letta": {
            "compose_image": pinned_image,
            "image": image_payload,
            "runtime_version": runtime_version.get("stdout"),
            "runtime_version_probe_ok": runtime_version.get("ok"),
            "release_commit_from_upstream_notes": "1131535",
        },
        "pydantic_ai_slim_version": pydantic_ai_version,
        "upstream_references": UPSTREAM_REFERENCES,
    }


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or "__pycache__" in path.parts
            or "outputs" in path.parts
            or path.suffix == ".pyc"
        ):
            continue
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


async def capture_router_catalog(*, base_url: str, api_key: str) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/models",
                headers=headers,
            )
        payload: object
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        return {
            "ok": response.status_code < 400,
            "status_code": response.status_code,
            "payload": payload,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
