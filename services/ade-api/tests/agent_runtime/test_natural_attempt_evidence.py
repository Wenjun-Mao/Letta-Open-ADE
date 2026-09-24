from __future__ import annotations

from types import SimpleNamespace

import pytest

import ade_api.features.agent_runtime.natural_attempt_evidence as evidence_module
from ade_api.features.agent_runtime.errors import RuntimeNotReady
from ade_api.features.agent_runtime.natural_attempt_evidence import (
    NaturalAttemptEvidence,
    capture_allowed,
    classify_outcome,
)


def test_capture_requires_explicit_isolated_evaluation_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local = "postgresql+psycopg://ade_owner@127.0.0.1:32768/ade_natural_test_case1"
    monkeypatch.delenv("ADE_NATURAL_MEMORY_CAPTURE", raising=False)
    assert (
        capture_allowed(
            database_url=local, runtime_mode="development", purpose="evaluation"
        )
        is False
    )
    monkeypatch.setenv("ADE_NATURAL_MEMORY_CAPTURE", "1")
    assert (
        capture_allowed(
            database_url=local, runtime_mode="development", purpose="evaluation"
        )
        is True
    )
    for database_url, mode, purpose in (
        (local, "release", "evaluation"),
        (local, "development", "agent_studio"),
        ("postgresql+psycopg://ade_owner@db/prod", "development", "evaluation"),
    ):
        with pytest.raises(RuntimeNotReady):
            capture_allowed(
                database_url=database_url, runtime_mode=mode, purpose=purpose
            )


def test_outcome_classification_requires_authoritative_consistency() -> None:
    assert (
        classify_outcome(
            run_status="succeeded",
            attempt_status="succeeded",
            assistant_message_ids=["assistant"],
            revision_ids=["revision"],
        )
        == "committed"
    )
    assert (
        classify_outcome(
            run_status="failed",
            attempt_status="failed",
            assistant_message_ids=[],
            revision_ids=[],
        )
        == "confirmed_rejection"
    )
    assert (
        classify_outcome(
            run_status="succeeded",
            attempt_status="failed",
            assistant_message_ids=["later-attempt"],
            revision_ids=[],
        )
        == "rejected_prior_attempt"
    )
    assert (
        classify_outcome(
            run_status="running",
            attempt_status="running",
            assistant_message_ids=[],
            revision_ids=[],
        )
        == "unconfirmed"
    )


def test_evidence_has_explicit_absent_stages_without_raw_wire_fields() -> None:
    evidence = NaturalAttemptEvidence(
        run_id="run-1", attempt=1, policy_binding="natural-user-assertions-v2-b"
    )
    evidence.capture_generation(
        messages_for_model=[{"role": "user", "content": "I live in Toronto."}],
        source_messages=(
            {"id": "user-1", "role": "user", "content": "I live in Toronto."},
        ),
        section_tokens={"current_user_message": 6},
        retrieved_fact_ids=[],
        omitted_message_ids=[],
        estimated_input_tokens=12,
        input_limit=100,
    )
    evidence.capture_generation_request(
        {
            "model": "synthetic::chat",
            "messages": [
                {
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": "private chain must not be retained",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "search_memory",
                                "arguments": '{"query":"Roxy"}',
                            },
                        }
                    ],
                },
                {"role": "tool", "content": '{"facts":["Roxy is a Husky"]}'},
            ],
            "max_tokens": 100,
            "tools": [],
        }
    )
    evidence.capture_reviewer_request(
        {
            "model": "synthetic::reviewer",
            "messages": [
                {"role": "system", "content": "Review visible claims."},
                {"role": "user", "content": '{"candidate_visible_reply":"Okay."}'},
            ],
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "enabled"},
            "reasoning_content": "private chain must not be retained",
        }
    )
    evidence.capture_provider_events(
        (
            SimpleNamespace(
                event_type="model.request.started",
                payload={"stage": "conversation", "request_number": 1},
            ),
        )
    )
    assert evidence.generation is not None
    assert evidence.generation["source_messages"][0]["id"] == "user-1"
    assert evidence.reviewer_decision is None
    assert evidence.generation_requests[0]["messages"][1]["role"] == "tool"
    assert evidence.reviewer_request is not None
    assert evidence.reviewer_request["messages"][1]["role"] == "user"
    assert "thinking" not in evidence.reviewer_request
    assert "reasoning_content" not in evidence.reviewer_request
    assert evidence.provider_events[0]["payload"]["stage"] == "conversation"
    assert "private chain" not in str(evidence.generation_requests)
    assert "private_reasoning" in evidence.excluded_fields
    assert "authentication_headers" in evidence.excluded_fields
    assert evidence_module.ARTIFACT_ROOT.name == "natural-memory-attempts"
