"""Candidate discovery, binding, and native generation packet contracts."""

from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

from ade_api.features.agent_runtime.context import (
    ContextBudget,
    ConversationHistoryMetadata,
)
from ade_api.features.agent_runtime.executor import (
    ConversationExecutor,
    curated_tools,
    initial_conversation_request,
)
from ade_api.features.agent_runtime.history_admission import admit_history
from ade_api.features.agent_runtime.natural_context import build_natural_context
from ade_api.features.prompt_center import build_prompt_template_reader
from workflows.evals.character_memory_dev.history_target_diagnostic import (
    OLD_MANIFESTS,
    PRIOR_DIAGNOSTIC,
    SCHEDULE,
    frozen_schedule,
    prior_diagnostic,
)
from workflows.evals.character_memory_dev.history_target_diagnostic_run import (
    CANDIDATE_PROMPT_KEY,
    GENERATION_BINDING,
    generation_binding,
    verified_generation_binding,
)
from workflows.evals.character_memory_dev.natural_live_results import sha256_file
from workflows.evals.deepseek_dev_smoke.isolation import ROOT


def _templates(tmp_path):
    registry = build_prompt_template_reader(
        ROOT, persona_db_path=tmp_path / "persona.sqlite3"
    )
    keys = {item["key"] for item in registry.list_templates("prompt", scenario="chat")}
    assert {"chat_v20260516", CANDIDATE_PROMPT_KEY} <= keys
    old = registry.get_template("prompt", "chat_v20260516", scenario="chat")
    candidate = registry.get_template("prompt", CANDIDATE_PROMPT_KEY, scenario="chat")
    persona = registry.get_template("persona", "chat_linxiaotang", scenario="chat")
    assert old and candidate and persona
    return old, candidate, persona


def _history():
    user = "我以前喜欢茉莉花茶。"
    assistant = "那时你提过茉莉花茶。"
    return {
        "run_id": "earlier-run",
        "conversation_id": "earlier-conversation",
        "definition_version_id": "earlier-definition",
        "archived": True,
        "messages": [
            {
                "id": f"earlier-{role}",
                "role": role,
                "content": content,
                "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
                "created_at": "2026-01-01T00:00:00+00:00",
                "sequence": sequence,
            }
            for sequence, (role, content) in enumerate(
                (("user", user), ("assistant", assistant)), start=1
            )
        ],
        "annotations": {
            "links": [],
            "facts": [],
            "revisions": [],
            "predecessor_edges": [],
        },
    }


def _packet(candidate, persona, *, user_text):
    current = {
        "id": "current-user",
        "role": "user",
        "content": user_text,
        "sequence": 3,
    }
    facts = [
        {
            "id": key,
            "subject_id": "subject",
            "entity_id": key,
            "fact_type": "pet.name",
            "qualifier": None,
            "normalized_key": f"pet.name|{key}",
            "value": value,
            "status": "active",
            "version": 1,
        }
        for key, value in (("dog-roxy", "Roxy"), ("dog-nini", "Nini"))
    ]
    facts.append(
        {
            "id": "forgotten-tea",
            "subject_id": "subject",
            "entity_id": "subject",
            "fact_type": "person.preference",
            "qualifier": "tea",
            "normalized_key": "person.preference|tea",
            "value": "茉莉花茶",
            "status": "inactive",
            "version": 2,
        }
    )
    entities = [
        {"id": "subject", "kind": "subject", "label": ""},
        {"id": "dog-roxy", "kind": "pet", "label": "Roxy"},
        {"id": "dog-nini", "kind": "pet", "label": "Nini"},
    ]
    context = build_natural_context(
        variant="B",
        system_prompt=candidate["content"],
        persona=persona["content"],
        current_user=current,
        eligible_recent_messages=[],
        lifecycle_facts=facts,
        retrieved_facts=facts,
        entities=entities,
        summary_content="",
        history_metadata=ConversationHistoryMetadata(0, 0),
        budget=ContextBudget(16384, 4096, 256),
        reviewer_suffix_limit=640,
    )
    return context.context, current, facts, entities


