from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final


RunOptions = Mapping[str, Any]
ArtifactRecord = dict[str, Any]


@dataclass(frozen=True)
class ArtifactDiscoveryContext:
    """Filesystem context that a run descriptor may expose as artifacts."""

    output_dir: Path
    log_file: Path | None
    state_root: Path


CommandBuilder = Callable[[Path, RunOptions], list[str]]
ArtifactDiscoverer = Callable[[ArtifactDiscoveryContext], list[ArtifactRecord]]


@dataclass(frozen=True)
class TestRunDescriptor:
    """Owns the executable and artifact contract for one Test Center run type."""

    run_type: str
    accepted_fields: frozenset[str]
    unexpected_field_message: str
    command_builder: CommandBuilder
    artifact_discoverer: ArtifactDiscoverer

    def validate_options(self, options: RunOptions) -> None:
        unexpected = sorted(set(options).difference(self.accepted_fields))
        if not unexpected:
            return

        raise ValueError(self.unexpected_field_message + ": " + ", ".join(unexpected))

    def build_command(self, output_dir: Path, options: RunOptions) -> list[str]:
        self.validate_options(options)
        return self.command_builder(output_dir, options)

    def discover_artifacts(
        self, context: ArtifactDiscoveryContext
    ) -> list[ArtifactRecord]:
        return self.artifact_discoverer(context)


CHAT_MEMORY_EVAL_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "model",
        "prompt_key",
        "persona_key",
        "embedding",
        "rounds",
        "fixture_key",
        "timeout_seconds",
        "retry_count",
        "judge_enabled",
        "judge_model_key",
    }
)


def _append_option(command: list[str], flag: str, value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    command.extend([flag, str(value)])


def _build_api_e2e_check(_: Path, __: RunOptions) -> list[str]:
    return [sys.executable, "workflows/smoke/ade_api_e2e_check.py"]


def _build_ade_mvp_smoke_e2e_check(_: Path, __: RunOptions) -> list[str]:
    return [sys.executable, "workflows/smoke/ade_mvp_smoke_e2e_check.py"]


def _build_chat_memory_eval(output_dir: Path, options: RunOptions) -> list[str]:
    command = [
        sys.executable,
        "workflows/evals/chat_memory_eval/run.py",
        "--config",
        "workflows/evals/chat_memory_eval/config.toml",
        "--output-dir",
        str(output_dir),
    ]
    _append_option(command, "--model", options.get("model"))
    _append_option(command, "--prompt-key", options.get("prompt_key"))
    _append_option(command, "--persona-key", options.get("persona_key"))
    _append_option(command, "--embedding", options.get("embedding"))
    _append_option(command, "--fixture-key", options.get("fixture_key"))
    _append_option(command, "--judge-model-key", options.get("judge_model_key"))
    _append_option(command, "--rounds", options.get("rounds"))
    _append_option(command, "--timeout-seconds", options.get("timeout_seconds"))
    _append_option(command, "--retry-count", options.get("retry_count"))
    if options.get("judge_enabled") is True:
        command.append("--judge-enabled")
    if options.get("judge_enabled") is False:
        command.append("--no-judge-enabled")
    return command


def discover_run_directory_artifacts(
    context: ArtifactDiscoveryContext,
) -> list[ArtifactRecord]:
    """Expose only files rooted in the orchestrator-owned run directory."""

    output_dir = context.output_dir.resolve()
    if not output_dir.is_relative_to(context.state_root.resolve()):
        return []

    artifacts: list[ArtifactRecord] = []
    log_file = context.log_file.resolve() if context.log_file else None
    if log_file and log_file.is_relative_to(output_dir):
        try:
            log_exists = log_file.is_file()
            log_size = log_file.stat().st_size if log_exists else 0
        except FileNotFoundError:
            log_exists = False
            log_size = 0
        artifacts.append(
            {
                "artifact_id": "orchestrator_log",
                "type": "log",
                "path": str(log_file),
                "exists": log_exists,
                "size_bytes": log_size,
            }
        )

    if not output_dir.is_dir():
        return artifacts

    for path in sorted(output_dir.rglob("*")):
        if path.name.startswith(".") or path.name == "run.json":
            continue
        try:
            if not path.is_file():
                continue
            resolved_path = path.resolve()
            if not resolved_path.is_relative_to(output_dir):
                continue
            if resolved_path == log_file:
                continue
            size_bytes = path.stat().st_size
        except FileNotFoundError:
            # A worker may atomically replace an artifact while the UI refreshes.
            continue
        relative = path.relative_to(output_dir).as_posix()
        artifacts.append(
            {
                "artifact_id": relative.replace("/", "__"),
                "type": path.suffix.lower().lstrip(".") or "artifact",
                "path": str(resolved_path),
                "exists": True,
                "size_bytes": size_bytes,
            }
        )
    return artifacts


RUN_DESCRIPTORS: Final[dict[str, TestRunDescriptor]] = {
    "ade_api_e2e_check": TestRunDescriptor(
        run_type="ade_api_e2e_check",
        accepted_fields=frozenset(),
        unexpected_field_message="Chat memory eval fields are only accepted when run_type='chat_memory_eval'",
        command_builder=_build_api_e2e_check,
        artifact_discoverer=discover_run_directory_artifacts,
    ),
    "ade_mvp_smoke_e2e_check": TestRunDescriptor(
        run_type="ade_mvp_smoke_e2e_check",
        accepted_fields=frozenset(),
        unexpected_field_message="Chat memory eval fields are only accepted when run_type='chat_memory_eval'",
        command_builder=_build_ade_mvp_smoke_e2e_check,
        artifact_discoverer=discover_run_directory_artifacts,
    ),
    "chat_memory_eval": TestRunDescriptor(
        run_type="chat_memory_eval",
        accepted_fields=CHAT_MEMORY_EVAL_FIELDS,
        unexpected_field_message="Unsupported fields for run_type='chat_memory_eval'",
        command_builder=_build_chat_memory_eval,
        artifact_discoverer=discover_run_directory_artifacts,
    ),
}

_LEGACY_ARTIFACT_DESCRIPTOR: Final[TestRunDescriptor] = TestRunDescriptor(
    run_type="legacy_persisted_run",
    accepted_fields=frozenset(),
    unexpected_field_message="Unsupported fields for run_type='legacy_persisted_run'",
    command_builder=lambda _output_dir, _options: [],
    artifact_discoverer=discover_run_directory_artifacts,
)


def get_run_descriptor(run_type: str) -> TestRunDescriptor:
    try:
        return RUN_DESCRIPTORS[run_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported run_type: {run_type}") from exc


def get_persisted_run_descriptor(run_type: str) -> TestRunDescriptor:
    """Keep historical manifests readable if a later release retires a run type."""

    return RUN_DESCRIPTORS.get(run_type, _LEGACY_ARTIFACT_DESCRIPTOR)


def validate_test_run_options(run_type: str, options: RunOptions) -> None:
    get_run_descriptor(run_type).validate_options(options)
