from __future__ import annotations

import asyncio
from types import SimpleNamespace

from workflows.evals.agent_runtime_acceptance.runner import (
    execute_case,
    run_primary_rounds,
)
from workflows.evals.agent_runtime_acceptance.tests.test_rounds import (
    _Case,
    _FakeClient,
    _Turn,
    _case,
)


def test_failed_terminal_turn_preserves_evidence_without_sending_later_turn() -> None:
    async def scenario() -> None:
        client = _FakeClient(status="failed")
        case = _Case(
            key="failed-turn",
            conversations={"primary": ("primary", "primary")},
            turns=(_Turn("primary", "first"), _Turn("primary", "second")),
        )
        result = await execute_case(
            client=client,
            case=case,
            namespace="acceptance-failed-turn",
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            prompt_key="chat_prompt",
            persona_key="chat_persona",
            timeout_seconds=180,
            retry_count=0,
        )
        assert client.accepted == ["first"]
        assert len(result.turns) == 1
        assert result.infrastructure["terminal_statuses"] == ["failed"]
        assert any(event.event_type == "run.failed" for event in result.events)
        assert result.score["pass"] is False

    asyncio.run(scenario())


def test_failed_case_does_not_start_later_case() -> None:
    async def scenario() -> None:
        client = _FakeClient(status="failed")
        rounds = await run_primary_rounds(
            client=client,
            cases=(_case("failed"), _case("later")),
            canonical_case_keys=("failed", "later"),
            namespace="acceptance-failed-case",
            rounds=3,
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            prompt_key="chat_prompt",
            persona_key="chat_persona",
            timeout_seconds=180,
            retry_count=0,
        )
        assert client.accepted == ["hello"]
        assert len(client.session_payloads) == 1
        assert len(rounds) == 1
        assert rounds[0].case_keys == ("failed",)
        assert rounds[0].passed is False

    asyncio.run(scenario())


def test_failed_assertion_stops_before_next_case() -> None:
    async def scenario() -> None:
        client = _FakeClient()
        failed_case = _Case(
            key="failed-assertion",
            conversations={"primary": ("primary", "primary")},
            turns=(_Turn("primary", "first"),),
            assistant_assertions=(
                SimpleNamespace(
                    conversation_key="primary", contains_any=(), forbidden=("hello",)
                ),
            ),
        )
        rounds = await run_primary_rounds(
            client=client,
            cases=(failed_case, _case("later")),
            canonical_case_keys=("failed-assertion", "later"),
            namespace="acceptance-failed-assertion",
            rounds=3,
            conversation_model_key="chat",
            reviewer_model_key="reviewer",
            embedding_model_key="embedding",
            prompt_key="chat_prompt",
            persona_key="chat_persona",
            timeout_seconds=180,
            retry_count=0,
        )
        assert client.accepted == ["first"]
        assert rounds[0].case_keys == ("failed-assertion",)
        assert rounds[0].cases[0].score["pass"] is False
        assert rounds[0].passed is False

    asyncio.run(scenario())
