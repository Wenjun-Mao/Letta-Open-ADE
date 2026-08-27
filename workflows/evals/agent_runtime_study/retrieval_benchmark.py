from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import uuid4

from .contracts import (
    AgentDefinition,
    Conversation,
    MemoryEpisode,
    MemoryOperation,
    MemoryProposal,
    MemorySubject,
    MessageRole,
)
from .memory import MemoryPolicy, MemoryRetriever
from .repository import InMemoryStudyRepository


@dataclass(frozen=True)
class RetrievalCase:
    key: str
    query: str
    expected_item_id: str


def run_retrieval_benchmark() -> dict[str, object]:
    repository = InMemoryStudyRepository()
    repository.add_agent_definition(
        AgentDefinition(
            id="agent_retrieval",
            name="retrieval",
            model_key="scripted",
            system_prompt="study",
            persona="study",
            tool_names=(),
        )
    )
    repository.add_subject(
        MemorySubject(id="subject_retrieval", external_key="retrieval")
    )
    repository.add_conversation(
        Conversation(
            id="conversation_retrieval",
            agent_definition_id="agent_retrieval",
            memory_subject_id="subject_retrieval",
        )
    )
    policy = MemoryPolicy(repository)
    fact_ids: dict[str, str] = {}
    for key, value in (
        ("dog_breed", "Rocky is a Husky"),
        ("home_city", "Toronto"),
        ("favorite_museum", "Royal Ontario Museum"),
    ):
        source = repository.append_message(
            conversation_id="conversation_retrieval",
            role=MessageRole.USER,
            content=value,
            run_id="retrieval_seed",
        )
        revision = policy.apply_batch(
            subject_id="subject_retrieval",
            proposals=(
                MemoryProposal(
                    operation=MemoryOperation.ADD,
                    key=key,
                    value=value,
                    evidence_quote=value,
                ),
            ),
            source_messages=(source,),
            run_id="retrieval_seed",
        )[0]
        fact_ids[key] = revision.fact_id
    episode_sources = tuple(
        repository.append_message(
            conversation_id="conversation_retrieval",
            role=MessageRole.USER,
            content=content,
            run_id="episode_seed",
        )
        for content in (
            "My first jazz concert was at Massey Hall.",
            "I took a memorable road trip to Montreal in spring.",
        )
    )
    episodes = (
        MemoryEpisode(
            id="episode_concert",
            subject_id="subject_retrieval",
            conversation_id="conversation_retrieval",
            content="The user's first jazz concert was at Massey Hall.",
            source_message_ids=(episode_sources[0].id,),
        ),
        MemoryEpisode(
            id="episode_roadtrip",
            subject_id="subject_retrieval",
            conversation_id="conversation_retrieval",
            content="The user took a memorable road trip to Montreal in spring.",
            source_message_ids=(episode_sources[1].id,),
        ),
    )
    for episode in episodes:
        repository.add_episode(episode)
    cases = (
        RetrievalCase("durable_pet", "What breed is Rocky?", fact_ids["dog_breed"]),
        RetrievalCase("durable_city", "Which city is home?", fact_ids["home_city"]),
        RetrievalCase(
            "cross_lingual_museum",
            "我最喜欢哪一家博物馆？",
            fact_ids["favorite_museum"],
        ),
        RetrievalCase(
            "episodic_concert", "Where was the first jazz concert?", "episode_concert"
        ),
        RetrievalCase(
            "episodic_trip", "Where did the spring road trip go?", "episode_roadtrip"
        ),
    )
    retriever = MemoryRetriever(repository)

    def evaluate(include_episodes: bool) -> tuple[int, float, list[dict[str, object]]]:
        started = time.perf_counter()
        rows = []
        hits = 0
        for case in cases:
            facts = retriever.search_facts("subject_retrieval", case.query, limit=4)
            found_ids = [fact.id for fact in facts]
            if include_episodes:
                found_ids.extend(
                    episode.id
                    for episode in retriever.search_episodes(
                        "subject_retrieval", case.query, limit=4
                    )
                )
            passed = case.expected_item_id in found_ids
            hits += int(passed)
            rows.append(
                {
                    "case_key": case.key,
                    "expected_item_id": case.expected_item_id,
                    "found_item_ids": found_ids,
                    "pass": passed,
                }
            )
        elapsed_ms = (time.perf_counter() - started) * 1000
        return hits, elapsed_ms, rows

    fact_hits, fact_latency, fact_rows = evaluate(False)
    episode_hits, episode_latency, episode_rows = evaluate(True)
    improvement = (episode_hits - fact_hits) / len(cases)
    overhead_ms = max(0.0, episode_latency - fact_latency)
    materially_improves = improvement >= 0.20 and overhead_ms < 5.0
    return {
        "benchmark_id": f"retrieval_{uuid4().hex[:8]}",
        "case_count": len(cases),
        "fact_only": {
            "hits": fact_hits,
            "recall": fact_hits / len(cases),
            "latency_ms": round(fact_latency, 6),
            "rows": fact_rows,
        },
        "fact_plus_episode": {
            "hits": episode_hits,
            "recall": episode_hits / len(cases),
            "latency_ms": round(episode_latency, 6),
            "rows": episode_rows,
        },
        "recall_improvement": improvement,
        "measured_overhead_ms": round(overhead_ms, 6),
        "materially_improves": materially_improves,
        "recommendation": (
            "retain_optional_episode_contract"
            if materially_improves
            else "defer_episode_persistence"
        ),
    }
