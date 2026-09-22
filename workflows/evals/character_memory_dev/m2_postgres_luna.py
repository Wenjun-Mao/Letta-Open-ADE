"""Four serial Luna probes conditioned by committed ADE PostgreSQL facts."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import AsyncConnection

from ade_api.features.agent_runtime.contracts import MemoryOperation
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository

from .luna import generate, preflight, subscription_environment
from .m2_postgres_case import (
    CaseResources,
    ScriptedAction,
    commit_scripted_action,
    create_case_resources,
)
from .output_schemas import output_schema
from .tasks import build_prompt, validate_result


EXPECTED_DATABASE = "ade_m2_memory_test_01a0ca1b"
TEST_DATABASE = re.compile(r"^ade_m2_memory_test_[0-9a-f]{8,}$")
OUTPUTS = Path(__file__).parent / "outputs"


@dataclass(frozen=True)
class ProbeStage:
    action: ScriptedAction
    question_id: str
    question: str


STAGES = (
    ProbeStage(
        ScriptedAction(
            key="subject_one_add",
            operation=MemoryOperation.ADD,
            subject_key="subject_one",
            conversation_key="conversation_one",
            sequence=1,
            source_text="我平时喝茶更喜欢红茶。",
            evidence_quote="喜欢红茶",
            value="红茶",
            qualifier="drink",
        ),
        "probe_after_add",
        "最近想挑一款茶，你记得我平时更偏爱哪类茶吗？",
    ),
    ProbeStage(
        ScriptedAction(
            key="subject_one_correct",
            operation=MemoryOperation.CORRECT,
            subject_key="subject_one",
            conversation_key="conversation_two",
            sequence=1,
            source_text="我的茶偏好改了，现在更喜欢绿茶。",
            evidence_quote="更喜欢绿茶",
            value="绿茶",
            predecessor_key="subject_one_add",
        ),
        "probe_after_correction",
        "如果给我泡茶，你觉得哪种茶现在更合我的口味？",
    ),
    ProbeStage(
        ScriptedAction(
            key="subject_one_forget",
            operation=MemoryOperation.FORGET,
            subject_key="subject_one",
            conversation_key="conversation_two",
            sequence=2,
            source_text="请把这个偏好忘掉。",
            evidence_quote="请把这个偏好忘掉",
            predecessor_key="subject_one_add",
        ),
        "probe_after_forget",
        "你还记得我平时偏爱喝什么茶吗？",
    ),
    ProbeStage(
        ScriptedAction(
            key="subject_two_add",
            operation=MemoryOperation.ADD,
            subject_key="subject_two",
            conversation_key="conversation_other_subject",
            sequence=1,
            source_text="我平时更喜欢听民谣。",
            evidence_quote="喜欢听民谣",
            value="民谣",
            qualifier="music",
        ),
        "probe_subject_two",
        "我平常听音乐时更偏爱哪种风格？",
    ),
)


class StageCommit(Protocol):
    async def __call__(
        self, action: ScriptedAction, committed: dict[str, dict[str, Any]]
    ) -> dict[str, Any]: ...


class ActiveFactRead(Protocol):
    async def __call__(self, subject_key: str) -> list[dict[str, Any]]: ...


class DialogueProbe(Protocol):
    async def __call__(
        self,
        stage: ProbeStage,
        data: dict[str, Any],
        facts: list[dict[str, Any]],
    ) -> dict[str, Any]: ...


def probe_input(question_id: str, question: str, facts: list[dict[str, Any]]) -> dict:
    """Build dialogue-only input from the subject-scoped repository result."""

    return {
        "messages": [{"id": question_id, "role": "user", "content": question}],
        "memories": [format_active_fact(fact) for fact in facts],
    }


def format_active_fact(fact: dict[str, Any]) -> str:
    if fact.get("fact_type") != "person.preference":
        raise ValueError("M2 dialogue slice accepts only typed person preferences")
    qualifier = fact.get("qualifier")
    value = fact.get("value")
    if not isinstance(qualifier, str) or not isinstance(value, str) or not value:
        raise ValueError("Repository returned a malformed active preference")
    labels = {"drink": "饮品", "music": "音乐"}
    if qualifier not in labels:
        raise ValueError(
            "M2 dialogue slice received an unexpected preference qualifier"
        )
    return f"用户{labels[qualifier]}偏好：{value}"


async def run_probe_sequence(
    *,
    commit: StageCommit,
    read_active_facts: ActiveFactRead,
    dialogue: DialogueProbe,
    record_probe: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Keep each commit, scoped read-back, and dialogue call in strict order."""

    committed: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    for stage in STAGES:
        committed[stage.action.key] = await commit(stage.action, committed)
        facts = await read_active_facts(stage.action.subject_key)
        data = probe_input(stage.question_id, stage.question, facts)
        record = {
            "probe": stage.question_id,
            "action": committed[stage.action.key],
            "subject_key": stage.action.subject_key,
            "prompt_context": data["memories"],
            "active_fact_sources": [
                {
                    "fact_id": str(fact["id"]),
                    "revision_id": str(fact["current_revision_id"]),
                    "value": fact["value"],
                    "qualifier": fact["qualifier"],
                }
                for fact in facts
            ],
            "input": data,
            "status": "context_prepared",
        }
        if record_probe:
            record_probe(record)
        result = await dialogue(stage, data, facts)
        record["result"] = result
        record["status"] = "completed"
        records.append(record)
    return records


