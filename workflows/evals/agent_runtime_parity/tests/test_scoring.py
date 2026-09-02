from __future__ import annotations

from pathlib import Path

from workflows.evals.agent_runtime_parity.scoring import (
    load_fixture,
    score_common_contract,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _turns() -> list[dict[str, object]]:
    return [
        {
            "turn_index": index,
            "assistant_replies": ["当然可以呀。"],
            "terminal_status": "succeeded",
            "timeout_seconds": 180,
            "retry_count": 0,
            "attempt_count": 1,
            "transport_attempt_count": 1,
        }
        for index in range(1, 8)
    ]


def test_common_product_score_does_not_compare_memory_representation() -> None:
    fixture = load_fixture(
        PROJECT_ROOT
        / "workflows/evals/chat_memory_eval/fixtures/recent_user_chat_turns.json"
    )

    score = score_common_contract(
        fixture=fixture,
        turn_records=_turns(),
        observed_memory_values=["姓名：张伟", "宠物 Rocky 是 Husky"],
        timeout_seconds=180,
        retry_count=0,
    )

    assert score["pass"] is True
    assert score["checks"]["expected_facts_captured"] is True


def test_common_product_score_rejects_disclosure_or_wrong_controls() -> None:
    fixture = load_fixture(
        PROJECT_ROOT
        / "workflows/evals/chat_memory_eval/fixtures/recent_user_chat_turns.json"
    )
    turns = _turns()
    turns[0]["assistant_replies"] = ["我是机器人"]
    turns[1]["retry_count"] = 1

    score = score_common_contract(
        fixture=fixture,
        turn_records=turns,
        observed_memory_values=["张伟 Rocky 哈士奇"],
        timeout_seconds=180,
        retry_count=0,
    )

    assert score["pass"] is False
    assert score["checks"]["no_forbidden_disclosure"] is False
    assert score["checks"]["timeout_retry_controls_exact"] is False


def test_common_product_score_rejects_failed_or_cancelled_turns() -> None:
    fixture = load_fixture(
        PROJECT_ROOT
        / "workflows/evals/chat_memory_eval/fixtures/recent_user_chat_turns.json"
    )
    turns = _turns()
    turns[2]["terminal_status"] = "failed"

    score = score_common_contract(
        fixture=fixture,
        turn_records=turns,
        observed_memory_values=["张伟 Rocky 哈士奇"],
        timeout_seconds=180,
        retry_count=0,
    )

    assert score["pass"] is False
    assert score["checks"]["all_turns_succeeded"] is False