def test_candidate_and_old_prompt_are_distinct_immutable_sources(tmp_path) -> None:
    old, candidate, _ = _templates(tmp_path)
    assert old["content"] != candidate["content"]
    assert "memory blocks" in old["content"]
    assert "memory blocks" not in candidate["content"]
    frozen = json.loads(GENERATION_BINDING.read_text())
    assert (
        hashlib.sha256(candidate["content"].encode()).hexdigest()
        == frozen["component_sha256"]["candidate_prompt"]
    )


def test_attribution_changes_cannot_reuse_prior_diagnostic_binding(tmp_path) -> None:
    old, candidate, persona = _templates(tmp_path)
    if not all(path.is_file() for path, _ in OLD_MANIFESTS):
        pytest.skip("ignored historical H4 manifests are unavailable")
    schedule, _, old_manifest = frozen_schedule()
    prior_manifest = prior_diagnostic()
    assert (
        hashlib.sha256(old["content"].encode()).hexdigest()
        == old_manifest["prompt_sha256"]
    )
    binding = generation_binding(
        candidate,
        persona,
        old_manifest,
        prior_manifest,
        schedule,
        schedule_sha256=sha256_file(SCHEDULE),
        historical_manifest_sha256=[item[1] for item in OLD_MANIFESTS],
        prior_diagnostic_manifest_sha256=PRIOR_DIAGNOSTIC[1],
    )
    assert (
        binding["component_sha256"]["candidate_prompt"]
        != binding["prior_prompt_sha256"]
    )
    frozen = json.loads(GENERATION_BINDING.read_text())
    assert (
        binding["component_sha256"]["memory_control"]
        != frozen["component_sha256"]["memory_control"]
    )
    assert (
        binding["reviewer_instruction_sha256"] != frozen["reviewer_instruction_sha256"]
    )
    assert binding["reviewer_schema_sha256"] == frozen["reviewer_schema_sha256"]
    with pytest.raises(RuntimeError, match="reviewer, persona or old prompt changed"):
        verified_generation_binding(
            candidate,
            persona,
            old_manifest,
            prior_manifest,
            schedule,
            schedule_sha256=sha256_file(SCHEDULE),
            historical_manifest_sha256=[item[1] for item in OLD_MANIFESTS],
            prior_diagnostic_manifest_sha256=PRIOR_DIAGNOSTIC[1],
        )


