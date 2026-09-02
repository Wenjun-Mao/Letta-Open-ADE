from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pydantic import ValidationError

from ade_api.features.test_center.contracts import (
    AgentRuntimeParityArtifactDigestsResponse,
    AgentRuntimeParityCleanupResponse,
    AgentRuntimeParityConfigResponse,
    AgentRuntimeParityDetailResponse,
    AgentRuntimeParityListItemResponse,
    AgentRuntimeParityProvenanceResponse,
    AgentRuntimeParityRoundResponse,
    AgentRuntimeParityTurnResponse,
)
from ade_api.features.test_center.run_descriptors import (
    DEFAULT_AGENT_RUNTIME_PARITY_CONFIG,
)
from ade_api.features.test_center.run_store import RunRecord


class AgentRuntimeParityArtifactUnavailable(RuntimeError):
    """Raised when a parity result cannot be proven from its stored artifacts."""


@dataclass(frozen=True)
class _ParityArtifacts:
    config: AgentRuntimeParityConfigResponse
    passed: bool
    inputs_comparable: bool
    cleanup_complete: bool
    rounds_requested: int
    rounds_completed: int
    rounds_passed: int
    artifact_digests: AgentRuntimeParityArtifactDigestsResponse
    checks: dict[str, bool]
    comparability_checks: dict[str, bool]
    cleanup: AgentRuntimeParityCleanupResponse
    provenance: AgentRuntimeParityProvenanceResponse
    rounds: list[AgentRuntimeParityRoundResponse]
    turns: list[AgentRuntimeParityTurnResponse]
    preflight_error: dict[str, str] | None


