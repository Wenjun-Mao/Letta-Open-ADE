from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .adapters import CustomLoopAdapter, PydanticAIAdapter
from .adapters.transport import HttpxChatCompletionsTransport
from .artifacts import StudyArtifactWriter, json_value
from .config import StudyConfig, public_config
from .contracts import ContextBudget, RuntimePolicy, TurnRequest
from .fixtures import StudyCase, load_cases, select_cases
from .memory import MemoryRetriever
from .memory_review import RouterMemoryReviewer
from .provenance import capture_provenance, capture_router_catalog
from .repository import InMemoryStudyRepository
from .runtime import StudyAgentRuntime, event_payload
from .semantic_retrieval import (
    EmbeddingClientConfig,
    OpenAICompatibleEmbeddingsClient,
    RetrievalConfig,
)
from .scoring import score_case
from .study_evidence import (
    build_qualification_evidence,
    run_semantic_retrieval_evaluation,
)
from .world import build_case_world


AdapterFactory = Callable[[], Any]
ReviewerFactory = Callable[[], Any]
RetrieverFactory = Callable[[InMemoryStudyRepository], MemoryRetriever]


def _adapter_factory(config: StudyConfig, adapter_name: str) -> AdapterFactory:
    if adapter_name == "custom_loop":
        return lambda: CustomLoopAdapter(
            HttpxChatCompletionsTransport(
                base_url=config.router_v1_base_url,
                api_key=config.router_api_key,
            )
        )
    if adapter_name == "pydantic_ai":
        return lambda: PydanticAIAdapter(
            base_url=config.router_v1_base_url,
            api_key=config.router_api_key,
        )
    raise ValueError(f"Unknown adapter: {adapter_name}")


async def run_live_study(
    config: StudyConfig,
    *,
    project_root: Path,
) -> dict[str, Any]:
    run_id = f"agent-runtime-study-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    all_cases = load_cases(config.fixture_path)
    cases = select_cases(all_cases, config.case_keys)
    rows: list[dict[str, Any]] = []
    with StudyArtifactWriter(config.output_dir, run_id) as writer:
        provenance = capture_provenance(project_root)
        provenance["effective_config"] = public_config(config)
        provenance["model_router_catalog"] = await capture_router_catalog(
            base_url=config.router_v1_base_url,
            api_key=config.router_api_key,
        )
        writer.write_provenance(provenance)
        embeddings = OpenAICompatibleEmbeddingsClient(
            EmbeddingClientConfig(
                base_url=config.embeddings_base_url,
                model=config.embeddings_model,
                dimensions=config.embedding_dimensions,
                timeout_seconds=config.embedding_timeout_seconds,
                api_key=config.embeddings_api_key or None,
                max_retries=0,
            )
        )
        retrieval_evidence = await asyncio.to_thread(
            run_semantic_retrieval_evaluation,
            config,
            embeddings=embeddings,
        )
        writer.write_retrieval(retrieval_evidence)
        calibrated_threshold = float(retrieval_evidence["calibration"]["threshold"])
        retriever_factory: RetrieverFactory = lambda repository: MemoryRetriever(
            repository,
            embeddings=embeddings,
            semantic_config=RetrievalConfig(
                strategy=config.retrieval_strategy,
                limit=config.policy.memory_search_limit,
                minimum_score=calibrated_threshold,
                query_instruction=config.retrieval_query_instruction,
            ),
        )
        reviewer_factory: ReviewerFactory = lambda: RouterMemoryReviewer(
            model_key=config.reviewer_model_key,
            base_url=config.router_v1_base_url,
            api_key=config.router_api_key,
            max_output_tokens=config.reviewer_max_output_tokens,
        )
        for adapter_name in config.adapters:
            factory = _adapter_factory(config, adapter_name)
            for model_key in config.models:
                for case in cases:
                    evidence = await run_case(
                        case=case,
                        model_key=model_key,
                        adapter_name=adapter_name,
                        adapter_factory=factory,
                        reviewer_factory=reviewer_factory,
                        retriever_factory=retriever_factory,
                        policy=config.policy,
                        writer=writer,
                    )
                    rows.append(evidence)
                    print(
                        f"[{adapter_name}] [{model_key}] {case.key}: "
                        f"pass={evidence['score']['pass']}",
                        flush=True,
                    )
        qualification_evidence = build_qualification_evidence(
            run_id=run_id,
            registry_path=config.deployment_registry_path,
            output_dir=config.output_dir,
            models=config.models,
            reviewer_model_key=config.reviewer_model_key,
            rows=rows,
            retrieval_evidence=retrieval_evidence,
            required_case_keys=tuple(case.key for case in all_cases),
            qualification_adapter="custom_loop",
            allow_unqualified_study_models=(config.allow_unqualified_study_models),
        )
        writer.write_qualification(qualification_evidence)
        row_passed = sum(1 for row in rows if row["score"]["pass"])
        gate_passed = int(bool(retrieval_evidence["acceptance"]["pass"])) + int(
            bool(qualification_evidence["study_gate_pass"])
        )
        summary = {
            "run_id": run_id,
            "kind": "live",
            "models": list(config.models),
            "adapters": list(config.adapters),
            "case_keys": [case.key for case in cases],
            "rows": rows,
            "total": len(rows) + 2,
            "passed": row_passed + gate_passed,
            "failed": len(rows) + 2 - row_passed - gate_passed,
            "retrieval_acceptance": retrieval_evidence["acceptance"],
            "qualification": qualification_evidence,
            "provenance_path": str(writer.provenance_path),
            "turns_path": str(writer.turns_path),
            "summary_path": str(writer.summary_path),
            "retrieval_path": str(writer.retrieval_path),
            "qualification_path": str(writer.qualification_path),
        }
        writer.write_summary(summary)
    return summary


