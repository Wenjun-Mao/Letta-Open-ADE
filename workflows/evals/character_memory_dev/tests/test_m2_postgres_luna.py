from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from workflows.evals.character_memory_dev.m2_postgres_luna import (
    STAGES,
    execute_database_case,
    probe_input,
    run_probe_sequence,
    validate_test_database_url,
)


def _fact(fact_id: str, revision_id: str, qualifier: str, value: str) -> dict:
    return {
        "id": fact_id,
        "current_revision_id": revision_id,
        "fact_type": "person.preference",
        "qualifier": qualifier,
        "value": value,
        "status": "active",
    }


def test_probe_input_contains_only_current_fact_values_and_new_question() -> None:
    facts = [_fact("fact-1", "revision-2", "drink", "绿茶")]
    data = probe_input("probe-2", "现在适合给我泡什么茶？", facts)

    assert data == {
        "messages": [
            {
                "id": "probe-2",
                "role": "user",
                "content": "现在适合给我泡什么茶？",
            }
        ],
        "memories": ["用户饮品偏好：绿茶"],
    }
    assert "红茶" not in repr(data)
    assert "source" not in data
    assert "expectations" not in data


def test_sequence_commits_then_reads_subject_scope_before_each_dialogue() -> None:
    asyncio.run(_exercise_sequence())


async def _exercise_sequence() -> None:
    events: list[tuple] = []
    subject_facts: dict[str, list[dict]] = {
        "subject_one": [],
        "subject_two": [],
    }

    async def commit(action, committed):
        events.append(("commit", action.key, action.subject_key))
        if action.key == "subject_one_add":
            subject_facts["subject_one"] = [
                _fact("fact-one", "revision-add", "drink", "红茶")
            ]
            return {"fact_id": "fact-one", "revision_id": "revision-add"}
        if action.key == "subject_one_correct":
            assert committed["subject_one_add"]["fact_id"] == "fact-one"
            subject_facts["subject_one"] = [
                _fact("fact-one", "revision-correct", "drink", "绿茶")
            ]
            return {"fact_id": "fact-one", "revision_id": "revision-correct"}
        if action.key == "subject_one_forget":
            assert committed["subject_one_add"]["fact_id"] == "fact-one"
            subject_facts["subject_one"] = []
            return {"fact_id": "fact-one", "revision_id": "revision-forget"}
        subject_facts["subject_two"] = [
            _fact("fact-two", "revision-other", "music", "民谣")
        ]
        return {"fact_id": "fact-two", "revision_id": "revision-other"}

    async def read_active_facts(subject_key):
        events.append(("read", subject_key))
        return list(subject_facts[subject_key])

    async def dialogue(stage, data, facts):
        events.append(("dialogue", stage.question_id, tuple(data["memories"])))
        assert set(data) == {"messages", "memories"}
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == stage.question
        assert all(message.get("role") == "user" for message in data["messages"])
        supplied = repr(data)
        for transcript in (
            "我平时喝茶更喜欢红茶。",
            "我的茶偏好改了，现在更喜欢绿茶。",
            "请把这个偏好忘掉。",
        ):
            assert transcript not in supplied
        return {"reply": "收到。"}

    records = await run_probe_sequence(
        commit=commit,
        read_active_facts=read_active_facts,
        dialogue=dialogue,
    )

    assert len(records) == 4
    assert [event[0] for event in events] == [
        "commit",
        "read",
        "dialogue",
        "commit",
        "read",
        "dialogue",
        "commit",
        "read",
        "dialogue",
        "commit",
        "read",
        "dialogue",
    ]
    assert [event[1] for event in events if event[0] == "dialogue"] == [
        "probe_after_add",
        "probe_after_correction",
        "probe_after_forget",
        "probe_subject_two",
    ]
    assert [record["prompt_context"] for record in records] == [
        ["用户饮品偏好：红茶"],
        ["用户饮品偏好：绿茶"],
        [],
        ["用户音乐偏好：民谣"],
    ]
    assert [record["active_fact_sources"] for record in records][-1] == [
        {
            "fact_id": "fact-two",
            "revision_id": "revision-other",
            "value": "民谣",
            "qualifier": "music",
        }
    ]
    assert [stage.action.operation.value for stage in STAGES] == [
        "add",
        "correct",
        "forget",
        "add",
    ]


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://ade_owner:secret@127.0.0.1/ade_m2_memory_test_01a0ca1b",
        "postgresql+psycopg://other@127.0.0.1/ade_m2_memory_test_01a0ca1b",
        "postgresql+psycopg://ade_owner@remote.example/ade_m2_memory_test_01a0ca1b",
        "postgresql+psycopg://ade_owner@127.0.0.1/ade_m2_memory_test_other",
    ],
)
def test_database_url_guard_only_allows_the_named_passwordless_loopback_db(
    url: str,
) -> None:
    with pytest.raises(ValueError):
        validate_test_database_url(url)


def test_database_url_guard_accepts_the_named_passwordless_loopback_db() -> None:
    validate_test_database_url(
        "postgresql+psycopg://ade_owner@127.0.0.1/ade_m2_memory_test_01a0ca1b"
    )


def test_postgres_case_commits_readbacks_and_probes_with_fake_dialogue(
    tmp_path: Path,
) -> None:
    database_url = os.getenv("ADE_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip(
            "ADE_TEST_DATABASE_URL must point at the named disposable M2 database"
        )
    try:
        validate_test_database_url(database_url)
    except ValueError:
        pytest.skip("M2 Luna case uses its separately named disposable database")

    async def run() -> None:
        calls = []

        async def fake_dialogue(stage, data, facts):
            calls.append((stage.question_id, data, facts))
            return {"reply": "伪造的测试回复"}

        case = await execute_database_case(
            database_url,
            tmp_path / "unique-m2-postgres-luna-case",
            dialogue_override=fake_dialogue,
        )

        assert case["status"] == "four_fake_probes_completed"
        assert [call[0] for call in calls] == [stage.question_id for stage in STAGES]
        assert [call[1]["memories"] for call in calls] == [
            ["用户饮品偏好：红茶"],
            ["用户饮品偏好：绿茶"],
            [],
            ["用户音乐偏好：民谣"],
        ]
        assert all(set(data) == {"messages", "memories"} for _, data, _ in calls)
        assert all(len(facts) <= 1 for _, _, facts in calls)
        assert calls[0][2][0]["id"] == case["sequence"][0]["fact_id"]
        assert case["probe_records"][2]["active_fact_sources"] == []
        assert (
            case["probe_records"][3]["active_fact_sources"][0]["qualifier"] == "music"
        )

    asyncio.run(run())