def test_assembled_packets_with_and_without_admitted_history(tmp_path) -> None:
    old, candidate, persona = _templates(tmp_path)
    base, current, facts, entities = _packet(
        candidate, persona, user_text="你还记得我以前提过什么茶吗？"
    )
    tools = curated_tools(("search_memory",), search_memory=_empty_search)
    plain = initial_conversation_request(
        model_key="deepseek::deepseek-flash",
        messages=base.messages,
        max_output_tokens=4096,
        tools=tools,
        provider_adapter="deepseek_openai",
    )
    assert "Historical evidence (read-only)" not in plain["messages"][0]["content"]
    assert "attributed conversation" in plain["messages"][0]["content"]
    assert "materially plausible alternative" in plain["messages"][0]["content"]
    assert "saved fact descriptors" in plain["tools"][0]["function"]["description"]
    assert "茉莉花茶" in plain["messages"][0]["content"]  # inactive, not current

    admission = admit_history(
        base=base,
        ranked_exchanges=[_history()],
        current_user=current,
        source_messages=[current],
        facts=facts,
        entities=entities,
        generation_model_key="deepseek::deepseek-flash",
        generation_adapter="deepseek_openai",
        generation_tools=tools,
        generation_input_limit=11213,
        generation_max_output_tokens=4096,
        reviewer_model_key="deepseek::deepseek-flash",
        reviewer_adapter="deepseek_openai",
        reviewer_input_limit=11469,
        reviewer_max_output_tokens=4096,
    )
    assert len(admission.exchanges) == 1
    with_history = initial_conversation_request(
        model_key="deepseek::deepseek-flash",
        messages=admission.context.messages,
        max_output_tokens=4096,
        tools=tools,
        provider_adapter="deepseek_openai",
    )
    system = with_history["messages"][0]["content"]
    assert "Historical evidence (read-only)" in system
    assert "我以前喜欢茉莉花茶" in system
    assert "empty saved-fact search does not negate supplied dialogue" in system
    assert "history alone cannot revive it as current" in system
    old_base, old_current, old_facts, old_entities = _packet(
        old, persona, user_text="你还记得我以前提过什么茶吗？"
    )
    old_admission = admit_history(
        base=old_base,
        ranked_exchanges=[_history()],
        current_user=old_current,
        source_messages=[old_current],
        facts=old_facts,
        entities=old_entities,
        generation_model_key="deepseek::deepseek-flash",
        generation_adapter="deepseek_openai",
        generation_tools=tools,
        generation_input_limit=11213,
        generation_max_output_tokens=4096,
        reviewer_model_key="deepseek::deepseek-flash",
        reviewer_adapter="deepseek_openai",
        reviewer_input_limit=11469,
        reviewer_max_output_tokens=4096,
    )
    assert len(old_admission.exchanges) == 1
    assert (
        admission.context.estimated_input_tokens
        < old_admission.context.estimated_input_tokens
    )
    for user_text in ("它现在叫小黑。", "Roxy 现在叫小黑。"):
        dog_context, _, _, _ = _packet(candidate, persona, user_text=user_text)
        dog_payload = initial_conversation_request(
            model_key="deepseek::deepseek-flash",
            messages=dog_context.messages,
            max_output_tokens=4096,
            tools=tools,
            provider_adapter="deepseek_openai",
        )
        assert dog_payload["messages"][-1]["content"] == user_text
        assert "Answer clear references" in dog_payload["messages"][0]["content"]


async def _empty_search(_query: str, _limit: int) -> list[dict]:
    return []


def test_empty_saved_fact_tool_continuation_keeps_admitted_testimony(tmp_path) -> None:
    _, candidate, persona = _templates(tmp_path)
    base, current, facts, entities = _packet(
        candidate, persona, user_text="你还记得我以前提过什么茶吗？"
    )
    tools = curated_tools(("search_memory",), search_memory=_empty_search)
    admitted = admit_history(
        base=base,
        ranked_exchanges=[_history()],
        current_user=current,
        source_messages=[current],
        facts=facts,
        entities=entities,
        generation_model_key="deepseek::deepseek-flash",
        generation_adapter="deepseek_openai",
        generation_tools=tools,
        generation_input_limit=11213,
        generation_max_output_tokens=4096,
        reviewer_model_key="deepseek::deepseek-flash",
        reviewer_adapter="deepseek_openai",
        reviewer_input_limit=11469,
        reviewer_max_output_tokens=4096,
    )

    class Transport:
        def __init__(self):
            self.requests = []

        async def chat_completion(self, payload, *, timeout_seconds):
            self.requests.append(payload)
            if len(self.requests) == 1:
                message = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "search_memory",
                                "arguments": '{"query":"茉莉花茶"}',
                            },
                        }
                    ],
                }
                reason = "tool_calls"
            else:
                message = {"role": "assistant", "content": "你以前提过茉莉花茶。"}
                reason = "stop"
            return {
                "id": f"reply-{len(self.requests)}",
                "choices": [{"message": message, "finish_reason": reason}],
            }

    transport = Transport()
    result = asyncio.run(
        ConversationExecutor(transport, provider_adapter="deepseek_openai").execute(
            model_key="deepseek::deepseek-flash",
            messages=admitted.context.messages,
            tools=tools,
            timeout_seconds=30,
            max_output_tokens=4096,
            input_token_limit=11213,
        )
    )
    assert result.model_request_count == 2
    assert result.tool_evidence[0]["content"]["facts"] == []
    continuation = transport.requests[1]
    assert "我以前喜欢茉莉花茶" in continuation["messages"][0]["content"]
    assert json.loads(continuation["messages"][-1]["content"])["facts"] == []
    assert result.assistant_text == "你以前提过茉莉花茶。"
