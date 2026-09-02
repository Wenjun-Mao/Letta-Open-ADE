from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any


class FixtureError(ValueError):
    pass


@dataclass(frozen=True)
class InitialFact:
    subject_key: str
    value: str
    fact_type: str = ""
    qualifier: str | None = None
    key: str = ""


@dataclass(frozen=True)
class PreludeMessages:
    conversation_key: str
    count: int
    user_template: str
    assistant_template: str
    summary: str
    summary_through_sequence: int


@dataclass(frozen=True)
class FixtureTurn:
    conversation_key: str
    user: str


@dataclass(frozen=True)
class FactAssertion:
    subject_key: str
    aliases: tuple[str, ...]
    key: str = ""
    absent: bool = False


@dataclass(frozen=True)
class AssistantAssertion:
    conversation_key: str
    contains_any: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()


@dataclass(frozen=True)
class StudyCase:
    key: str
    description: str
    agent_keys: tuple[str, ...]
    subject_keys: tuple[str, ...]
    conversations: dict[str, tuple[str, str]]
    initial_facts: tuple[InitialFact, ...]
    prelude_messages: tuple[PreludeMessages, ...]
    turns: tuple[FixtureTurn, ...]
    fact_assertions: tuple[FactAssertion, ...]
    assistant_assertions: tuple[AssistantAssertion, ...]
    enabled_tools: tuple[str, ...]
    expected_tool_observations: tuple[str, ...]
    require_failed_tool_result: bool
    profile_token_override: int | None


def study_cases_path() -> Path:
    return _package_data_path("study_cases.json")


def semantic_retrieval_cases_path() -> Path:
    return _package_data_path("semantic_retrieval_cases.json")


def _package_data_path(name: str) -> Path:
    resource = files("agent_runtime_eval_contracts").joinpath("data", name)
    return Path(str(resource))


def load_cases(path: Path) -> tuple[StudyCase, ...]:
    if not path.is_file():
        raise FixtureError(f"Fixture suite not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise FixtureError("Fixture suite must contain a cases array")
    cases = tuple(_case(item) for item in payload["cases"])
    keys = [case.key for case in cases]
    if len(keys) != len(set(keys)):
        raise FixtureError("Fixture case keys must be unique")
    return cases


def select_cases(
    cases: tuple[StudyCase, ...], keys: tuple[str, ...]
) -> tuple[StudyCase, ...]:
    if not keys:
        return cases
    by_key = {case.key: case for case in cases}
    missing = sorted(set(keys) - set(by_key))
    if missing:
        raise FixtureError(f"Unknown fixture case keys: {missing}")
    return tuple(by_key[key] for key in keys)


def _case(value: object) -> StudyCase:
    item = _object(value, "case")
    key = _required_string(item, "key")
    agents = _strings(item.get("agent_keys")) or ("primary",)
    subjects = _strings(item.get("subject_keys")) or ("primary",)
    conversations_raw = _object(item.get("conversations"), f"{key}.conversations")
    conversations: dict[str, tuple[str, str]] = {}
    for conversation_key, binding_value in conversations_raw.items():
        binding = _object(binding_value, f"{key}.{conversation_key}")
        agent_key = _required_string(binding, "agent_key")
        subject_key = _required_string(binding, "subject_key")
        if agent_key not in agents or subject_key not in subjects:
            raise FixtureError(
                f"{key}.{conversation_key} references an undeclared agent or subject"
            )
        conversations[str(conversation_key)] = (agent_key, subject_key)
    if not conversations:
        raise FixtureError(f"{key} must define at least one conversation")

    turns = tuple(
        FixtureTurn(
            conversation_key=_required_string(
                _object(turn, "turn"), "conversation_key"
            ),
            user=_required_string(_object(turn, "turn"), "user"),
        )
        for turn in _list(item.get("turns"))
    )
    if not turns:
        raise FixtureError(f"{key} must define at least one turn")
    for turn in turns:
        if turn.conversation_key not in conversations:
            raise FixtureError(f"{key} turn references {turn.conversation_key}")

    enabled_tools = _strings(item.get("enabled_tools"))
    expected_tool_observations = _strings(item.get("expected_tool_observations"))
    if len(enabled_tools) != len(set(enabled_tools)):
        raise FixtureError(f"{key}.enabled_tools must be unique")
    if len(expected_tool_observations) != len(set(expected_tool_observations)):
        raise FixtureError(f"{key}.expected_tool_observations must be unique")
    unavailable_expectations = sorted(
        set(expected_tool_observations) - set(enabled_tools)
    )
    if unavailable_expectations:
        raise FixtureError(
            f"{key} expects observations for disabled tools: {unavailable_expectations}"
        )

    return StudyCase(
        key=key,
        description=str(item.get("description") or "").strip(),
        agent_keys=agents,
        subject_keys=subjects,
        conversations=conversations,
        initial_facts=tuple(
            InitialFact(
                subject_key=_required_string(
                    _object(fact, "initial_fact"), "subject_key"
                ),
                value=_required_string(_object(fact, "initial_fact"), "value"),
                fact_type=str(
                    _object(fact, "initial_fact").get("fact_type") or ""
                ).strip(),
                qualifier=(
                    str(_object(fact, "initial_fact")["qualifier"]).strip()
                    if _object(fact, "initial_fact").get("qualifier") is not None
                    else None
                ),
                key=str(_object(fact, "initial_fact").get("key") or "").strip(),
            )
            for fact in _list(item.get("initial_facts"))
        ),
        prelude_messages=tuple(
            _prelude(_object(prelude, "prelude"))
            for prelude in _list(item.get("prelude_messages"))
        ),
        turns=turns,
        fact_assertions=tuple(
            _fact_assertion(_object(assertion, "fact_assertion"))
            for assertion in _list(item.get("fact_assertions"))
        ),
        assistant_assertions=tuple(
            _assistant_assertion(_object(assertion, "assistant_assertion"))
            for assertion in _list(item.get("assistant_assertions"))
        ),
        enabled_tools=enabled_tools,
        expected_tool_observations=expected_tool_observations,
        require_failed_tool_result=bool(item.get("require_failed_tool_result", False)),
        profile_token_override=(
            int(item["profile_token_override"])
            if item.get("profile_token_override") is not None
            else None
        ),
    )


def _prelude(item: dict[str, Any]) -> PreludeMessages:
    return PreludeMessages(
        conversation_key=_required_string(item, "conversation_key"),
        count=int(item.get("count") or 0),
        user_template=_required_string(item, "user_template"),
        assistant_template=_required_string(item, "assistant_template"),
        summary=str(item.get("summary") or "").strip(),
        summary_through_sequence=int(item.get("summary_through_sequence") or 0),
    )


def _fact_assertion(item: dict[str, Any]) -> FactAssertion:
    aliases = _strings(item.get("aliases"))
    if not aliases:
        raise FixtureError("fact assertion requires aliases")
    return FactAssertion(
        subject_key=_required_string(item, "subject_key"),
        key=str(item.get("key") or "").strip(),
        aliases=aliases,
        absent=bool(item.get("absent", False)),
    )


def _assistant_assertion(item: dict[str, Any]) -> AssistantAssertion:
    return AssistantAssertion(
        conversation_key=_required_string(item, "conversation_key"),
        contains_any=_strings(item.get("contains_any")),
        forbidden=_strings(item.get("forbidden")),
    )


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FixtureError(f"{label} must be an object")
    return value


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: object) -> tuple[str, ...]:
    return tuple(str(item).strip() for item in _list(value) if str(item).strip())


def _required_string(item: dict[str, Any], key: str) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        raise FixtureError(f"{key} is required")
    return value
