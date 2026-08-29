from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .client import RunTimeout, RuntimeV3Client
from .normalization import normalize_case


@dataclass(frozen=True)
class ResourceScope:
    definition_keys: tuple[str, ...]
    subject_external_keys: tuple[str, ...]
    deployment_fingerprints: dict[str, str]
    deployment_snapshots: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class CaseExecution:
    case_key: str
    score: dict[str, Any]
    turns: tuple[Any, ...]
    events: tuple[Any, ...]
    tools: tuple[Any, ...]
    facts: tuple[Any, ...]
    infrastructure: dict[str, Any]
    resources: ResourceScope


@dataclass(frozen=True)
class QualificationRound:
    index: int
    kind: str
    execution_mode: str
    complete_matrix: bool
    passed: bool
    case_keys: tuple[str, ...]
    cases: tuple[CaseExecution, ...]
    deployment_fingerprints: dict[str, str]
    artifact_sha256: str = ""


async def execute_case(
    *,
    client: RuntimeV3Client,
    case: object,
    namespace: str,
    conversation_model_key: str,
    reviewer_model_key: str,
    embedding_model_key: str,
    timeout_seconds: float,
    retry_count: int,
    resource_scope_sink: list[ResourceScope] | None = None,
) -> CaseExecution:
    definitions: dict[str, str] = {}
    subjects: dict[str, str] = {}
    conversations: dict[str, str] = {}
    definition_keys: list[str] = []
    subject_external_keys: list[str] = []
    fingerprints: dict[str, str] = {}
    deployment_snapshots: list[dict[str, Any]] = []
    for agent_key in tuple(getattr(case, "agent_keys", ("primary",))):
        definition_key = _resource_key(
            namespace, str(getattr(case, "key")), f"agent-{agent_key}"
        )
        created = await client.create_definition(
            definition_key=definition_key,
            name=f"v3 acceptance {getattr(case, 'key')} {agent_key}",
            model_key=conversation_model_key,
            reviewer_model_key=reviewer_model_key,
            embedding_model_key=embedding_model_key,
        )
        definition_keys.append(definition_key)
        fingerprints.update(_deployment_fingerprints(created))
        deployment_snapshots.extend(_deployment_snapshots(created))
        if resource_scope_sink is not None:
            resource_scope_sink.append(
                ResourceScope(
                    (definition_key,),
                    (),
                    _deployment_fingerprints(created),
                    _deployment_snapshots(created),
                )
            )
        definitions[str(agent_key)] = _id(created, "definition")
    for subject_key in tuple(getattr(case, "subject_keys", ("primary",))):
        external_key = _resource_key(
            namespace, str(getattr(case, "key")), f"subject-{subject_key}"
        )
        created = await client.create_subject(
            external_key, f"v3 acceptance {subject_key}"
        )
        subject_external_keys.append(external_key)
        if resource_scope_sink is not None:
            resource_scope_sink.append(ResourceScope((), (external_key,), {}, ()))
        subjects[str(subject_key)] = _id(created, "subject")
    for conversation_key, binding in dict(getattr(case, "conversations")).items():
        agent_key, subject_key = binding
        created = await client.create_conversation(
            definitions[agent_key], subjects[subject_key]
        )
        conversations[str(conversation_key)] = _id(created, "conversation")
    scope = ResourceScope(
        definition_keys=tuple(definition_keys),
        subject_external_keys=tuple(subject_external_keys),
        deployment_fingerprints=fingerprints,
        deployment_snapshots=tuple(deployment_snapshots),
    )

    # v3 deliberately has no mutable seed endpoint. Setup is expressed as normal
    # user turns so the black-box workflow does not bypass the runtime contract.
    for fact in tuple(getattr(case, "initial_facts", ())):
        subject_key = str(getattr(fact, "subject_key", "primary"))
        conversation_key = _first_conversation_for_subject(case, subject_key)
        content = (
            f"Please remember this exact durable fact: {getattr(fact, 'value', '')}"
        )
        await _complete_setup_turn(
            client,
            conversations[conversation_key],
            content,
            namespace,
            timeout_seconds,
            retry_count,
        )
    for prelude in tuple(getattr(case, "prelude_messages", ())):
        conversation_key = str(getattr(prelude, "conversation_key"))
        for number in range(1, int(getattr(prelude, "count", 0)) + 1):
            template = str(getattr(prelude, "user_template"))
            await _complete_setup_turn(
                client,
                conversations[conversation_key],
                template.format(index=number),
                namespace,
                timeout_seconds,
                retry_count,
            )

    completed_turns: list[dict[str, Any]] = []
    for index, turn in enumerate(tuple(getattr(case, "turns")), start=1):
        conversation_key = str(getattr(turn, "conversation_key"))
        conversation_id = conversations[conversation_key]
        accepted = await client.accept_turn(
            conversation_id,
            str(getattr(turn, "user")),
            _idempotency_key(namespace, str(getattr(case, "key")), index),
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
        )
        try:
            run, events = await client.await_terminal(
                accepted, timeout_seconds=timeout_seconds * (retry_count + 1) + 30
            )
        except RunTimeout:
            run = await client.cancel_run(str(accepted["run_id"]))
            events = ()
        state = await client.get_conversation_state(conversation_id)
        completed_turns.append(
            {
                "conversation_key": conversation_key,
                "run": run,
                "events": events,
                "conversation_state": state,
            }
        )
    facts: dict[str, list[dict[str, Any]]] = {}
    for subject_key, subject_id in subjects.items():
        response = await client.get_subject_memories(subject_id)
        values = response.get("facts")
        facts[subject_key] = list(values) if isinstance(values, list) else []
    normalized = normalize_case(case=case, turns=completed_turns, subject_facts=facts)
    passed = (
        bool(normalized.score.get("pass")) and not normalized.infrastructure["failures"]
    )
    score = {**normalized.score, "pass": passed}
    return CaseExecution(
        case_key=str(getattr(case, "key")),
        score=score,
        turns=normalized.turns,
        events=normalized.events,
        tools=normalized.tools,
        facts=normalized.facts,
        infrastructure=normalized.infrastructure,
        resources=scope,
    )


