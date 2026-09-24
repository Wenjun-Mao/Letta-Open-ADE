"""Provision one isolated Agent Studio browser fixture with a fake router binding."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url

from ade_api.features.agent_runtime.agent_studio_sessions import PurposeSessionService
from ade_api.features.agent_runtime.contracts import (
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.deployments import resolve_deployment
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)

from .offline_natural_router import _catalog


class FakeDefinitions:
    def __init__(self, *, policy_binding: str) -> None:
        self.catalog = _catalog()
        self.policy_binding = policy_binding

    async def prepare(self, request, *, purpose):
        if purpose != "agent_studio":
            raise ValueError("browser fixture requires Agent Studio purpose")
        snapshots = [
            resolve_deployment(
                self.catalog,
                route_alias=alias,
                role=role,
                mode="development",
            ).as_snapshot()
            for role, alias in (
                ("conversation", request.model_key),
                ("reviewer", request.reviewer_model_key),
                ("retriever", request.embedding_model_key),
            )
        ]
        return {
            "definition_key": request.definition_key,
            "name": request.name,
            "model_key": request.model_key,
            "reviewer_model_key": request.reviewer_model_key,
            "embedding_model_key": request.embedding_model_key,
            "prompt_key": request.prompt_key,
            "prompt_sha256": "a" * 64,
            "prompt_content": "You are a careful companion. Scripted offline browser fixture.",
            "persona_key": request.persona_key,
            "persona_sha256": "b" * 64,
            "persona_content": "Lin Xiaotang",
            "tool_names": [],
            "memory_policy_version": self.policy_binding,
            "qualification_state": "unqualified",
            "deployment_snapshot": snapshots,
        }


async def provision(
    database_url: str, *, existing_subject_id: str | None = None
) -> dict:
    url = make_url(database_url)
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or url.username != "ade_owner"
        or url.password is not None
        or not re.fullmatch(r"ade_m2_memory_test_[0-9a-f]{8,}", url.database or "")
    ):
        raise ValueError("browser fixture requires a passwordless isolated loopback DB")
    engine = create_persistence_engine(database_url)
    token = uuid4().hex[:12]
    try:
        old_readonly = existing_subject_id is not None
        sessions = PurposeSessionService(
            database=RuntimeDatabase(engine),
            definitions=FakeDefinitions(
                policy_binding=(
                    "typed-user-facts-v1"
                    if old_readonly
                    else "natural-user-assertions-v4-b"
                )
            ),
            purpose="agent_studio",
            session_namespace=(
                "natural-browser-old-policy"
                if old_readonly
                else "natural-browser-fixture"
            ),
        )
        result = await sessions.create(
            CreateAgentStudioSessionRequest(
                idempotency_key=f"natural-browser-{token}",
                title=(
                    "FAKE ROUTER — archived old-policy read-only conversation"
                    if old_readonly
                    else "FAKE ROUTER — natural memory browser journey"
                ),
                new_definition=CreateAgentDefinitionRequest(
                    definition_key=f"natural_browser_{token}",
                    name=(
                        "FAKE ROUTER old policy"
                        if old_readonly
                        else "FAKE ROUTER natural memory"
                    ),
                    model_key="fake::conversation",
                    reviewer_model_key="fake::reviewer",
                    embedding_model_key="fake::retriever",
                    tool_names=[],
                ),
                memory_subject_id=existing_subject_id,
                new_subject=(
                    None
                    if old_readonly
                    else CreateMemorySubjectRequest(
                        external_key=f"natural-browser-{token}",
                        display_name="Synthetic browser subject",
                    )
                ),
            )
        )
        if old_readonly:
            await sessions.set_archived(result["conversation"]["id"], archived=True)
        return {
            "fixture": "scripted fake router; no provider or embedding model calls",
            "database": url.database,
            "old_policy_readonly": old_readonly,
            "conversation_id": result["conversation"]["id"],
            "subject_id": result["memory_subject"]["id"],
            "definition_version_id": result["agent_definition"]["id"],
        }
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--existing-subject-id")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("browser fixture output already exists")
    result = asyncio.run(
        provision(args.database_url, existing_subject_id=args.existing_subject_id)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    args.output.chmod(0o600)
    print(args.output)


if __name__ == "__main__":
    main()
