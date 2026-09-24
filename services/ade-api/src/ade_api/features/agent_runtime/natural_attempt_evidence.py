"""Opt-in, isolated evaluation artifacts for natural-memory attempts.

Only ADE-selected visible inputs and typed decisions are retained. Authentication,
provider wire bodies, private reasoning, and raw exceptions never enter this path.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.platform.project_paths import PROJECT_ROOT

from .errors import RuntimeNotReady
from .context import BuiltContext
from .context import estimate_tokens
from .persistence.metadata import (
    conversations,
    memory_revisions,
    memory_subjects,
    messages,
    run_attempts,
    runs,
)


ARTIFACT_ROOT = (
    PROJECT_ROOT
    / "workflows/evals/character_memory_dev/outputs/natural-memory-attempts"
)
_ISOLATED_DATABASE = re.compile(r"^ade_[a-z0-9_]*_test_[a-z0-9]+$")
_MAX_ARTIFACT_BYTES = 2_000_000


def capture_allowed(*, database_url: str, runtime_mode: str, purpose: str) -> bool:
    if os.getenv("ADE_NATURAL_MEMORY_CAPTURE") != "1":
        return False
    url = make_url(database_url)
    if (
        runtime_mode != "development"
        or purpose != "evaluation"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or not _ISOLATED_DATABASE.fullmatch(url.database or "")
    ):
        raise RuntimeNotReady(
            "Natural-memory evidence capture requires an isolated local evaluation database"
        )
    return True


def start_natural_capture(
    *,
    database_url: str,
    runtime_mode: str,
    purpose: str,
    run_id: str,
    attempt: int,
    policy_binding: str,
) -> NaturalAttemptEvidence | None:
    if not capture_allowed(
        database_url=database_url, runtime_mode=runtime_mode, purpose=purpose
    ):
        return None
    return NaturalAttemptEvidence(
        run_id=run_id, attempt=attempt, policy_binding=policy_binding
    )


@dataclass
class NaturalAttemptEvidence:
    run_id: str
    attempt: int
    policy_binding: str
    generation: dict[str, Any] | None = None
    generation_requests: list[dict[str, Any]] = field(default_factory=list)
    compaction_request: dict[str, Any] | None = None
    compaction_result: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    candidate_visible_reply: str | None = None
    reviewer_request: dict[str, Any] | None = None
    reviewer_decision: dict[str, Any] | None = None
    embedding_stage: dict[str, Any] | None = None
    provider_events: list[dict[str, Any]] = field(default_factory=list)
    excluded_fields: tuple[str, ...] = field(
        default=(
            "authentication_headers",
            "provider_wire_bodies",
            "private_reasoning",
            "raw_exceptions",
        )
    )

    def capture_generation(
        self,
        *,
        messages_for_model: list[dict[str, Any]],
        source_messages: tuple[dict[str, Any], ...],
        section_tokens: dict[str, int],
        retrieved_fact_ids: list[str],
        omitted_message_ids: list[str],
        estimated_input_tokens: int,
        input_limit: int,
    ) -> None:
        self.generation = {
            "messages": messages_for_model,
            "source_messages": [
                {"id": item["id"], "role": item["role"], "content": item["content"]}
                for item in source_messages
            ],
            "section_tokens": section_tokens,
            "retrieved_fact_ids": retrieved_fact_ids,
            "omitted_message_ids": omitted_message_ids,
            "estimated_input_tokens": estimated_input_tokens,
            "input_limit": input_limit,
        }

    def capture_candidate(self, text: str, tool_evidence: list[dict[str, Any]]) -> None:
        self.candidate_visible_reply = text
        self.tools = tool_evidence

    def capture_generation_request(self, payload: dict[str, Any]) -> None:
        messages_for_model = []
        for message in payload.get("messages", []):
            visible = {
                key: message[key]
                for key in ("role", "content", "name", "tool_call_id")
                if key in message
            }
            if "tool_calls" in message:
                visible["tool_calls"] = [
                    {
                        "id": call.get("id"),
                        "type": call.get("type"),
                        "function": {
                            "name": (call.get("function") or {}).get("name"),
                            "arguments": (call.get("function") or {}).get("arguments"),
                        },
                    }
                    for call in message["tool_calls"]
                ]
            messages_for_model.append(visible)
        retained = {
            "model": payload.get("model"),
            "messages": messages_for_model,
            "max_tokens": payload.get("max_tokens"),
            "tools": payload.get("tools", []),
            "tool_choice": payload.get("tool_choice"),
        }
        retained["serialized_visible_token_estimate"] = estimate_tokens(
            json.dumps(retained, ensure_ascii=False, separators=(",", ":"))
        )
        self.generation_requests.append(retained)

    def capture_compaction_request(self, payload: dict[str, Any]) -> None:
        retained = {
            "model": payload.get("model"),
            "messages": payload.get("messages"),
            "max_tokens": payload.get("max_tokens"),
            "response_format": payload.get("response_format"),
        }
        retained["serialized_visible_token_estimate"] = estimate_tokens(
            json.dumps(retained, ensure_ascii=False, separators=(",", ":"))
        )
        self.compaction_request = retained

    def capture_compaction_result(self, result: Any) -> None:
        self.compaction_result = {
            "summary_content": result.content,
            "summary_through_sequence": result.plan.through_sequence,
            "source_message_ids": list(result.plan.source_message_ids),
            "provider_request_id": result.provider_request_id,
            "usage": result.usage,
        }

    def capture_reviewer_request(self, payload: dict[str, Any]) -> None:
        self.reviewer_request = {
            "model": payload["model"],
            "messages": payload["messages"],
            "max_tokens": payload["max_tokens"],
            "response_format": payload.get("response_format"),
            "serialized_visible_token_estimate": estimate_tokens(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            ),
        }

    def capture_reviewer_decision(self, decision: Any) -> None:
        self.reviewer_decision = decision.model_dump(mode="json")

    def capture_embeddings(self, count: int, dimensions: int) -> None:
        self.embedding_stage = {"count": count, "dimensions": dimensions}

    def capture_provider_events(self, events: tuple[Any, ...]) -> None:
        self.provider_events = [
            {"event_type": event.event_type, "payload": event.payload}
            for event in events
        ]


def capture_context(
    evidence: NaturalAttemptEvidence | None,
    *,
    context: BuiltContext,
    source_messages: tuple[dict[str, Any], ...],
    input_limit: int,
) -> None:
    if evidence is None:
        return
    evidence.capture_generation(
        messages_for_model=context.messages,
        source_messages=source_messages,
        section_tokens=context.section_tokens,
        retrieved_fact_ids=context.retrieved_fact_ids,
        omitted_message_ids=context.omitted_message_ids,
        estimated_input_tokens=context.estimated_input_tokens,
        input_limit=input_limit,
    )


def classify_outcome(
    *,
    run_status: str | None,
    attempt_status: str | None,
    assistant_message_ids: list[str],
    revision_ids: list[str],
) -> str:
    if (
        attempt_status == "succeeded"
        and run_status == "succeeded"
        and len(assistant_message_ids) == 1
    ):
        return "committed"
    if attempt_status in {"failed", "cancelled"}:
        if run_status in {"failed", "cancelled"} and not (
            assistant_message_ids or revision_ids
        ):
            return "confirmed_rejection"
        if run_status == "succeeded":
            return "rejected_prior_attempt"
    return "unconfirmed"


async def retain_attempt_evidence(
    engine: AsyncEngine, evidence: NaturalAttemptEvidence
) -> Path:
    """Read authoritative state after finalization, then atomically retain once."""

    UUID(evidence.run_id)
    if evidence.attempt < 1 or ARTIFACT_ROOT.is_symlink():
        raise RuntimeError("Natural-memory evidence path is not safe")

    async with engine.connect() as connection:
        run = (
            (await connection.execute(select(runs).where(runs.c.id == evidence.run_id)))
            .mappings()
            .one_or_none()
        )
        attempt = (
            (
                await connection.execute(
                    select(run_attempts).where(
                        run_attempts.c.run_id == evidence.run_id,
                        run_attempts.c.attempt_number == evidence.attempt,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        assistant_ids = list(
            (
                await connection.execute(
                    select(messages.c.id).where(
                        messages.c.run_id == evidence.run_id,
                        messages.c.role == "assistant",
                    )
                )
            ).scalars()
        )
        revision_ids = list(
            (
                await connection.execute(
                    select(memory_revisions.c.id).where(
                        memory_revisions.c.run_id == evidence.run_id
                    )
                )
            ).scalars()
        )
        generation = None
        if run is not None:
            subject_id = await connection.scalar(
                select(conversations.c.memory_subject_id).where(
                    conversations.c.id == run["conversation_id"]
                )
            )
            if subject_id is not None:
                generation = await connection.scalar(
                    select(memory_subjects.c.memory_generation).where(
                        memory_subjects.c.id == subject_id
                    )
                )
    run_status = str(run["status"]) if run is not None else None
    attempt_status = str(attempt["status"]) if attempt is not None else None
    outcome = classify_outcome(
        run_status=run_status,
        attempt_status=attempt_status,
        assistant_message_ids=[str(value) for value in assistant_ids],
        revision_ids=[str(value) for value in revision_ids],
    )
    provider_counts: dict[str, int] = {}
    for event in evidence.provider_events:
        if event["event_type"] == "model.request.started":
            stage = str(event["payload"]["stage"])
            provider_counts[stage] = provider_counts.get(stage, 0) + 1
    payload = {
        "schema_version": 1,
        "run_id": evidence.run_id,
        "attempt": evidence.attempt,
        "policy_binding": evidence.policy_binding,
        "generation": evidence.generation or {"stage": "absent"},
        "generation_requests": (
            evidence.generation_requests
            if evidence.generation_requests
            else {"stage": "absent"}
        ),
        "compaction_request": evidence.compaction_request or {"stage": "absent"},
        "compaction_result": evidence.compaction_result or {"stage": "absent"},
        "tools": evidence.tools if evidence.tools is not None else {"stage": "absent"},
        "candidate_visible_reply": (
            evidence.candidate_visible_reply
            if evidence.candidate_visible_reply is not None
            else {"stage": "absent"}
        ),
        "reviewer_request": evidence.reviewer_request or {"stage": "absent"},
        "reviewer_decision": evidence.reviewer_decision or {"stage": "absent"},
        "embedding_stage": evidence.embedding_stage or {"stage": "absent"},
        "provider_events": evidence.provider_events,
        "provider_request_counts": provider_counts,
        "terminal_readback": {
            "outcome": outcome,
            "candidate_commit": (
                "committed_visible_message"
                if outcome == "committed"
                else "uncommitted_undelivered"
                if outcome in {"confirmed_rejection", "rejected_prior_attempt"}
                else "unconfirmed"
            ),
            "run_status": run_status,
            "attempt_status": attempt_status,
            "assistant_message_ids": [str(value) for value in assistant_ids],
            "revision_ids": [str(value) for value in revision_ids],
            "accepted_memory_generation": (
                int(run["accepted_memory_generation"]) if run is not None else None
            ),
            "observed_memory_generation": (
                int(generation) if generation is not None else None
            ),
        },
        "excluded_fields": evidence.excluded_fields,
    }
    serialized = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")
    if len(serialized) > _MAX_ARTIFACT_BYTES:
        raise RuntimeError("Natural-memory evidence exceeds its artifact limit")
    directory = ARTIFACT_ROOT / evidence.run_id
    if directory.is_symlink():
        raise RuntimeError("Natural-memory evidence run path is not safe")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"attempt-{evidence.attempt:03d}.json"
    if target.exists():
        if target.read_bytes() != serialized:
            raise RuntimeError("Natural-memory evidence attempt already differs")
        return target
    temporary = directory / f".attempt-{evidence.attempt:03d}-{os.getpid()}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, target)
        except FileExistsError:
            if target.read_bytes() != serialized:
                raise RuntimeError(
                    "Natural-memory evidence attempt already differs"
                ) from None
    finally:
        if temporary.exists():
            temporary.unlink()
    return target
