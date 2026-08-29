from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class CleanupError(RuntimeError):
    pass


@dataclass(frozen=True)
class CleanupScope:
    run_id: str
    definition_keys: tuple[str, ...]
    subject_external_keys: tuple[str, ...]

    def validate(self) -> None:
        token = self.run_id.strip()
        if not token or (not self.definition_keys and not self.subject_external_keys):
            raise CleanupError(
                "cleanup scope must include a run-bound generated resource"
            )
        if any(not value.startswith(token) for value in self.definition_keys):
            raise CleanupError("definition cleanup scope is not bound to the run id")
        if any(not value.startswith(token) for value in self.subject_external_keys):
            raise CleanupError("subject cleanup scope is not bound to the run id")


@dataclass(frozen=True)
class RecoveryManifest:
    path: Path
    payload: dict[str, Any]


class ScopedPostgresCleanup:
    """Purge only generated v3 resources after recording an operator recovery manifest."""

    def __init__(
        self,
        *,
        database_url: str,
        output_dir: Path,
        execute: Callable[[str, tuple[tuple[str, ...], ...]], Any] | None = None,
    ) -> None:
        if not database_url.startswith(
            ("postgres://", "postgresql://", "postgresql+psycopg://")
        ):
            raise CleanupError("cleanup requires a PostgreSQL database URL")
        self.database_url = database_url
        self.output_dir = output_dir
        self._execute = execute

    def cleanup(self, scope: CleanupScope) -> RecoveryManifest:
        scope.validate()
        statements = _scoped_statements(scope)
        payload = {
            "schema_version": 1,
            "kind": "agent-runtime-v3-cleanup-recovery-manifest",
            "created_at": datetime.now(UTC).isoformat(),
            "status": "prepared",
            "database_target": _redacted_database_target(self.database_url),
            "scope": {
                "run_id": scope.run_id,
                "definition_keys": list(scope.definition_keys),
                "subject_external_keys": list(scope.subject_external_keys),
            },
            "statement_sha256": hashlib.sha256(
                "\n".join(statement for statement, _params in statements).encode()
            ).hexdigest(),
            "deletions": [],
        }
        path = self.output_dir / scope.run_id / "cleanup-recovery-manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_manifest(path, payload)
        try:
            if self._execute is None:
                results = self._execute_psycopg(statements)
                payload["deletions"].extend(_safe_result(result) for result in results)
            else:
                for statement, params in statements:
                    result = self._execute(statement, params)
                    payload["deletions"].append(_safe_result(result))
        except Exception as exc:
            payload["status"] = "failed"
            payload["error_type"] = type(exc).__name__
            _write_manifest(path, payload)
            raise CleanupError(
                "scoped cleanup failed; recovery manifest was preserved"
            ) from exc
        payload["status"] = "completed"
        payload["completed_at"] = datetime.now(UTC).isoformat()
        _write_manifest(path, payload)
        return RecoveryManifest(path=path, payload=payload)

    def _execute_psycopg(
        self, statements: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...]
    ) -> list[dict[str, int]]:
        try:
            import psycopg
        except ModuleNotFoundError as exc:
            raise CleanupError(
                "psycopg is required for live PostgreSQL cleanup"
            ) from exc
        with psycopg.connect(_psycopg_url(self.database_url)) as connection:
            with connection.cursor() as cursor:
                results = []
                for statement, params in statements:
                    cursor.execute(statement, _psycopg_params(params))
                    results.append({"rowcount": cursor.rowcount})
                return results