async def run_primary_rounds(
    *,
    client: RuntimeV3Client,
    cases: tuple[object, ...],
    canonical_case_keys: tuple[str, ...],
    namespace: str,
    rounds: int,
    conversation_model_key: str,
    reviewer_model_key: str,
    embedding_model_key: str,
    timeout_seconds: float,
    retry_count: int,
    execution_mode: str = "live-api",
    resource_scope_sink: list[ResourceScope] | None = None,
    on_round_complete: Callable[[QualificationRound], QualificationRound] | None = None,
) -> tuple[QualificationRound, ...]:
    results: list[QualificationRound] = []
    for index in range(1, rounds + 1):
        executions = tuple(
            await execute_case(
                client=client,
                case=case,
                namespace=_resource_key(namespace, f"round-{index}"),
                conversation_model_key=conversation_model_key,
                reviewer_model_key=reviewer_model_key,
                embedding_model_key=embedding_model_key,
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
                resource_scope_sink=resource_scope_sink,
            )
            for case in cases
        )
        fingerprints = _combined_fingerprints(executions)
        case_keys = tuple(item.case_key for item in executions)
        result = QualificationRound(
            index=index,
            kind="primary",
            execution_mode=execution_mode,
            complete_matrix=case_keys == canonical_case_keys,
            passed=all(bool(item.score.get("pass")) for item in executions),
            case_keys=case_keys,
            cases=executions,
            deployment_fingerprints=fingerprints,
        )
        results.append(on_round_complete(result) if on_round_complete else result)
    return tuple(results)


async def run_llama_compatibility_round(
    *,
    client: RuntimeV3Client,
    cases: tuple[object, ...],
    namespace: str,
    conversation_model_key: str,
    reviewer_model_key: str,
    embedding_model_key: str,
    timeout_seconds: float,
    retry_count: int,
    resource_scope_sink: list[ResourceScope] | None = None,
    on_round_complete: Callable[[QualificationRound], QualificationRound] | None = None,
) -> QualificationRound:
    executions = tuple(
        await execute_case(
            client=client,
            case=case,
            namespace=_resource_key(namespace, "llama-compatibility"),
            conversation_model_key=conversation_model_key,
            reviewer_model_key=reviewer_model_key,
            embedding_model_key=embedding_model_key,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            resource_scope_sink=resource_scope_sink,
        )
        for case in cases
    )
    result = QualificationRound(
        index=1,
        kind="llama-compatibility",
        execution_mode="live-api",
        complete_matrix=False,
        passed=all(bool(item.score.get("pass")) for item in executions),
        case_keys=tuple(item.case_key for item in executions),
        cases=executions,
        deployment_fingerprints=_combined_fingerprints(executions),
    )
    return on_round_complete(result) if on_round_complete else result


async def _complete_setup_turn(
    client: RuntimeV3Client,
    conversation_id: str,
    content: str,
    namespace: str,
    timeout_seconds: float,
    retry_count: int,
) -> None:
    accepted = await client.accept_turn(
        conversation_id,
        content,
        _idempotency_key(namespace, "setup", _stable_content_index(content)),
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
    )
    run, _events = await client.await_terminal(
        accepted, timeout_seconds=timeout_seconds * (retry_count + 1) + 30
    )
    if run.get("status") != "succeeded":
        raise RuntimeError("canonical setup turn did not succeed")


def _first_conversation_for_subject(case: object, subject_key: str) -> str:
    for conversation_key, (_agent, subject) in dict(
        getattr(case, "conversations")
    ).items():
        if subject == subject_key:
            return str(conversation_key)
    raise RuntimeError(f"case has no conversation for subject {subject_key}")


def _deployment_fingerprints(definition: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for deployment in definition.get("deployments") or []:
        if not isinstance(deployment, dict):
            continue
        role = str(deployment.get("role") or "")
        fingerprint = str(deployment.get("fingerprint") or "")
        if role and fingerprint:
            values[role] = fingerprint
    return values


def _deployment_snapshots(definition: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    deployments = definition.get("deployments")
    if not isinstance(deployments, list):
        return ()
    return tuple(dict(item) for item in deployments if isinstance(item, dict))


def _combined_fingerprints(executions: tuple[CaseExecution, ...]) -> dict[str, str]:
    combined: dict[str, str] = {}
    for execution in executions:
        for role, fingerprint in execution.resources.deployment_fingerprints.items():
            prior = combined.setdefault(role, fingerprint)
            if prior != fingerprint:
                combined[role] = "inconsistent"
    return combined


def _resource_key(*parts: str) -> str:
    joined = "-".join(parts).lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "-", joined).strip("-_")
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:10]
    return f"{normalized[:52].rstrip('-_')}-{digest}"


def _idempotency_key(namespace: str, case_key: str, index: int) -> str:
    return _resource_key(namespace, case_key, f"turn-{index}")


def _stable_content_index(content: str) -> int:
    return int(hashlib.sha256(content.encode("utf-8")).hexdigest()[:8], 16)


def _id(payload: dict[str, Any], kind: str) -> str:
    value = str(payload.get("id") or "").strip()
    if not value:
        raise RuntimeError(f"v3 {kind} response is missing id")
    return value