def validate_test_database_url(database_url: str) -> None:
    try:
        url = make_url(database_url)
    except (ArgumentError, ValueError) as exc:
        raise ValueError(
            "M2 Luna workflow requires the named local test database"
        ) from exc
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"localhost", "127.0.0.1", "::1"}
        or url.username != "ade_owner"
        or url.password is not None
        or url.database != EXPECTED_DATABASE
        or not TEST_DATABASE.fullmatch(url.database or "")
    ):
        raise ValueError(
            "M2 Luna workflow only permits its passwordless loopback test database"
        )


async def verify_database(connection: AsyncConnection) -> None:
    row = (
        (
            await connection.execute(
                text("SELECT current_database() AS database, current_user AS role")
            )
        )
        .mappings()
        .one()
    )
    if row["database"] != EXPECTED_DATABASE or row["role"] != "ade_owner":
        raise ValueError(
            "Connected database identity does not match the disposable M2 target"
        )
    exists = await connection.scalar(text("SELECT to_regclass('ade.memory_facts')"))
    if exists is None:
        raise ValueError("The disposable M2 database is not migrated to the ADE schema")


def write_case_log(path: Path, case: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


async def execute_database_case(
    database_url: str,
    case_root: Path,
    *,
    dialogue_override: DialogueProbe | None = None,
) -> dict[str, Any]:
    """Run scripted commits and four read-after-commit probes, without cleanup."""

    validate_test_database_url(database_url)
    case_root.mkdir(parents=True, exist_ok=False)
    case = {
        "kind": "m2-ade-postgres-context-conditioning-development",
        "case_id": case_root.name,
        "database": EXPECTED_DATABASE,
        "mutations": "scripted typed inputs through ADE validation/write path; not model extraction",
        "dialogue_mode": "fake"
        if dialogue_override is not None
        else "luna-subscription",
        "sequence": [],
        "evidence_limits": [
            "not semantic retrieval quality",
            "not extraction quality",
            "not native runtime qualification",
            "not security proof",
            "not Hindsight comparison",
        ],
    }
    write_case_log(case_root / "case.json", case)
    engine = create_persistence_engine(database_url)
    reader = create_persistence_engine(database_url)
    resources: CaseResources
    try:
        async with reader.connect() as connection:
            await verify_database(connection)
        async with engine.begin() as connection:
            resources = await create_case_resources(connection)
        case["resource_ids"] = {
            "workspace_id": resources.workspace_id,
            "subject_ids": resources.subject_ids,
            "conversation_ids": resources.conversation_ids,
        }
        write_case_log(case_root / "case.json", case)

        async def commit_action(
            action: ScriptedAction, committed: dict[str, dict[str, Any]]
        ) -> dict[str, Any]:
            async with engine.begin() as connection:
                evidence = await commit_scripted_action(
                    connection,
                    resources=resources,
                    action=action,
                    committed=committed,
                )
            case["sequence"].append(
                {
                    "event": "committed_scripted_operation",
                    "operation": action.operation.value,
                    "action_key": action.key,
                    "fact_id": evidence["fact_id"],
                    "revision_id": evidence["revision_id"],
                    "source_message_id": evidence["source_message_id"],
                    "source_quote": evidence["source_quote"],
                    "subject_id": evidence["subject_id"],
                    "conversation_id": evidence["conversation_id"],
                }
            )
            write_case_log(case_root / "case.json", case)
            return evidence

        async def read_active_facts(subject_key: str) -> list[dict[str, Any]]:
            subject_id = resources.subject_ids[subject_key]
            async with reader.connect() as connection:
                return await MemoryRepository(connection).list_active_facts(subject_id)

        async def dialogue(
            stage: ProbeStage,
            data: dict[str, Any],
            facts: list[dict[str, Any]],
        ) -> dict[str, Any]:
            call_number = next(
                index
                for index, candidate in enumerate(STAGES, start=1)
                if candidate.question_id == stage.question_id
            )
            output = case_root / f"call-{call_number:02d}-{stage.question_id}"
            if dialogue_override is not None:
                return await dialogue_override(stage, data, facts)
            prompt = build_prompt("dialogue", data)
            raw = generate(
                prompt,
                output,
                timeout_seconds=180,
                output_schema=output_schema("dialogue"),
            )
            result = validate_result("dialogue", raw, data)
            (output / "input.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (output / "database-context.json").write_text(
                json.dumps(
                    {
                        "subject_id": resources.subject_ids[stage.action.subject_key],
                        "active_facts_read_from_ade_repository": [
                            {
                                "fact_id": str(fact["id"]),
                                "revision_id": str(fact["current_revision_id"]),
                                "fact_type": fact["fact_type"],
                                "qualifier": fact["qualifier"],
                                "value": fact["value"],
                            }
                            for fact in facts
                        ],
                        "prompt_memories_exact": data["memories"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            case["sequence"].append(
                {
                    "event": "dialogue_call_validated",
                    "probe": stage.question_id,
                    "output_directory": output.name,
                    "reply": result["reply"],
                }
            )
            write_case_log(case_root / "case.json", case)
            return result

        def record_probe(record: dict[str, Any]) -> None:
            call_number = next(
                index
                for index, candidate in enumerate(STAGES, start=1)
                if candidate.question_id == record["probe"]
            )
            case["sequence"].append(
                {
                    "event": "probe_context_prepared",
                    "output_directory": f"call-{call_number:02d}-{record['probe']}",
                    **record,
                }
            )
            write_case_log(case_root / "case.json", case)

        records = await run_probe_sequence(
            commit=commit_action,
            read_active_facts=read_active_facts,
            dialogue=dialogue,
            record_probe=record_probe,
        )
        case["probe_records"] = records
        case["status"] = (
            "four_fake_probes_completed"
            if dialogue_override is not None
            else "four_calls_validated"
        )
        write_case_log(case_root / "case.json", case)
        return case
    except Exception as exc:
        case["status"] = "incomplete_or_uncertain"
        case["failure"] = f"{type(exc).__name__}: {exc}"
        write_case_log(case_root / "case.json", case)
        raise
    finally:
        await reader.dispose()
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("ADE_TEST_DATABASE_URL"))
    parser.add_argument("--output-root", type=Path, default=OUTPUTS)
    args = parser.parse_args()
    if not args.database_url:
        parser.error("ADE_TEST_DATABASE_URL is required")
    try:
        validate_test_database_url(args.database_url)
        auth_env = subscription_environment()
        cli_version = preflight(auth_env)
        case_root = args.output_root / f"m2-postgres-luna-{uuid4().hex}"
        case = asyncio.run(execute_database_case(args.database_url, case_root))
    except (ValueError, OSError, RuntimeError, ArgumentError) as exc:
        print(f"M2 PostgreSQL Luna workflow failed: {exc}")
        return 1
    case["cli_version"] = cli_version
    write_case_log(case_root / "case.json", case)
    print(f"Four serial dialogue calls validated; evidence: {case_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
