from __future__ import annotations

import asyncio
import hashlib
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import insert, select, update

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
from ade_api.features.agent_runtime.natural_attempt_evidence import (
    NaturalAttemptEvidence,
    retain_attempt_evidence,
)
from ade_api.features.agent_runtime.natural_memory_review import NaturalReviewDecision
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_subjects,
    messages,
    run_attempts,
    runs,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="isolated PostgreSQL evidence test database required"
)


def test_failed_candidate_and_committed_readback_are_retained_separately(
    tmp_path, monkeypatch, seed_m2_memory_resources, record_m2_memory_turn
) -> None:
    assert DATABASE_URL is not None
    monkeypatch.setattr(evidence_module, "ARTIFACT_ROOT", tmp_path / "evidence")

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        try:
            async with engine.begin() as connection:
                ids = await seed_m2_memory_resources(connection)
                rejected = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_one"],
                    "I live in Toronto.",
                )
                await connection.execute(
                    update(runs)
                    .where(runs.c.id == rejected["run_id"])
                    .values(status="failed")
                )
                await connection.execute(
                    insert(run_attempts).values(
                        id=str(uuid4()),
                        run_id=rejected["run_id"],
                        attempt_number=1,
                        status="failed",
                        timeout_seconds=30,
                    )
                )
                committed = await record_m2_memory_turn(
                    connection,
                    ids["workspace"],
                    ids["conversation_two"],
                    "How are you?",
                )
                await connection.execute(
                    insert(run_attempts).values(
                        id=str(uuid4()),
                        run_id=committed["run_id"],
                        attempt_number=1,
                        status="succeeded",
                        timeout_seconds=30,
                    )
                )
                await connection.execute(
                    insert(messages).values(
                        id=str(uuid4()),
                        workspace_id=ids["workspace"],
                        conversation_id=ids["conversation_two"],
                        sequence=2,
                        role="assistant",
                        content="Hello.",
                        content_sha256=hashlib.sha256(b"Hello.").hexdigest(),
                        run_id=committed["run_id"],
                    )
                )

            false_veto = NaturalAttemptEvidence(
                run_id=rejected["run_id"],
                attempt=1,
                policy_binding="natural-user-assertions-v3-b",
            )
            false_veto.capture_candidate("Okay, Toronto.", [])
            false_veto.capture_reviewer_decision(
                NaturalReviewDecision.model_validate(
                    {
                        "decisions": [
                            {
                                "kind": "subject_add",
                                "fact_type": "person.current_location",
                                "value": "Toronto",
                                "evidence": {
                                    "mode": "direct",
                                    "current_quote": "I live in Toronto",
                                },
                            }
                        ],
                    }
                )
            )
            rejected_path = await retain_attempt_evidence(engine, false_veto)
            rejected_artifact = json.loads(rejected_path.read_text())
            assert (
                rejected_artifact["terminal_readback"]["outcome"]
                == "confirmed_rejection"
            )
            assert (
                rejected_artifact["terminal_readback"]["candidate_commit"]
                == "uncommitted_undelivered"
            )
            assert rejected_artifact["terminal_readback"]["assistant_message_ids"] == []
            assert rejected_artifact["terminal_readback"]["revision_ids"] == []
            assert (
                rejected_artifact["terminal_readback"]["observed_memory_generation"]
                == 1
            )
            assert rejected_artifact["candidate_visible_reply"] == "Okay, Toronto."
            assert (
                rejected_artifact["reviewer_decision"]["decisions"][0]["kind"]
                == "subject_add"
            )
            assert rejected_artifact["generation"] == {"stage": "absent"}
            assert rejected_path.stat().st_mode & 0o777 == 0o600

            accepted = NaturalAttemptEvidence(
                run_id=committed["run_id"],
                attempt=1,
                policy_binding="natural-user-assertions-v3-b",
            )
            accepted.capture_candidate("Hello.", [])
            committed_path = await retain_attempt_evidence(engine, accepted)
            committed_artifact = json.loads(committed_path.read_text())
            assert committed_artifact["terminal_readback"]["outcome"] == "committed"
            assert (
                committed_artifact["terminal_readback"]["candidate_commit"]
                == "committed_visible_message"
            )
            assert (
                len(committed_artifact["terminal_readback"]["assistant_message_ids"])
                == 1
            )

            monkeypatch.setattr(evidence_module, "ARTIFACT_ROOT", tmp_path / "fault")

            def fail_link(_source, _target):
                raise OSError("synthetic artifact failure")

            monkeypatch.setattr(evidence_module.os, "link", fail_link)
            with pytest.raises(OSError, match="synthetic artifact failure"):
                await retain_attempt_evidence(engine, accepted)
            async with engine.connect() as connection:
                assert (
                    await connection.scalar(
                        select(runs.c.status).where(runs.c.id == committed["run_id"])
                    )
                    == "succeeded"
                )
                assert (
                    await connection.scalar(
                        select(memory_subjects.c.memory_generation).where(
                            memory_subjects.c.id == ids["subject_one"]
                        )
                    )
                    == 1
                )
        finally:
            await engine.dispose()

    asyncio.run(scenario())