def _scoped_statements(
    scope: CleanupScope,
) -> tuple[tuple[str, tuple[tuple[str, ...], ...]], ...]:
    # Every statement begins from resources matched by both generated namespaces.
    target = """
WITH target_conversations AS (
    SELECT c.id
    FROM ade.conversations AS c
    JOIN ade.agent_definition_versions AS d ON d.id = c.agent_definition_version_id
    JOIN ade.memory_subjects AS s ON s.id = c.memory_subject_id
    WHERE d.definition_key = ANY(%s)
      AND s.external_key = ANY(%s)
      AND c.workspace_id = (
          SELECT id FROM ade.workspaces WHERE workspace_key = 'default'
      )
), target_runs AS (
    SELECT r.id FROM ade.runs AS r JOIN target_conversations AS c ON c.id = r.conversation_id
)
""".strip()
    target_facts = """
WITH target_subjects AS (
    SELECT id
    FROM ade.memory_subjects
    WHERE external_key = ANY(%s)
      AND workspace_id = (
          SELECT id FROM ade.workspaces WHERE workspace_key = 'default'
      )
), target_facts AS (
    SELECT id FROM ade.memory_facts WHERE subject_id IN (SELECT id FROM target_subjects)
), target_revisions AS (
    SELECT id FROM ade.memory_revisions WHERE fact_id IN (SELECT id FROM target_facts)
)
""".strip()
    conversation_params = (scope.definition_keys, scope.subject_external_keys)
    fact_params = (scope.subject_external_keys,)
    definition_params = (scope.definition_keys,)
    subject_params = (scope.subject_external_keys,)
    statements: list[tuple[str, tuple[tuple[str, ...], ...]]] = []
    if scope.definition_keys and scope.subject_external_keys:
        statements.extend(
            (
                (
                    target
                    + "\nDELETE FROM ade.outbox WHERE run_id IN (SELECT id FROM target_runs)",
                    conversation_params,
                ),
                (
                    target
                    + "\nDELETE FROM ade.run_events WHERE run_id IN (SELECT id FROM target_runs)",
                    conversation_params,
                ),
                (
                    target
                    + "\nDELETE FROM ade.run_attempts WHERE run_id IN (SELECT id FROM target_runs)",
                    conversation_params,
                ),
                (
                    target
                    + "\nDELETE FROM ade.conversation_leases WHERE run_id IN (SELECT id FROM target_runs)",
                    conversation_params,
                ),
                (
                    target
                    + "\nDELETE FROM ade.summary_sources WHERE summary_id IN (SELECT id FROM ade.conversation_summaries WHERE conversation_id IN (SELECT id FROM target_conversations))",
                    conversation_params,
                ),
                (
                    target
                    + "\nDELETE FROM ade.conversation_summaries WHERE conversation_id IN (SELECT id FROM target_conversations)",
                    conversation_params,
                ),
                (
                    target
                    + "\nDELETE FROM ade.messages WHERE conversation_id IN (SELECT id FROM target_conversations)",
                    conversation_params,
                ),
            )
        )
    if scope.subject_external_keys:
        statements.extend(
            (
                (
                    target_facts
                    + "\nDELETE FROM ade.memory_revision_sources WHERE revision_id IN (SELECT id FROM target_revisions)",
                    fact_params,
                ),
                (
                    target_facts
                    + "\nDELETE FROM ade.memory_revision_predecessors WHERE revision_id IN (SELECT id FROM target_revisions) OR predecessor_revision_id IN (SELECT id FROM target_revisions)",
                    fact_params,
                ),
                (
                    target_facts
                    + "\nDELETE FROM ade.memory_embeddings WHERE fact_id IN (SELECT id FROM target_facts)",
                    fact_params,
                ),
                (
                    target_facts
                    + "\nUPDATE ade.memory_facts SET current_revision_id = NULL WHERE id IN (SELECT id FROM target_facts)",
                    fact_params,
                ),
                (
                    target_facts
                    + "\nDELETE FROM ade.memory_revisions WHERE fact_id IN (SELECT id FROM target_facts)",
                    fact_params,
                ),
                (
                    target_facts
                    + "\nDELETE FROM ade.memory_facts WHERE id IN (SELECT id FROM target_facts)",
                    fact_params,
                ),
            )
        )
    if scope.definition_keys and scope.subject_external_keys:
        statements.extend(
            (
                (
                    target
                    + "\nDELETE FROM ade.runs WHERE id IN (SELECT id FROM target_runs)",
                    conversation_params,
                ),
                (
                    target
                    + "\nDELETE FROM ade.conversations WHERE id IN (SELECT id FROM target_conversations)",
                    conversation_params,
                ),
            )
        )
    if scope.definition_keys:
        statements.append(
            (
                """
DELETE FROM ade.agent_definition_versions
WHERE definition_key = ANY(%s)
  AND workspace_id = (
      SELECT id FROM ade.workspaces WHERE workspace_key = 'default'
  )
""".strip(),
                definition_params,
            ),
        )
    if scope.subject_external_keys:
        statements.extend(
            (
                (
                    """
DELETE FROM ade.memory_entities
WHERE subject_id IN (
    SELECT id
    FROM ade.memory_subjects
    WHERE external_key = ANY(%s)
      AND workspace_id = (
          SELECT id FROM ade.workspaces WHERE workspace_key = 'default'
      )
)
""".strip(),
                    subject_params,
                ),
                (
                    """
DELETE FROM ade.memory_subjects
WHERE external_key = ANY(%s)
  AND workspace_id = (
      SELECT id FROM ade.workspaces WHERE workspace_key = 'default'
  )
""".strip(),
                    subject_params,
                ),
            )
        )
    return tuple(statements)


def _safe_result(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            str(key): value[key]
            for key in value
            if isinstance(value[key], (str, int, float, bool, type(None)))
        }
    return {"result_type": type(value).__name__}


def _redacted_database_target(database_url: str) -> str:
    parsed = urlsplit(database_url)
    host = parsed.hostname or "unknown"
    database = parsed.path.rsplit("/", maxsplit=1)[-1] or "unknown"
    return f"{parsed.scheme}://{host}/{database}"


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _psycopg_params(
    params: tuple[tuple[str, ...], ...],
) -> tuple[list[str], ...]:
    # Psycopg maps lists to PostgreSQL arrays; tuples are composite records.
    return tuple(list(values) for values in params)


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
