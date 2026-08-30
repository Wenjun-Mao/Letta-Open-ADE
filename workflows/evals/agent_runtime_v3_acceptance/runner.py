from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .client import RunTimeout, RuntimeV3Client
from .normalization import normalize_case
from .qualification import requires_versioned_summary


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
    setup_run_ids: tuple[str, ...] = ()


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


class CaseStageError(RuntimeError):
    """A safe, artifact-ready failure from one observable case stage."""

    def __init__(self, stage: str) -> None:
        super().__init__(stage)
        self.stage = stage


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
    definition_tools = _case_tool_names(case)
    for agent_key in tuple(getattr(case, "agent_keys", ("primary",))):
        definition_key = _resource_key(
            namespace, str(getattr(case, "key")), f"agent-{agent_key}"
        )
        definition_keys.append(definition_key)
        if resource_scope_sink is not None:
            # Register the deterministic key before the request. A timeout can
            # leave creation outcome unknown, but cleanup must still cover it.
            resource_scope_sink.append(ResourceScope((definition_key,), (), {}, ()))
        created = await _run_stage(
            "definition_setup",
            client.create_definition(
                definition_key=definition_key,
                name=f"v3 acceptance {getattr(case, 'key')} {agent_key}",
                model_key=conversation_model_key,
                reviewer_model_key=reviewer_model_key,
                embedding_model_key=embedding_model_key,
                tool_names=definition_tools,
            ),
        )
        fingerprints.update(_deployment_fingerprints(created))
        deployment_snapshots.extend(_deployment_snapshots(created))
        if resource_scope_sink is not None:
            resource_scope_sink.append(
                ResourceScope(
                    (),
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
        subject_external_keys.append(external_key)
        if resource_scope_sink is not None:
            resource_scope_sink.append(ResourceScope((), (external_key,), {}, ()))
        created = await _run_stage(
            "subject_setup",
            client.create_subject(external_key, f"v3 acceptance {subject_key}"),
        )
        subjects[str(subject_key)] = _id(created, "subject")
    for conversation_key, binding in dict(getattr(case, "conversations")).items():
        agent_key, subject_key = binding
        created = await _run_stage(
            "conversation_setup",
            client.create_conversation(definitions[agent_key], subjects[subject_key]),
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
    auxiliary_turns: list[dict[str, Any]] = []
    for fact in tuple(getattr(case, "initial_facts", ())):
        subject_key = str(getattr(fact, "subject_key", "primary"))
        conversation_key = _first_conversation_for_subject(case, subject_key)
        content = _natural_fact_setup_message(fact)
        setup_run, setup_events = await _complete_setup_turn(
            client,
            conversations[conversation_key],
            content,
            namespace,
            timeout_seconds,
            retry_count,
            stage="initial_fact_setup",
        )
        auxiliary_turns.append(
            {
                "conversation_key": conversation_key,
                "run": setup_run,
                "events": setup_events,
            }
        )
        response = await _run_stage(
            "initial_fact_memory_verification",
            client.get_subject_memories(subjects[subject_key]),
        )
        _verify_public_initial_fact(
            response=response,
            subject_id=subjects[subject_key],
            fact=fact,
        )
    for prelude in tuple(getattr(case, "prelude_messages", ())):
        conversation_key = str(getattr(prelude, "conversation_key"))
        for number in range(1, int(getattr(prelude, "count", 0)) + 1):
            template = str(getattr(prelude, "user_template"))
            setup_run, setup_events = await _complete_setup_turn(
                client,
                conversations[conversation_key],
                template.format(index=number),
                namespace,
                timeout_seconds,
                retry_count,
                stage="prelude_setup",
            )
            auxiliary_turns.append(
                {
                    "conversation_key": conversation_key,
                    "run": setup_run,
                    "events": setup_events,
                }
            )

    completed_turns: list[dict[str, Any]] = []
    for index, turn in enumerate(tuple(getattr(case, "turns")), start=1):
        conversation_key = str(getattr(turn, "conversation_key"))
        conversation_id = conversations[conversation_key]
        accepted = await _run_stage(
            "turn_execution",
            client.accept_turn(
                conversation_id,
                str(getattr(turn, "user")),
                _idempotency_key(namespace, str(getattr(case, "key")), index),
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
            ),
        )
        run, events = await _run_stage(
            "turn_execution",
            _await_terminal_with_cancellation(
                client,
                accepted,
                timeout_seconds=timeout_seconds * (retry_count + 1) + 30,
            ),
        )
        state = await _run_stage(
            "turn_state_observation", client.get_conversation_state(conversation_id)
        )
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
        response = await _run_stage(
            "final_memory_observation", client.get_subject_memories(subject_id)
        )
        values = response.get("facts")
        facts[subject_key] = list(values) if isinstance(values, list) else []
    normalized = _normalize_case(
        case=case,
        turns=completed_turns,
        auxiliary_turns=auxiliary_turns,
        subject_facts=facts,
    )
    capability_checks = _capability_checks(case, normalized.events, completed_turns)
    capability_failures = [check for check in capability_checks if not check["pass"]]
    infrastructure = {
        **normalized.infrastructure,
        "failures": [
            *normalized.infrastructure["failures"],
            *capability_failures,
        ],
        "capability_checks": capability_checks,
    }
    passed = bool(normalized.score.get("pass")) and not infrastructure["failures"]
    score = {
        **normalized.score,
        "pass": passed,
        "checks": [*normalized.score["checks"], *capability_failures],
        "failed_checks": [
            *normalized.score["failed_checks"],
            *capability_failures,
        ],
    }
    return CaseExecution(
        case_key=str(getattr(case, "key")),
        score=score,
        turns=normalized.turns,
        events=normalized.events,
        tools=normalized.tools,
        facts=normalized.facts,
        infrastructure=infrastructure,
        resources=scope,
        setup_run_ids=tuple(str(item["run"]["id"]) for item in auxiliary_turns),
    )


async def _run_stage(stage: str, operation: Any) -> Any:
    try:
        return await operation
    except CaseStageError:
        raise
    except Exception as exc:
        raise CaseStageError(stage) from exc


def _normalize_case(
    *,
    case: object,
    turns: list[dict[str, Any]],
    auxiliary_turns: list[dict[str, Any]],
    subject_facts: dict[str, list[dict[str, Any]]],
) -> Any:
    try:
        return normalize_case(
            case=case,
            turns=turns,
            auxiliary_turns=auxiliary_turns,
            subject_facts=subject_facts,
        )
    except Exception as exc:
        raise CaseStageError("normalization") from exc


def _case_tool_names(case: object) -> tuple[str, ...]:
    requested = ("search_memory", *tuple(getattr(case, "required_tools", ())))
    return tuple(dict.fromkeys(str(name) for name in requested))


def _natural_fact_setup_message(fact: object) -> str:
    value = str(getattr(fact, "value", "")).strip()
    fact_type = str(getattr(fact, "fact_type", "")).strip()
    qualifier = str(getattr(fact, "qualifier", "") or "").strip()
    if fact_type == "person.name":
        return f"My name is {value}. Please remember it."
    if fact_type == "person.current_location":
        return f"I currently live in {value}. Please remember it."
    if fact_type == "person.preference" and qualifier:
        return f"My favorite {qualifier} is {value}. Please remember it."
    if fact_type == "person.shoe_size":
        return f"My shoe size is {value}. Please remember it."
    if fact_type == "pet.name":
        return f"My pet's name is {value}. Please remember it."
    if fact_type == "pet.breed":
        return f"My pet's breed is {value}. Please remember it."
    if fact_type == "relationship.person" and qualifier:
        return f"My {qualifier} is {value}. Please remember it."
    return f"Please remember this detail: {value}."


def _verify_public_initial_fact(
    *, response: dict[str, Any], subject_id: str, fact: object
) -> None:
    fact_type = str(getattr(fact, "fact_type", "")).strip()
    qualifier = str(getattr(fact, "qualifier", "") or "").strip() or None
    value = str(getattr(fact, "value", "")).strip()
    key = str(getattr(fact, "key", "")).strip()
    facts = response.get("facts")
    if not isinstance(facts, list):
        raise CaseStageError("initial_fact_memory_verification") from AssertionError()
    for observed in facts:
        if not isinstance(observed, dict):
            continue
        if observed.get("status") != "active" or observed.get("value") != value:
            continue
        if fact_type:
            observed_qualifier = (
                str(observed.get("qualifier") or "").strip().casefold() or None
            )
            if (
                observed.get("fact_type") == fact_type
                and observed_qualifier == qualifier
                and observed.get("entity_id") == subject_id
            ):
                return
        elif key and observed.get("key") == key:
            return
    raise CaseStageError("initial_fact_memory_verification") from AssertionError()


def _capability_checks(
    case: object,
    events: tuple[Any, ...],
    completed_turns: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not requires_versioned_summary(case):
        return []
    expected_messages: dict[str, int] = {}
    for prelude in tuple(getattr(case, "prelude_messages", ())):
        conversation_key = str(getattr(prelude, "conversation_key"))
        expected_messages[conversation_key] = expected_messages.get(
            conversation_key, 0
        ) + (2 * int(getattr(prelude, "count", 0)))
    for turn in tuple(getattr(case, "turns", ())):
        conversation_key = str(getattr(turn, "conversation_key"))
        expected_messages[conversation_key] = (
            expected_messages.get(conversation_key, 0) + 2
        )
    observed_messages: dict[str, int] = {}
    for turn in completed_turns:
        state_messages = (turn.get("conversation_state") or {}).get("messages")
        if isinstance(state_messages, list):
            observed_messages[str(turn["conversation_key"])] = len(state_messages)
    summary_observed = any(
        str(getattr(event, "event_type", "")) == "summary.committed" for event in events
    )
    raw_history_preserved = all(
        observed_messages.get(key, 0) >= expected
        for key, expected in expected_messages.items()
    )
    return [
        {
            "kind": "versioned_summary_committed",
            "pass": summary_observed,
        },
        {
            "kind": "raw_history_preserved",
            "expected_message_counts": expected_messages,
            "observed_message_counts": observed_messages,
            "pass": raw_history_preserved,
        },
    ]


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
    diagnostic: bool = False,
    resource_scope_sink: list[ResourceScope] | None = None,
    on_round_complete: Callable[[QualificationRound], QualificationRound] | None = None,
) -> tuple[QualificationRound, ...]:
    results: list[QualificationRound] = []
    for index in range(1, rounds + 1):
        executions: list[CaseExecution] = []
        for case in cases:
            case_scopes: list[ResourceScope] = []
            try:
                execution = await execute_case(
                    client=client,
                    case=case,
                    namespace=_resource_key(namespace, f"round-{index}"),
                    conversation_model_key=conversation_model_key,
                    reviewer_model_key=reviewer_model_key,
                    embedding_model_key=embedding_model_key,
                    timeout_seconds=timeout_seconds,
                    retry_count=retry_count,
                    resource_scope_sink=case_scopes,
                )
            except Exception as exc:
                execution = _failed_case_execution(case, exc, case_scopes)
            finally:
                if resource_scope_sink is not None:
                    resource_scope_sink.extend(case_scopes)
            executions.append(execution)
        materialized_executions = tuple(executions)
        fingerprints = _combined_fingerprints(materialized_executions)
        case_keys = tuple(item.case_key for item in materialized_executions)
        result = QualificationRound(
            index=index,
            kind="diagnostic" if diagnostic else "primary",
            execution_mode=("live-api-diagnostic" if diagnostic else execution_mode),
            complete_matrix=not diagnostic and case_keys == canonical_case_keys,
            passed=all(
                bool(item.score.get("pass")) for item in materialized_executions
            ),
            case_keys=case_keys,
            cases=materialized_executions,
            deployment_fingerprints=fingerprints,
        )
        results.append(on_round_complete(result) if on_round_complete else result)
        if not result.passed:
            # With a fixed three-round qualification window, any failed complete
            # round makes a promotion proposal impossible for this run.
            break
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
    executions: list[CaseExecution] = []
    for case in cases:
        case_scopes: list[ResourceScope] = []
        try:
            execution = await execute_case(
                client=client,
                case=case,
                namespace=_resource_key(namespace, "llama-compatibility"),
                conversation_model_key=conversation_model_key,
                reviewer_model_key=reviewer_model_key,
                embedding_model_key=embedding_model_key,
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
                resource_scope_sink=case_scopes,
            )
        except Exception as exc:
            execution = _failed_case_execution(case, exc, case_scopes)
        finally:
            if resource_scope_sink is not None:
                resource_scope_sink.extend(case_scopes)
        executions.append(execution)
    materialized_executions = tuple(executions)
    result = QualificationRound(
        index=1,
        kind="llama-compatibility",
        execution_mode="live-api",
        complete_matrix=False,
        passed=all(bool(item.score.get("pass")) for item in materialized_executions),
        case_keys=tuple(item.case_key for item in materialized_executions),
        cases=materialized_executions,
        deployment_fingerprints=_combined_fingerprints(materialized_executions),
    )
    return on_round_complete(result) if on_round_complete else result


async def _complete_setup_turn(
    client: RuntimeV3Client,
    conversation_id: str,
    content: str,
    namespace: str,
    timeout_seconds: float,
    retry_count: int,
    *,
    stage: str,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    accepted = await _run_stage(
        stage,
        client.accept_turn(
            conversation_id,
            content,
            _idempotency_key(namespace, "setup", _stable_content_index(content)),
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
        ),
    )
    run, events = await _run_stage(
        stage,
        _await_terminal_with_cancellation(
            client,
            accepted,
            timeout_seconds=timeout_seconds * (retry_count + 1) + 30,
        ),
    )
    if run.get("status") != "succeeded":
        raise CaseStageError(stage) from AssertionError()
    return run, events


async def _await_terminal_with_cancellation(
    client: RuntimeV3Client,
    accepted: dict[str, Any],
    *,
    timeout_seconds: float,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    try:
        return await client.await_terminal(accepted, timeout_seconds=timeout_seconds)
    except RunTimeout:
        return await _cancel_and_await_terminal(client, accepted)
    except BaseException:
        try:
            await _cancel_and_await_terminal(client, accepted)
        except Exception as cleanup_error:
            raise RuntimeError(
                "accepted v3 run could not be cancelled before cleanup"
            ) from cleanup_error
        raise


async def _cancel_and_await_terminal(
    client: RuntimeV3Client, accepted: dict[str, Any]
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    run_id = str(accepted["run_id"])
    await client.cancel_run(run_id)
    try:
        run, events = await client.await_terminal(accepted, timeout_seconds=30)
    except RunTimeout as exc:
        run = await client.get_run(run_id)
        events = ()
        if run.get("status") not in {"succeeded", "failed", "cancelled"}:
            raise RuntimeError(f"cancelled v3 run {run_id} did not terminate") from exc
    return run, events


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


def _failed_case_execution(
    case: object, exc: Exception, scopes: list[ResourceScope]
) -> CaseExecution:
    resources = ResourceScope(
        definition_keys=tuple(key for scope in scopes for key in scope.definition_keys),
        subject_external_keys=tuple(
            key for scope in scopes for key in scope.subject_external_keys
        ),
        deployment_fingerprints=_combined_scope_fingerprints(scopes),
        deployment_snapshots=tuple(
            snapshot for scope in scopes for snapshot in scope.deployment_snapshots
        ),
    )
    stage_error = exc if isinstance(exc, CaseStageError) else None
    cause = stage_error.__cause__ if stage_error is not None else exc
    stage = stage_error.stage if stage_error is not None else "case_execution"
    failure = {
        "kind": "case_execution_error",
        "stage": stage,
        "pass": False,
        "error_type": type(cause).__name__,
        "message": f"{stage.replace('_', ' ')} failed",
    }
    return CaseExecution(
        case_key=str(getattr(case, "key")),
        score={
            "case_key": str(getattr(case, "key")),
            "pass": False,
            "checks": [failure],
            "failed_checks": [failure],
        },
        turns=(),
        events=(),
        tools=(),
        facts=(),
        infrastructure={
            "failures": [failure],
            "terminal_statuses": [],
            "all_terminal": False,
        },
        resources=resources,
    )


def _combined_scope_fingerprints(scopes: list[ResourceScope]) -> dict[str, str]:
    combined: dict[str, str] = {}
    for scope in scopes:
        for role, fingerprint in scope.deployment_fingerprints.items():
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