async def run_case(
    *,
    case: StudyCase,
    model_key: str,
    adapter_name: str,
    adapter_factory: AdapterFactory,
    reviewer_factory: ReviewerFactory,
    retriever_factory: RetrieverFactory,
    policy: RuntimePolicy,
    writer: StudyArtifactWriter | None = None,
) -> dict[str, Any]:
    world = build_case_world(case, model_key=model_key)
    runtime = StudyAgentRuntime(
        repository=world.repository,
        executor=adapter_factory(),
        memory_reviewer=reviewer_factory(),
        memory_retriever=retriever_factory(world.repository),
    )
    case_policy = _case_policy(policy, case)
    results_by_conversation: dict[str, list] = {
        key: [] for key in world.conversation_ids
    }
    for turn_index, turn in enumerate(case.turns, 1):
        conversation_id = world.conversation_ids[turn.conversation_key]
        result = await runtime.run_turn(
            TurnRequest(
                conversation_id=conversation_id,
                user_content=turn.user,
                idempotency_key=f"{adapter_name}:{model_key}:{case.key}:{turn_index}",
                policy=case_policy,
            )
        )
        results_by_conversation[turn.conversation_key].append(result)
        if writer:
            writer.write_turn(
                {
                    "adapter": adapter_name,
                    "model_key": model_key,
                    "case_key": case.key,
                    "turn_index": turn_index,
                    "conversation_key": turn.conversation_key,
                    "user": turn.user,
                    "run": result.run,
                    "assistant": (
                        result.assistant_message.content
                        if result.assistant_message
                        else None
                    ),
                    "candidate_assistant": result.candidate_assistant_text,
                    "memory_revisions": result.memory_revisions,
                    "tool_executions": result.tool_executions,
                    "reasoning": result.reasoning,
                    "raw_model_messages": result.raw_model_messages,
                    "usage": result.usage,
                    "memory_review": result.memory_review,
                    "elapsed_seconds": result.elapsed_seconds,
                    "context": result.context,
                    "events": event_payload(result),
                }
            )
        if result.run.status.value != "succeeded":
            break

    facts_by_subject = {
        key: world.repository.list_subject_facts(subject_id, active_only=True)
        for key, subject_id in world.subject_ids.items()
    }
    score = score_case(
        case=case,
        facts_by_subject=facts_by_subject,
        results_by_conversation={
            key: tuple(values) for key, values in results_by_conversation.items()
        },
    )
    role_scores = score.pop("role_scores")
    all_facts = {
        key: world.repository.list_subject_facts(subject_id, active_only=False)
        for key, subject_id in world.subject_ids.items()
    }
    revisions = {
        fact.id: tuple(world.repository.revisions.get(fact.id, ()))
        for facts in all_facts.values()
        for fact in facts
    }
    return {
        "adapter": adapter_name,
        "model_key": model_key,
        "case_key": case.key,
        "description": case.description,
        "score": score,
        "role_scores": role_scores,
        "active_facts": json_value(facts_by_subject),
        "all_facts": json_value(all_facts),
        "revisions": json_value(revisions),
        "raw_message_counts": {
            key: len(world.repository.list_messages(conversation_id))
            for key, conversation_id in world.conversation_ids.items()
        },
        "summary_versions": {
            key: len(world.repository.list_summary_versions(conversation_id))
            for key, conversation_id in world.conversation_ids.items()
        },
    }


def _case_policy(policy: RuntimePolicy, case: StudyCase) -> RuntimePolicy:
    if case.profile_token_override is None:
        return policy
    budget: ContextBudget = replace(
        policy.context_budget, profile_tokens=case.profile_token_override
    )
    return replace(policy, context_budget=budget)


def printable_summary(summary: dict[str, Any]) -> str:
    return (
        f"run_id: {summary['run_id']}\n"
        f"passed: {summary['passed']}/{summary['total']}\n"
        f"summary: {summary['summary_path']}"
    )
