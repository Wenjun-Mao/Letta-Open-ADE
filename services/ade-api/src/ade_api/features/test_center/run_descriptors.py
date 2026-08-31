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
OptionValidator = Callable[[RunOptions], None]


def _accept_any_values(_: RunOptions) -> None:
    return None


@dataclass(frozen=True)
class TestRunDescriptor:
    """Owns the executable and artifact contract for one Test Center run type."""

    run_type: str
    accepted_fields: frozenset[str]
    unexpected_field_message: str
    command_builder: CommandBuilder
    artifact_discoverer: ArtifactDiscoverer
    option_validator: OptionValidator = _accept_any_values

    def validate_options(self, options: RunOptions) -> None:
        unexpected = sorted(set(options).difference(self.accepted_fields))
        if not unexpected:
            self.option_validator(options)
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

AGENT_RUNTIME_V3_ACCEPTANCE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "conversation_model_key",
        "reviewer_model_key",
        "embedding_model_key",
        "rounds",
        "timeout_seconds",
        "retry_count",
        "include_llama_compatibility",
        "case_keys",
    }
)

AGENT_RUNTIME_V3_DIAGNOSTIC_CASE_KEYS: Final[tuple[str, ...]] = (
    "chat_memory_baseline",
    "correction_chain",
    "explicit_forgetting",
    "cross_agent_subject_sharing",
    "cross_subject_isolation",
    "old_memory_deep_search",
    "long_history_compaction",
    "false_memory_prevention",
    "weather_tool_selection",
    "weather_tool_failure",
)


def canonicalize_agent_runtime_v3_case_keys(
    case_keys: object,
) -> tuple[str, ...]:
    """Validate diagnostic cases and preserve the runner's canonical ordering."""

    if not isinstance(case_keys, (list, tuple)):
        raise ValueError(
            "agent runtime v3 case_keys must be a list of canonical case keys"
        )
    if not case_keys:
        raise ValueError("agent runtime v3 case_keys must not be empty")
    if not all(isinstance(case_key, str) for case_key in case_keys):
        raise ValueError(
            "agent runtime v3 case_keys must contain canonical string values"
        )

    selected_keys = tuple(case_keys)
    if len(selected_keys) != len(set(selected_keys)):
        raise ValueError("agent runtime v3 case_keys must not contain duplicates")

    unknown_keys = sorted(
        set(selected_keys).difference(AGENT_RUNTIME_V3_DIAGNOSTIC_CASE_KEYS)
    )
    if unknown_keys:
        raise ValueError(
            "agent runtime v3 case_keys must be canonical: " + ", ".join(unknown_keys)
        )

    selected = set(selected_keys)
    return tuple(
        case_key
        for case_key in AGENT_RUNTIME_V3_DIAGNOSTIC_CASE_KEYS
        if case_key in selected
    )


# These mirror the runner TOML so Test Center can render an active run before
# the runner has written its effective config into the summary artifact.
DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG: Final[dict[str, Any]] = {
    "model": "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8",
    "prompt_key": "chat_v20260516",
    "persona_key": "chat_linxiaotang",
    "embedding": "letta/letta-free",
    "fixture_key": "recent_user_chat_turns",
    "rounds": 3,
    "timeout_seconds": 180.0,
    "retry_count": 0,
    "judge_enabled": True,
}

DEFAULT_AGENT_RUNTIME_V3_ACCEPTANCE_CONFIG: Final[dict[str, Any]] = {
    "conversation_model_key": "dgx_vllm::qwen3.6-35b-a3b-fp8",
    "reviewer_model_key": "dgx_vllm::qwen3.6-35b-a3b-fp8",
    "embedding_model_key": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
    "rounds": 3,
    "timeout_seconds": 180.0,
    "retry_count": 0,
    "include_llama_compatibility": True,
}


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
        "--run-id",
        output_dir.name,
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


def _validate_chat_memory_eval(options: RunOptions) -> None:
    retry_count = options.get("retry_count")
    if retry_count not in {None, 0}:
        raise ValueError(
            "chat memory evaluation retry_count must be 0 because message requests "
            "do not have a server-owned idempotency contract"
        )


def _validate_agent_runtime_v3_acceptance(options: RunOptions) -> None:
    rounds = options.get("rounds")
    if rounds is not None and (not isinstance(rounds, int) or not 1 <= rounds <= 3):
        raise ValueError("agent runtime v3 acceptance rounds must be between 1 and 3")
    timeout_seconds = options.get("timeout_seconds")
    if timeout_seconds is not None and float(timeout_seconds) < 5:
        raise ValueError(
            "agent runtime v3 acceptance timeout_seconds must be between 5 and 600"
        )
    case_keys = options.get("case_keys")
    if case_keys is not None:
        canonicalize_agent_runtime_v3_case_keys(case_keys)


def _build_agent_runtime_v3_acceptance(
    output_dir: Path, options: RunOptions
) -> list[str]:
    case_keys = (
        canonicalize_agent_runtime_v3_case_keys(options["case_keys"])
        if options.get("case_keys") is not None
        else ()
    )
    command = [
        sys.executable,
        "workflows/evals/agent_runtime_v3_acceptance/run.py",
        "--config",
        "workflows/evals/agent_runtime_v3_acceptance/config.toml",
        "--output-dir",
        str(output_dir),
    ]
    _append_option(
        command, "--conversation-model-key", options.get("conversation_model_key")
    )
    _append_option(command, "--reviewer-model-key", options.get("reviewer_model_key"))
    _append_option(command, "--embedding-model-key", options.get("embedding_model_key"))
    if case_keys:
        for case_key in case_keys:
            command.extend(["--case-key", case_key])
        _append_option(command, "--timeout-seconds", options.get("timeout_seconds"))
        _append_option(command, "--retry-count", options.get("retry_count"))
        # Focused runs are diagnostics. Their command cannot satisfy promotion
        # qualification requirements, regardless of the submitted form state.
        command.extend(["--rounds", "1", "--no-include-llama-compatibility"])
        return command
    _append_option(command, "--rounds", options.get("rounds"))
    _append_option(command, "--timeout-seconds", options.get("timeout_seconds"))
    _append_option(command, "--retry-count", options.get("retry_count"))
    compatibility = options.get("include_llama_compatibility")
    if compatibility is True:
        command.append("--include-llama-compatibility")
    if compatibility is False:
        command.append("--no-include-llama-compatibility")
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
        option_validator=_validate_chat_memory_eval,
    ),
    "agent_runtime_v3_acceptance": TestRunDescriptor(
        run_type="agent_runtime_v3_acceptance",
        accepted_fields=AGENT_RUNTIME_V3_ACCEPTANCE_FIELDS,
        unexpected_field_message=(
            "Unsupported fields for run_type='agent_runtime_v3_acceptance'"
        ),
        command_builder=_build_agent_runtime_v3_acceptance,
        artifact_discoverer=discover_run_directory_artifacts,
        option_validator=_validate_agent_runtime_v3_acceptance,
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
