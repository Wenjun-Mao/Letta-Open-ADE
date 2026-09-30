"""Runtime-owned PC-11 fixtures and independent full persistence observation."""

import json
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.engine import make_url

from ade_api.features.agent_runtime.persistence.metadata import (
    memory_entities,
    memory_facts,
    memory_revisions,
    memory_revision_sources,
    memory_revision_predecessors,
    memory_subjects,
)
from ade_api.features.agent_runtime.router_transport import RouterTransport
from ade_api.features.agent_runtime.history_ranking import document_text
from workflows.evals.character_memory_dev.story_continuity.baseline import (
    expected_catalog,
    validate_catalog,
)


def require_owned_database(url: str) -> None:
    parsed = make_url(url)
    if not (
        parsed.drivername == "postgresql+psycopg"
        and parsed.host in {"localhost", "127.0.0.1", "::1"}
        and parsed.username == "ade_owner"
        and parsed.password is None
        and re.fullmatch(r"ade_history_test_[0-9a-f]{8,}", parsed.database or "")
    ):
        raise ValueError("Explicit disposable passwordless loopback database required")


async def full_state(engine, subject_id: str) -> dict:
    async with engine.connect() as connection:
        await connection.execution_options(isolation_level="REPEATABLE READ")

        async def rows(table, condition):
            result = (
                await connection.execute(select(table).where(condition))
            ).mappings()
            values = json.loads(
                json.dumps(
                    [dict(row) for row in result],
                    default=lambda value: (
                        value.isoformat() if isinstance(value, datetime) else str(value)
                    ),
                )
            )
            return sorted(
                values,
                key=lambda row: json.dumps(
                    row, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                ),
            )

        revisions = select(memory_revisions.c.id).where(
            memory_revisions.c.subject_id == subject_id
        )
        return {
            "facts": await rows(memory_facts, memory_facts.c.subject_id == subject_id),
            "entities": await rows(
                memory_entities, memory_entities.c.subject_id == subject_id
            ),
            "revisions": await rows(
                memory_revisions, memory_revisions.c.subject_id == subject_id
            ),
            "sources": await rows(
                memory_revision_sources,
                memory_revision_sources.c.revision_id.in_(revisions),
            ),
            "predecessors": await rows(
                memory_revision_predecessors,
                memory_revision_predecessors.c.revision_id.in_(revisions),
            ),
            "generation": await connection.scalar(
                select(memory_subjects.c.memory_generation).where(
                    memory_subjects.c.id == subject_id
                )
            ),
        }


class ScriptedRouter(RouterTransport):
    """Every RouterTransport dispatch is replaced, including catalog/embedding.

    Catalog identities describe tested configuration, NOT actual model execution.
    No super dispatch or external fallback is available.
    """

    def __init__(self):
        super().__init__(base_url="http://offline.invalid")
        object.__setattr__(self, "reply", "")
        object.__setattr__(self, "reject", False)
        object.__setattr__(self, "packets", [])
        object.__setattr__(self, "vectors", {})

    def bind_document(self, user: str, assistant: str, *, preferred: bool):
        # Exact scripted fixture vectors, not a semantic rule or ranking-quality
        # test. This makes source admission deterministic with the real ranker.
        key = document_text({"user": user, "assistant": assistant})
        self.vectors[key] = ([1.0, 0.0] if preferred else [0.0, 1.0]) + [0.0] * 1022

    def script(self, reply: str, *, reject: bool = False):
        object.__setattr__(self, "reply", reply)
        object.__setattr__(self, "reject", reject)

    async def _request(self, path, payload, *, timeout_seconds, method="POST"):
        self.packets.append({"path": path, "payload": payload})
        if path == "/router/model-catalog":
            catalog = expected_catalog()
            validate_catalog(catalog)
            return catalog
        if path == "/embeddings":
            return {
                "data": [
                    {
                        "index": i,
                        "embedding": self.vectors.get(text, [1.0] + [0.0] * 1023),
                    }
                    for i, text in enumerate(payload["input"])
                ]
            }
        if path != "/chat/completions":
            raise AssertionError("Unknown fake-router operation; no provider fallback")
        review = bool(payload.get("response_format"))
        # Deliberately invalid reviewer output tests a real failed attempt,
        # not a hand-inserted failed row or a fictional semantic veto.
        content = (
            ("{}" if self.reject else json.dumps({"decisions": []}))
            if review
            else self.reply
        )
        return {
            "id": "scripted-pc11",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
        }