class AgentRuntimeParityEvaluationReader:
    """Project signed paired-product artifacts into stable Test Center evidence."""

    _COMPARISON_CHECKS = frozenset(
        {
            "preflight_completed",
            "inputs_comparable",
            "all_paired_rounds_pass",
            "cleanup_complete",
            "zero_retry_policy",
        }
    )
    _COMPARABILITY_CHECKS = frozenset(
        {
            "parity_spec_hash_present",
            "source_identity_complete",
            "native_worker_build_matches_evaluator",
            "legacy_inputs_available",
            "fixture_hash_present",
            "all_native_rounds_have_definitions",
            "prompt_snapshots_match",
            "persona_snapshots_match",
            "conversation_models_match",
            "reviewer_models_match",
            "native_embedding_matches",
        }
    )
    _LEGACY_SCORE_CHECKS = frozenset(
        {
            "no_forbidden_disclosure",
            "expected_facts_captured",
            "all_turns_succeeded",
            "timeout_retry_controls_exact",
        }
    )
    _NATIVE_SCORE_CHECKS = _LEGACY_SCORE_CHECKS | {"agent_studio_session_lifecycle"}
    _REQUIRED_ENGINES = frozenset({"letta-v2", "ade-native-v3"})
    _GIT_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
    _SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
    _EMPTY_FILE_SHA256 = hashlib.sha256(b"").hexdigest()

    _ARTIFACT_NAMES = {
        "parity_spec": "parity-spec.json",
        "provenance": "provenance.json",
        "normalized_turns": "normalized-turns.jsonl",
        "comparison": "comparison.json",
        "summary": "summary.json",
    }

    def __init__(self, state_root: Path):
        self._state_root = Path(state_root).resolve()

    def list_item(self, run: RunRecord) -> dict[str, Any]:
        config = self._config_from_mapping(run.get("options"))
        response = self._base_response(run, config=config, ready=False)
        if str(run.get("status", "")) in {"queued", "running"}:
            return response.model_dump()
        try:
            artifacts = self._read_artifacts(run)
            return self._base_response(
                run,
                config=artifacts.config,
                ready=True,
                artifacts=artifacts,
            ).model_dump()
        except AgentRuntimeParityArtifactUnavailable:
            return response.model_dump()

    def detail(self, run: RunRecord) -> dict[str, Any]:
        if str(run.get("status", "")) in {"queued", "running"}:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity artifacts are not ready while the run is active"
            )
        artifacts = self._read_artifacts(run)
        return AgentRuntimeParityDetailResponse(
            **self._base_response(
                run,
                config=artifacts.config,
                ready=True,
                artifacts=artifacts,
            ).model_dump(),
            checks=artifacts.checks,
            comparability_checks=artifacts.comparability_checks,
            cleanup=artifacts.cleanup,
            provenance=artifacts.provenance,
            rounds=artifacts.rounds,
            turns=artifacts.turns,
            preflight_error=artifacts.preflight_error,
        ).model_dump()

    def _base_response(
        self,
        run: RunRecord,
        *,
        config: AgentRuntimeParityConfigResponse,
        ready: bool,
        artifacts: _ParityArtifacts | None = None,
    ) -> AgentRuntimeParityListItemResponse:
        return AgentRuntimeParityListItemResponse(
            run_id=str(run.get("run_id", "")),
            run_status=str(run.get("status", "")),
            created_at=str(run.get("created_at", "")),
            finished_at=str(run.get("finished_at", "")),
            ready=ready,
            config=config,
            passed=artifacts.passed if artifacts else None,
            inputs_comparable=artifacts.inputs_comparable if artifacts else None,
            cleanup_complete=artifacts.cleanup_complete if artifacts else None,
            rounds_requested=artifacts.rounds_requested if artifacts else None,
            rounds_completed=artifacts.rounds_completed if artifacts else None,
            rounds_passed=artifacts.rounds_passed if artifacts else None,
            artifact_digests=artifacts.artifact_digests if artifacts else None,
        )

    def _read_artifacts(self, run: RunRecord) -> _ParityArtifacts:
        run_id = str(run.get("run_id", "")).strip()
        artifact_run_id = self._artifact_run_id(run_id)
        root = self._artifact_root(run, artifact_run_id)
        spec, spec_sha256 = self._read_signed_json(
            root / self._ARTIFACT_NAMES["parity_spec"]
        )
        provenance, provenance_sha256 = self._read_signed_json(
            root / self._ARTIFACT_NAMES["provenance"]
        )
        comparison, comparison_sha256 = self._read_signed_json(
            root / self._ARTIFACT_NAMES["comparison"]
        )
        summary, summary_sha256 = self._read_signed_json(
            root / self._ARTIFACT_NAMES["summary"]
        )
        normalized_turns, normalized_turns_sha256 = self._read_jsonl(
            root / self._ARTIFACT_NAMES["normalized_turns"]
        )
        self._validate_bundle(
            artifact_run_id=artifact_run_id,
            spec=spec,
            spec_sha256=spec_sha256,
            provenance=provenance,
            provenance_sha256=provenance_sha256,
            normalized_turns=normalized_turns,
            normalized_turns_sha256=normalized_turns_sha256,
            comparison=comparison,
            comparison_sha256=comparison_sha256,
            summary=summary,
        )
        try:
            config = AgentRuntimeParityConfigResponse.model_validate(
                {
                    "prompt_key": self._string(spec["requested_inputs"], "prompt_key"),
                    "persona_key": self._string(
                        spec["requested_inputs"], "persona_key"
                    ),
                    "legacy_model": self._string(
                        spec["requested_inputs"]["legacy"], "model"
                    ),
                    "legacy_embedding": self._string(
                        spec["requested_inputs"]["legacy"], "embedding"
                    ),
                    "native_conversation_model": self._string(
                        spec["requested_inputs"]["native"], "conversation_model"
                    ),
                    "native_reviewer_model": self._string(
                        spec["requested_inputs"]["native"], "reviewer_model"
                    ),
                    "native_embedding_model": self._string(
                        spec["requested_inputs"]["native"], "embedding_model"
                    ),
                    "rounds": self._integer(spec["controls"], "rounds"),
                    "timeout_seconds": self._number(
                        spec["controls"], "timeout_seconds"
                    ),
                    "retry_count": self._integer(spec["controls"], "retry_count"),
                }
            )
            checks = self._boolean_mapping(comparison, "checks")
            comparability = self._mapping(comparison, "comparability")
            comparability_checks = self._boolean_mapping(comparability, "checks")
            cleanup = self._cleanup_response(self._mapping(comparison, "cleanup"))
            rounds = self._rounds(self._list(comparison, "rounds"))
            turns = self._turns(normalized_turns)
            provenance_response = self._provenance_response(provenance, comparability)
            preflight_error = self._safe_error(comparison.get("preflight_error"))
            artifact_digests = AgentRuntimeParityArtifactDigestsResponse(
                parity_spec_sha256=spec_sha256,
                provenance_sha256=provenance_sha256,
                normalized_turns_sha256=normalized_turns_sha256,
                comparison_sha256=comparison_sha256,
                summary_sha256=summary_sha256,
                evidence_sha256=self._evidence_sha256(
                    spec_sha256,
                    provenance_sha256,
                    normalized_turns_sha256,
                    comparison_sha256,
                    summary_sha256,
                ),
            )
            return _ParityArtifacts(
                config=config,
                passed=self._boolean(summary, "pass"),
                inputs_comparable=self._boolean(summary, "inputs_comparable"),
                cleanup_complete=self._boolean(summary, "cleanup_complete"),
                rounds_requested=self._integer(summary, "rounds_requested"),
                rounds_completed=self._integer(summary, "rounds_completed"),
                rounds_passed=self._integer(summary, "rounds_passed"),
                artifact_digests=artifact_digests,
                checks=checks,
                comparability_checks=comparability_checks,
                cleanup=cleanup,
                provenance=provenance_response,
                rounds=rounds,
                turns=turns,
                preflight_error=preflight_error,
            )
        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity artifacts have an invalid evidence shape"
            ) from exc

    def _validate_bundle(
        self,
        *,
        artifact_run_id: str,
        spec: Mapping[str, Any],
        spec_sha256: str,
        provenance: Mapping[str, Any],
        provenance_sha256: str,
        normalized_turns: list[Mapping[str, Any]],
        normalized_turns_sha256: str,
        comparison: Mapping[str, Any],
        comparison_sha256: str,
        summary: Mapping[str, Any],
    ) -> None:
        for artifact, expected_kind in (
            (spec, "agent-runtime-parity-spec"),
            (provenance, "agent-runtime-parity-provenance"),
            (comparison, "agent-runtime-parity-comparison"),
            (summary, "agent-runtime-parity-summary"),
        ):
            if (
                artifact.get("schema_version") != 1
                or artifact.get("kind") != expected_kind
                or artifact.get("run_id") != artifact_run_id
            ):
                raise AgentRuntimeParityArtifactUnavailable(
                    "Agent-runtime parity artifacts do not bind to this Test Center run"
                )
        if provenance.get("parity_spec_sha256") != spec_sha256:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity provenance does not match its parity spec"
            )
        if provenance.get("normalized_turns_sha256") != normalized_turns_sha256:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity provenance does not match normalized turns"
            )
        self._validate_source_identity(provenance)
        comparison_inputs = self._mapping(comparison, "artifact_inputs")
        summary_inputs = self._mapping(summary, "artifact_inputs")
        expected_comparison_inputs = {
            "parity_spec_sha256": spec_sha256,
            "provenance_sha256": provenance_sha256,
            "normalized_turns_sha256": normalized_turns_sha256,
        }
        if any(
            comparison_inputs.get(key) != value
            for key, value in expected_comparison_inputs.items()
        ):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity comparison does not match its evidence artifacts"
            )
        if any(
            summary_inputs.get(key) != value
            for key, value in {
                **expected_comparison_inputs,
                "comparison_sha256": comparison_sha256,
            }.items()
        ):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity summary does not match its evidence artifacts"
            )
        checks = self._canonical_boolean_mapping(
            comparison,
            "checks",
            self._COMPARISON_CHECKS,
            "comparison",
        )
        if comparison.get("pass") is not all(checks.values()):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity comparison pass state does not match checks"
            )
        if summary.get("pass") is not comparison.get("pass"):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity summary pass state does not match comparison"
            )
        if summary.get("inputs_comparable") is not self._boolean(
            self._mapping(comparison, "comparability"), "pass"
        ) or summary.get("cleanup_complete") is not self._boolean(
            self._mapping(comparison, "cleanup"), "completed"
        ):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity summary signals do not match comparison evidence"
            )
        comparability = self._mapping(comparison, "comparability")
        preflight_completed = checks["preflight_completed"]
        if preflight_completed:
            self._canonical_boolean_mapping(
                comparability,
                "checks",
                self._COMPARABILITY_CHECKS,
                "comparability",
            )
        rounds = self._list(comparison, "rounds")
        expected_rounds = self._integer(self._mapping(spec, "controls"), "rounds")
        if expected_rounds < 1:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity requested round count is invalid"
            )
        passed_rounds = sum(
            1
            for round_ in rounds
            if isinstance(round_, Mapping) and round_.get("pass") is True
        )
        if preflight_completed:
            self._validate_rounds(
                rounds,
                expected_rounds=expected_rounds,
                require_exact_coverage=True,
            )
            self._validate_completed_preflight_turn_engines(
                normalized_turns,
                expected_rounds=expected_rounds,
            )
        else:
            self._validate_preflight_failure(
                rounds=rounds,
                normalized_turns=normalized_turns,
                normalized_turns_sha256=normalized_turns_sha256,
                preflight_error=comparison.get("preflight_error"),
            )
        if (
            self._integer(summary, "rounds_completed") != len(rounds)
            or self._integer(summary, "rounds_passed") != passed_rounds
            or self._integer(summary, "rounds_requested") != expected_rounds
        ):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity summary round counts do not match comparison evidence"
            )

    def _validate_source_identity(self, provenance: Mapping[str, Any]) -> None:
        try:
            source = self._mapping(provenance, "source_identity")
            revision = self._string(source, "revision")
            fingerprint = self._string(source, "fingerprint")
            self._boolean(source, "dirty")
        except ValueError as exc:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity provenance source identity is invalid"
            ) from exc
        if not self._GIT_REVISION_PATTERN.fullmatch(
            revision
        ) or not self._SHA256_PATTERN.fullmatch(fingerprint):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity provenance source identity is invalid"
            )

    def _validate_rounds(
        self,
        rounds: list[Any],
        *,
        expected_rounds: int,
        require_exact_coverage: bool,
    ) -> None:
        round_numbers: list[int] = []
        for round_ in rounds:
            if not isinstance(round_, Mapping):
                raise AgentRuntimeParityArtifactUnavailable(
                    "Agent-runtime parity comparison round is invalid"
                )
            try:
                round_number = self._integer(round_, "round")
                legacy_score = self._mapping(round_, "legacy_score")
                native_score = self._mapping(round_, "native_score")
                legacy_checks = self._canonical_boolean_mapping(
                    legacy_score,
                    "checks",
                    self._LEGACY_SCORE_CHECKS,
                    "legacy round score",
                )
                native_checks = self._canonical_boolean_mapping(
                    native_score,
                    "checks",
                    self._NATIVE_SCORE_CHECKS,
                    "native round score",
                )
                legacy_passed = self._boolean(legacy_score, "pass")
                native_passed = self._boolean(native_score, "pass")
                paired_passed = self._boolean(round_, "pass")
            except ValueError as exc:
                raise AgentRuntimeParityArtifactUnavailable(
                    "Agent-runtime parity comparison round is invalid"
                ) from exc
            if legacy_passed is not all(
                legacy_checks.values()
            ) or native_passed is not all(native_checks.values()):
                raise AgentRuntimeParityArtifactUnavailable(
                    "Agent-runtime parity round pass state does not match engine checks"
                )
            if paired_passed is not (legacy_passed and native_passed):
                raise AgentRuntimeParityArtifactUnavailable(
                    "Agent-runtime parity paired round does not match engine outcomes"
                )
            round_numbers.append(round_number)
        if require_exact_coverage and set(round_numbers) != set(
            range(1, expected_rounds + 1)
        ):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity comparison must contain exactly the requested distinct rounds"
            )
        if len(round_numbers) != len(set(round_numbers)):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity comparison rounds are duplicated"
            )

    def _validate_preflight_failure(
        self,
        *,
        rounds: list[Any],
        normalized_turns: list[Mapping[str, Any]],
        normalized_turns_sha256: str,
        preflight_error: object,
    ) -> None:
        if rounds:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity preflight failure must not contain rounds"
            )
        if normalized_turns:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity preflight failure must not contain normalized turns"
            )
        if normalized_turns_sha256 != self._EMPTY_FILE_SHA256:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity preflight failure normalized-turns artifact must be empty"
            )
        try:
            safe_error = self._safe_error(preflight_error)
        except ValueError as exc:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity preflight failure error is invalid"
            ) from exc
        if not safe_error:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity preflight failure must include a public error"
            )

    def _validate_completed_preflight_turn_engines(
        self,
        turns: list[Mapping[str, Any]],
        *,
        expected_rounds: int,
    ) -> None:
        try:
            engine_rounds = {
                (self._string(turn, "engine"), self._integer(turn, "round"))
                for turn in turns
            }
        except ValueError as exc:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity normalized turns are invalid"
            ) from exc
        expected = {
            (engine, round_number)
            for engine in self._REQUIRED_ENGINES
            for round_number in range(1, expected_rounds + 1)
        }
        if engine_rounds != expected:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity normalized turns are missing a required engine or round"
            )

    def _artifact_root(self, run: RunRecord, artifact_run_id: str) -> Path:
        output_dir = Path(str(run.get("output_dir", ""))).resolve()
        root = (output_dir / artifact_run_id).resolve()
        if (
            not output_dir.is_relative_to(self._state_root)
            or not output_dir.is_dir()
            or not root.is_relative_to(output_dir)
            or root.parent != output_dir
            or not root.is_dir()
        ):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity output directory is unavailable"
            )
        return root

    @staticmethod
    def _artifact_run_id(run_id: str) -> str:
        normalized = run_id.strip().lower()
        if not normalized:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity Test Center run ID is invalid"
            )
        return f"parity-{normalized}"

    def _read_signed_json(self, path: Path) -> tuple[dict[str, Any], str]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AgentRuntimeParityArtifactUnavailable(
                f"Agent-runtime parity artifact is unreadable: {path.name}"
            ) from exc
        if not isinstance(payload, dict):
            raise AgentRuntimeParityArtifactUnavailable(
                f"Agent-runtime parity artifact is not an object: {path.name}"
            )
        artifact_sha256 = str(payload.pop("artifact_sha256", ""))
        expected_sha256 = self._canonical_sha256(payload)
        if artifact_sha256 != expected_sha256:
            raise AgentRuntimeParityArtifactUnavailable(
                f"Agent-runtime parity artifact digest is invalid: {path.name}"
            )
        return payload, artifact_sha256

    @staticmethod
    def _read_jsonl(path: Path) -> tuple[list[Mapping[str, Any]], str]:
        try:
            payload = path.read_bytes()
            rows = [
                json.loads(line)
                for line in payload.decode("utf-8").splitlines()
                if line.strip()
            ]
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity normalized-turns artifact is unreadable"
            ) from exc
        if any(not isinstance(row, Mapping) for row in rows):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity normalized-turns rows are invalid"
            )
        keys = [
            (row.get("engine"), row.get("round"), row.get("turn_index")) for row in rows
        ]
        if len(keys) != len(set(keys)):
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity normalized-turns rows are duplicated"
            )
        return rows, hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _canonical_sha256(payload: object) -> str:
        material = (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            + "\n"
        ).encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    @classmethod
    def _evidence_sha256(cls, *digests: str) -> str:
        return cls._canonical_sha256(
            {
                key: value
                for key, value in zip(
                    (
                        "parity_spec_sha256",
                        "provenance_sha256",
                        "normalized_turns_sha256",
                        "comparison_sha256",
                        "summary_sha256",
                    ),
                    digests,
                    strict=True,
                )
            }
        )

    @staticmethod
    def _mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
        value = payload.get(key)
        if not isinstance(value, Mapping):
            raise ValueError(f"{key} must be an object")
        return value

    @staticmethod
    def _list(payload: Mapping[str, Any], key: str) -> list[Any]:
        value = payload.get(key)
        if not isinstance(value, list):
            raise ValueError(f"{key} must be a list")
        return value

    @staticmethod
    def _string(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
        return value

    @staticmethod
    def _integer(payload: Mapping[str, Any], key: str) -> int:
        value = payload.get(key)
        if type(value) is not int:
            raise ValueError(f"{key} must be an integer")
        return value

    @staticmethod
    def _number(payload: Mapping[str, Any], key: str) -> float:
        value = payload.get(key)
        if type(value) not in {int, float}:
            raise ValueError(f"{key} must be a number")
        return float(value)

    @staticmethod
    def _boolean(payload: Mapping[str, Any], key: str) -> bool:
        value = payload.get(key)
        if type(value) is not bool:
            raise ValueError(f"{key} must be a boolean")
        return value

    @classmethod
    def _boolean_mapping(cls, payload: Mapping[str, Any], key: str) -> dict[str, bool]:
        mapping = cls._mapping(payload, key)
        if not mapping or any(type(value) is not bool for value in mapping.values()):
            raise ValueError(f"{key} must be a non-empty boolean mapping")
        return {str(name): bool(value) for name, value in mapping.items()}

    @classmethod
    def _canonical_boolean_mapping(
        cls,
        payload: Mapping[str, Any],
        key: str,
        expected_names: frozenset[str],
        artifact_section: str,
    ) -> dict[str, bool]:
        try:
            mapping = cls._boolean_mapping(payload, key)
        except ValueError as exc:
            raise AgentRuntimeParityArtifactUnavailable(
                f"Agent-runtime parity {artifact_section} check set is invalid"
            ) from exc
        if set(mapping) != expected_names:
            raise AgentRuntimeParityArtifactUnavailable(
                f"Agent-runtime parity {artifact_section} check set is incomplete or unexpected"
            )
        return mapping

    def _cleanup_response(
        self, cleanup: Mapping[str, Any]
    ) -> AgentRuntimeParityCleanupResponse:
        legacy = self._mapping(cleanup, "legacy")
        native = self._mapping(cleanup, "native")
        return AgentRuntimeParityCleanupResponse(
            completed=self._boolean(cleanup, "completed"),
            legacy_completed=self._boolean(legacy, "completed"),
            native_completed=self._boolean(native, "completed"),
            legacy_creation_indeterminate=self._boolean(
                legacy, "creation_indeterminate"
            ),
        )

    def _provenance_response(
        self,
        provenance: Mapping[str, Any],
        comparability: Mapping[str, Any],
    ) -> AgentRuntimeParityProvenanceResponse:
        source = self._mapping(provenance, "source_identity")
        native = self._mapping(provenance, "native")
        legacy = self._mapping(provenance, "legacy")
        health = self._optional_mapping(native.get("worker_health"))
        legacy_inputs = self._optional_mapping(legacy.get("inputs"))
        prompt = self._optional_mapping(legacy_inputs.get("prompt"))
        persona = self._optional_mapping(legacy_inputs.get("persona"))
        comparability_checks = self._boolean_mapping(comparability, "checks")
        return AgentRuntimeParityProvenanceResponse(
            source_revision=self._string(source, "revision"),
            source_dirty=self._boolean(source, "dirty"),
            source_fingerprint=self._string(source, "fingerprint"),
            native_worker_ready=self._optional_boolean(health, "worker_ready"),
            native_worker_build_matches=comparability_checks.get(
                "native_worker_build_matches_evaluator"
            ),
            prompt_content_sha256=self._optional_sha256(prompt, "content_sha256"),
            persona_content_sha256=self._optional_sha256(persona, "content_sha256"),
            fixture_sha256=self._optional_sha256(comparability, "fixture_sha256"),
        )

    def _rounds(self, rounds: list[Any]) -> list[AgentRuntimeParityRoundResponse]:
        response: list[AgentRuntimeParityRoundResponse] = []
        for item in rounds:
            if not isinstance(item, Mapping):
                raise ValueError("round must be an object")
            legacy_score = self._mapping(item, "legacy_score")
            native_score = self._mapping(item, "native_score")
            response.append(
                AgentRuntimeParityRoundResponse(
                    round=self._integer(item, "round"),
                    passed=self._boolean(item, "pass"),
                    legacy_passed=self._boolean(legacy_score, "pass"),
                    native_passed=self._boolean(native_score, "pass"),
                    legacy_checks=self._boolean_mapping(legacy_score, "checks"),
                    native_checks=self._boolean_mapping(native_score, "checks"),
                )
            )
        return response

    def _turns(
        self, turns: list[Mapping[str, Any]]
    ) -> list[AgentRuntimeParityTurnResponse]:
        response: list[AgentRuntimeParityTurnResponse] = []
        for item in turns:
            replies = item.get("assistant_replies")
            tools = item.get("tool_outcomes")
            events = item.get("run_events")
            memory = item.get("memory_outcome")
            if not isinstance(replies, list) or any(
                not isinstance(value, str) for value in replies
            ):
                raise ValueError("assistant_replies must be a string list")
            tool_names = [
                str(tool.get("name") or "")
                for tool in tools or []
                if isinstance(tool, Mapping) and str(tool.get("name") or "")
            ]
            event_types = [
                str(event.get("type") or "")
                for event in events or []
                if isinstance(event, Mapping) and str(event.get("type") or "")
            ]
            attempt = item.get("attempt_count")
            if attempt is not None and type(attempt) is not int:
                raise ValueError("attempt_count must be an integer or null")
            memory_changed = (
                memory.get("changed") if isinstance(memory, Mapping) else None
            )
            if memory_changed is not None and type(memory_changed) is not bool:
                raise ValueError("memory changed must be a boolean or null")
            response.append(
                AgentRuntimeParityTurnResponse(
                    engine=self._string(item, "engine"),
                    round=self._integer(item, "round"),
                    turn_index=self._integer(item, "turn_index"),
                    terminal_status=self._string(item, "terminal_status"),
                    user_content=self._string(item, "user_content"),
                    assistant_replies=list(replies),
                    attempt_count=attempt,
                    elapsed_seconds=self._number(item, "elapsed_seconds"),
                    tool_names=tool_names,
                    event_types=event_types,
                    memory_changed=memory_changed,
                )
            )
        return response

    @staticmethod
    def _optional_sha256(payload: Mapping[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"{key} must be a SHA-256")
        return value

    @staticmethod
    def _optional_mapping(value: object) -> Mapping[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise ValueError("optional evidence value must be an object or null")
        return value

    @staticmethod
    def _optional_boolean(payload: Mapping[str, Any], key: str) -> bool | None:
        value = payload.get(key)
        if value is None:
            return None
        if type(value) is not bool:
            raise ValueError(f"{key} must be a boolean when present")
        return value

    @staticmethod
    def _safe_error(value: object) -> dict[str, str] | None:
        if value is None:
            return None
        if not isinstance(value, Mapping):
            raise ValueError("preflight_error must be an object or null")
        # The runner already narrows errors to public class/code/status fields.
        # Retain only scalar values when presenting them through Test Center.
        return {
            str(key): str(item)
            for key, item in value.items()
            if isinstance(item, (str, int, float, bool))
        }

    @staticmethod
    def _config_from_mapping(value: object) -> AgentRuntimeParityConfigResponse:
        options = value if isinstance(value, Mapping) else {}
        config = dict(DEFAULT_AGENT_RUNTIME_PARITY_CONFIG)
        for key in config:
            if key in options and options[key] is not None:
                config[key] = options[key]
        try:
            return AgentRuntimeParityConfigResponse.model_validate(config)
        except ValidationError as exc:
            raise AgentRuntimeParityArtifactUnavailable(
                "Agent-runtime parity launch options are invalid"
            ) from exc
