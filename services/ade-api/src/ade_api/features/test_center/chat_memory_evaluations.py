from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from ade_api.features.test_center.contracts import (
    ChatMemoryEvaluationConfigResponse,
    ChatMemoryEvaluationDetailResponse,
    ChatMemoryEvaluationFixtureResponse,
    ChatMemoryEvaluationListItemResponse,
    ChatMemoryEvaluationMemoryBlockResponse,
    ChatMemoryEvaluationMetricsResponse,
    ChatMemoryEvaluationRoundResponse,
    ChatMemoryEvaluationTurnResponse,
)
from ade_api.features.test_center.run_descriptors import (
    DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG,
)
from ade_api.features.test_center.run_store import RunRecord


class ChatMemoryEvaluationArtifactUnavailable(RuntimeError):
    """Raised when a persisted evaluation is not yet ready to be read safely."""


class _SummaryArtifact(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    rounds_total: int
    rounds_passed: int
    rounds_failed: int
    errors: int
    pass_rate: float
    config: dict[str, Any]
    fixture: ChatMemoryEvaluationFixtureResponse


@dataclass(frozen=True)
class _EvaluationArtifacts:
    config: ChatMemoryEvaluationConfigResponse
    fixture: ChatMemoryEvaluationFixtureResponse
    metrics: ChatMemoryEvaluationMetricsResponse
    rounds: list[ChatMemoryEvaluationRoundResponse]


class ChatMemoryEvaluationReader:
    """Projects runner artifacts into stable Test Center read models."""

    _SUMMARY_GLOB = "chat_memory_eval_*_summary.json"
    _JSONL_GLOB = "chat_memory_eval_*.jsonl"

    def __init__(self, state_root: Path):
        self._state_root = Path(state_root).resolve()

    def list_item(self, run: RunRecord) -> dict[str, Any]:
        request_config = self._config_from_mapping(run.get("options"))
        response = self._base_response(run, config=request_config, ready=False)
        if str(run.get("status", "")) in {"queued", "running"}:
            return response.model_dump()

        try:
            artifacts = self._read_artifacts(run)
        except ChatMemoryEvaluationArtifactUnavailable:
            return response.model_dump()

        return self._base_response(
            run,
            config=artifacts.config,
            ready=True,
            metrics=artifacts.metrics,
        ).model_dump()

    def detail(self, run: RunRecord) -> dict[str, Any]:
        if str(run.get("status", "")) in {"queued", "running"}:
            raise ChatMemoryEvaluationArtifactUnavailable(
                "Chat-memory evaluation artifacts are not ready while the run is active"
            )

        artifacts = self._read_artifacts(run)
        detail = ChatMemoryEvaluationDetailResponse(
            **self._base_response(
                run,
                config=artifacts.config,
                ready=True,
                metrics=artifacts.metrics,
            ).model_dump(),
            fixture=artifacts.fixture,
            rounds=artifacts.rounds,
        )
        return detail.model_dump()

    def _base_response(
        self,
        run: RunRecord,
        *,
        config: ChatMemoryEvaluationConfigResponse,
        ready: bool,
        metrics: ChatMemoryEvaluationMetricsResponse | None = None,
    ) -> ChatMemoryEvaluationListItemResponse:
        return ChatMemoryEvaluationListItemResponse(
            run_id=str(run.get("run_id", "")),
            run_status=str(run.get("status", "")),
            created_at=str(run.get("created_at", "")),
            finished_at=str(run.get("finished_at", "")),
            ready=ready,
            config=config,
            metrics=metrics,
        )

    def _read_artifacts(self, run: RunRecord) -> _EvaluationArtifacts:
        output_dir = self._output_directory(run)
        summary_path = self._single_artifact(output_dir, self._SUMMARY_GLOB, "summary")
        jsonl_path = self._single_artifact(output_dir, self._JSONL_GLOB, "JSONL")
        summary = self._read_summary(summary_path)
        rounds = self._read_rounds(jsonl_path)

        if summary.rounds_total != len(rounds):
            raise ChatMemoryEvaluationArtifactUnavailable(
                "Chat-memory evaluation summary round count does not match its JSONL artifact"
            )
        rounds_passed = sum(1 for round_ in rounds if round_.passed)
        errors = sum(1 for round_ in rounds if round_.status == "error")
        if (
            summary.rounds_passed != rounds_passed
            or summary.rounds_failed != len(rounds) - rounds_passed
            or summary.errors != errors
        ):
            raise ChatMemoryEvaluationArtifactUnavailable(
                "Chat-memory evaluation summary metrics do not match its JSONL artifact"
            )

        return _EvaluationArtifacts(
            config=self._config_from_mapping(summary.config),
            fixture=summary.fixture,
            metrics=self._metrics(summary, rounds),
            rounds=rounds,
        )

    def _output_directory(self, run: RunRecord) -> Path:
        output_dir = Path(str(run.get("output_dir", ""))).resolve()
        if not output_dir.is_relative_to(self._state_root) or not output_dir.is_dir():
            raise ChatMemoryEvaluationArtifactUnavailable(
                "Chat-memory evaluation output directory is unavailable"
            )
        return output_dir

    def _single_artifact(
        self, output_dir: Path, pattern: str, artifact_name: str
    ) -> Path:
        candidates: list[Path] = []
        try:
            for candidate in output_dir.glob(pattern):
                resolved = candidate.resolve()
                if (
                    resolved.is_relative_to(self._state_root)
                    and resolved.parent == output_dir
                    and resolved.is_file()
                ):
                    candidates.append(resolved)
        except OSError as exc:
            raise ChatMemoryEvaluationArtifactUnavailable(
                f"Unable to inspect chat-memory evaluation {artifact_name} artifacts"
            ) from exc

        if len(candidates) != 1:
            raise ChatMemoryEvaluationArtifactUnavailable(
                f"Expected exactly one chat-memory evaluation {artifact_name} artifact"
            )
        return candidates[0]

    def _read_summary(self, summary_path: Path) -> _SummaryArtifact:
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            return _SummaryArtifact.model_validate(payload)
        except (
            OSError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise ChatMemoryEvaluationArtifactUnavailable(
                "Chat-memory evaluation summary artifact is invalid"
            ) from exc

    def _read_rounds(self, jsonl_path: Path) -> list[ChatMemoryEvaluationRoundResponse]:
        try:
            lines = jsonl_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise ChatMemoryEvaluationArtifactUnavailable(
                "Unable to read chat-memory evaluation JSONL artifact"
            ) from exc

        rounds: list[ChatMemoryEvaluationRoundResponse] = []
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("JSONL row must be an object")
                rounds.append(self._round_from_raw(raw))
            except (ValueError, ValidationError, json.JSONDecodeError) as exc:
                raise ChatMemoryEvaluationArtifactUnavailable(
                    f"Chat-memory evaluation JSONL artifact is invalid at line {line_number}"
                ) from exc
        return rounds

    def _round_from_raw(self, raw: dict[str, Any]) -> ChatMemoryEvaluationRoundResponse:
        raw_turns = raw.get("turns", [])
        if not isinstance(raw_turns, list):
            raise ValueError("round turns must be a list")
        return ChatMemoryEvaluationRoundResponse.model_validate(
            {
                "round": raw.get("round"),
                "status": raw.get("status"),
                "passed": raw.get("pass"),
                "elapsed_seconds": raw.get("elapsed_seconds"),
                "agent_id": raw.get("agent_id", ""),
                "archived": raw.get("archived", False),
                "purged": raw.get("purged", False),
                "error": raw.get("error", ""),
                "initial_human_memory": raw.get("initial_human_memory", ""),
                "final_human_memory": raw.get("final_human_memory", ""),
                "deterministic_score": self._deterministic_score_from_raw(raw),
                "judge": raw.get("judge", {}),
                "turns": [self._turn_from_raw(turn) for turn in raw_turns],
                "memory_blocks": self._memory_blocks_from_raw(raw),
            }
        )

    @staticmethod
    def _deterministic_score_from_raw(raw: dict[str, Any]) -> Any:
        score = raw.get("deterministic_score")
        if isinstance(score, dict):
            return score
        if raw.get("status") != "error":
            return score

        # Workflow error rows predate the typed read model and expose their
        # deterministic signals as flat CSV-compatible fields.
        missing_facts = raw.get("missing_expected_facts", "")
        return {
            "pass": False,
            "forbidden_hit_count": _nonnegative_int(raw.get("forbidden_hit_count")),
            "forbidden_hits": [],
            "human_memory_changed": raw.get("human_memory_changed") is True,
            "expected_facts_passed": raw.get("expected_facts_passed") is True,
            "missing_expected_facts": (
                [item.strip() for item in missing_facts.split(",") if item.strip()]
                if isinstance(missing_facts, str)
                else []
            ),
        }

    @staticmethod
    def _turn_from_raw(raw: Any) -> ChatMemoryEvaluationTurnResponse:
        if not isinstance(raw, dict):
            raise ValueError("turn must be an object")
        return ChatMemoryEvaluationTurnResponse.model_validate(
            {
                "turn_index": raw.get("turn_index"),
                "user_input": raw.get("user_input"),
                "assistant_replies": raw.get("assistant_replies"),
                "elapsed_seconds": raw.get("elapsed_seconds"),
                "memory_changed_this_turn": raw.get("memory_changed_this_turn"),
                "human_memory_before_turn": raw.get("human_memory_before_turn"),
                "human_memory_after_turn": raw.get("human_memory_after_turn"),
                "tool_calls": raw.get("tool_calls"),
                "memory_tool_calls": raw.get("memory_tool_calls"),
            }
        )

    @staticmethod
    def _memory_blocks_from_raw(
        raw: dict[str, Any],
    ) -> list[ChatMemoryEvaluationMemoryBlockResponse]:
        persistent_state = raw.get("persistent_state")
        if not isinstance(persistent_state, dict):
            return []
        raw_blocks = persistent_state.get("memory_blocks")
        if not isinstance(raw_blocks, list):
            return []

        blocks: list[ChatMemoryEvaluationMemoryBlockResponse] = []
        for raw_block in raw_blocks:
            if not isinstance(raw_block, dict):
                continue
            label = raw_block.get("label")
            value = raw_block.get("value")
            if not isinstance(label, str) or not isinstance(value, str):
                continue
            description = raw_block.get("description")
            limit = raw_block.get("limit")
            blocks.append(
                ChatMemoryEvaluationMemoryBlockResponse(
                    label=label,
                    value=value,
                    description=description if isinstance(description, str) else None,
                    limit=limit if type(limit) is int else None,
                )
            )
        return blocks

    @staticmethod
    def _config_from_mapping(value: Any) -> ChatMemoryEvaluationConfigResponse:
        source = value if isinstance(value, dict) else {}
        mapping = {**DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG}
        for key in DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG:
            if key in source:
                mapping[key] = source[key]

        timeout = mapping["timeout_seconds"]
        rounds = mapping["rounds"]
        retry_count = mapping["retry_count"]
        judge_enabled = mapping["judge_enabled"]
        return ChatMemoryEvaluationConfigResponse(
            model=ChatMemoryEvaluationReader._string_or_default(
                mapping["model"], "model"
            ),
            prompt_key=ChatMemoryEvaluationReader._string_or_default(
                mapping["prompt_key"], "prompt_key"
            ),
            persona_key=ChatMemoryEvaluationReader._string_or_default(
                mapping["persona_key"], "persona_key"
            ),
            embedding=ChatMemoryEvaluationReader._string_or_default(
                mapping["embedding"], "embedding"
            ),
            fixture_key=ChatMemoryEvaluationReader._string_or_default(
                mapping["fixture_key"], "fixture_key"
            ),
            rounds=(
                rounds
                if type(rounds) is int
                else DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG["rounds"]
            ),
            timeout_seconds=(
                float(timeout)
                if type(timeout) in {int, float}
                else DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG["timeout_seconds"]
            ),
            retry_count=(
                retry_count
                if type(retry_count) is int
                else DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG["retry_count"]
            ),
            judge_enabled=(
                judge_enabled
                if type(judge_enabled) is bool
                else DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG["judge_enabled"]
            ),
        )

    @staticmethod
    def _string_or_default(value: Any, key: str) -> str:
        if isinstance(value, str) and value.strip():
            return value
        return str(DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG[key])

    @staticmethod
    def _metrics(
        summary: _SummaryArtifact,
        rounds: list[ChatMemoryEvaluationRoundResponse],
    ) -> ChatMemoryEvaluationMetricsResponse:
        elapsed_total = sum(round_.elapsed_seconds for round_ in rounds)
        return ChatMemoryEvaluationMetricsResponse(
            rounds_total=summary.rounds_total,
            rounds_passed=summary.rounds_passed,
            rounds_failed=summary.rounds_failed,
            errors=summary.errors,
            pass_rate=summary.pass_rate,
            average_elapsed_seconds=(
                round(elapsed_total / len(rounds), 3) if rounds else 0.0
            ),
            forbidden_hit_count=sum(
                _nonnegative_int(round_.deterministic_score.get("forbidden_hit_count"))
                for round_ in rounds
            ),
            memory_changed_rounds=sum(
                bool(round_.deterministic_score.get("human_memory_changed"))
                for round_ in rounds
            ),
            expected_facts_passed_rounds=sum(
                bool(round_.deterministic_score.get("expected_facts_passed"))
                for round_ in rounds
            ),
            memory_tool_call_count=sum(
                len(turn.memory_tool_calls)
                for round_ in rounds
                for turn in round_.turns
            ),
            total_tool_call_count=sum(
                len(turn.tool_calls) for round_ in rounds for turn in round_.turns
            ),
            cleanup_passed_rounds=sum(
                round_.archived and round_.purged for round_ in rounds
            ),
        )


def _nonnegative_int(value: Any) -> int:
    return value if type(value) is int and value >= 0 else 0
