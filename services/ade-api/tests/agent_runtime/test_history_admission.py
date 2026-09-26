"""H3 packet and read-only reviewer contracts without provider dispatch."""

from __future__ import annotations

import asyncio
import hashlib
import json

import pytest

from ade_api.features.agent_runtime.context import BuiltContext
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.executor import initial_conversation_request
from ade_api.features.agent_runtime.history_admission import (
    HISTORY_DATA_INSTRUCTION,
    HistoryProbe,
    admit_history,
)
from ade_api.features.agent_runtime.natural_memory_binding import (
    build_natural_binding_map,
)
from ade_api.features.agent_runtime.natural_memory_policy import (
    prepare_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_review import (
    parse_natural_review_decision,
)
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    NaturalMemoryReviewer,
    natural_review_request,
    serialized_review_tokens,
)


SUBJECT = "00000000-0000-0000-0000-000000000001"
CURRENT = {
    "id": "00000000-0000-0000-0000-000000000002",
    "role": "user",
    "content": "你还记得吗？我现在住在 Toronto。",
    "sequence": 3,
}
ENTITIES = [{"id": SUBJECT, "subject_id": SUBJECT, "kind": "subject"}]


def test_automatic_arm_requires_frozen_selector_before_execution() -> None:
    with pytest.raises(RuntimeValidationError) as error:
        HistoryProbe(arm="automatic_history")
    assert error.value.detail_code == "natural_history_selector_unavailable"


def _exchange(user: str = '我说："早上喜欢咖啡。"') -> dict:
    assistant = "我记得你当时这样说。"

    def message(role: str, content: str, sequence: int) -> dict:
        return {
            "id": f"history-{role}-{sequence}",
            "role": role,
            "content": content,
            "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "created_at": "2026-01-01T00:00:00+00:00",
            "sequence": sequence,
        }

    return {
        "run_id": "history-run",
        "conversation_id": "history-conversation",
        "definition_version_id": "history-definition",
        "archived": True,
        "messages": [message("user", user, 1), message("assistant", assistant, 2)],
        "annotations": {
            "links": [],
            "facts": [],
            "revisions": [],
            "predecessor_edges": [],
        },
    }


def _prepared(decisions: list[dict], *, exchange: dict | None = None) -> None:
    binding = build_natural_binding_map(
        current_user_message=CURRENT,
        source_messages=[CURRENT],
        facts=[],
        entities=ENTITIES,
        history_exchanges=[exchange or _exchange()],
    )
    prepare_natural_memory_review(
        decision=parse_natural_review_decision({"decisions": decisions}),
        subject_id=SUBJECT,
        current_user_message=CURRENT,
        available_messages=[CURRENT],
        facts=[],
        entities=ENTITIES,
        candidate_reply="你一直喜欢早上咖啡。",
        binding_map=binding,
    )


WRITE = {
    "kind": "subject_add",
    "fact_type": "person.current_location",
    "value": "Toronto",
    "evidence": {"mode": "direct", "current_quote": "我现在住在 Toronto"},
}
CONFLICT = {
    "kind": "conflict",
    "current_quote": "你还记得吗",
    "candidate_reply_quote": "你一直喜欢早上咖啡",
    "history": {"handle": "H1", "quote": "早上喜欢咖啡。"},
}


@pytest.mark.parametrize("decisions", [[CONFLICT, WRITE], [WRITE, CONFLICT]])
def test_h_conflict_rejects_valid_sibling_in_either_order(
    decisions: list[dict],
) -> None:
    with pytest.raises(RuntimeValidationError) as error:
        _prepared(decisions)
    assert error.value.detail_code == "natural_memory_reply_conflict"


def test_unknown_or_ambiguous_h_span_fails_binding() -> None:
    with pytest.raises(RuntimeValidationError) as unknown:
        _prepared(
            [{**CONFLICT, "history": {"handle": "H9", "quote": "早上喜欢咖啡。"}}]
        )
    assert unknown.value.detail_code == "natural_review_binding"
    repeated = _exchange("早上喜欢咖啡。早上喜欢咖啡。")
    with pytest.raises(RuntimeValidationError) as ambiguous:
        _prepared([CONFLICT], exchange=repeated)
    assert ambiguous.value.detail_code == "natural_review_binding"


def test_h_cannot_be_write_support_or_target() -> None:
    with pytest.raises(RuntimeValidationError) as support:
        parse_natural_review_decision(
            {
                "decisions": [
                    {
                        **WRITE,
                        "evidence": {
                            "mode": "resolve_user",
                            "current_quote": "我现在住在 Toronto",
                            "support_handle": "H1",
                            "support_quote": "早上喜欢咖啡。",
                        },
                    }
                ]
            }
        )
    assert support.value.detail_code == "natural_review_schema"
    with pytest.raises(RuntimeValidationError) as target:
        parse_natural_review_decision(
            {
                "decisions": [
                    {
                        "kind": "forget",
                        "target": "H1",
                        "evidence": {"mode": "direct", "current_quote": "你还记得吗"},
                    }
                ]
            }
        )
    assert target.value.detail_code == "natural_review_schema"


def test_same_chinese_history_packet_in_generation_and_review() -> None:
    exchange = _exchange()
    base = BuiltContext(
        messages=[
            {"role": "system", "content": "Stay in character."},
            {"role": "user", "content": CURRENT["content"]},
        ],
        section_tokens={},
        omitted_message_ids=[],
        retrieved_fact_ids=[],
        estimated_input_tokens=0,
    )
    admission = admit_history(
        base=base,
        ranked_exchanges=[exchange],
        current_user=CURRENT,
        source_messages=[CURRENT],
        facts=[],
        entities=ENTITIES,
        generation_model_key="deepseek::deepseek-flash",
        generation_adapter="deepseek_openai",
        generation_tools={},
        generation_input_limit=10_000,
        generation_max_output_tokens=512,
        reviewer_model_key="deepseek::deepseek-flash",
        reviewer_adapter="deepseek_openai",
        reviewer_input_limit=100_000,
        reviewer_max_output_tokens=4096,
    )
    assert len(admission.exchanges) == 1
    review = natural_review_request(
        model_key="deepseek::deepseek-flash",
        provider_adapter="deepseek_openai",
        current_user_message=CURRENT,
        source_messages=[CURRENT],
        facts=[],
        entities=ENTITIES,
        candidate_reply="我记得。",
        history_exchanges=list(admission.exchanges),
        history_capable=True,
    )
    packet = json.loads(review["messages"][1]["content"])
    wire = json.dumps(packet["history"], ensure_ascii=False, separators=(",", ":"))
    assert wire in admission.context.messages[0]["content"]
    assert packet["eligible_support"] == []
    assert packet["history"][0]["messages"][0]["handle"] == "H1"


def test_long_annotation_omits_whole_exchange() -> None:
    exchange = _exchange()
    exchange["annotations"]["note"] = "x" * 20_000
    base = BuiltContext(
        messages=[
            {"role": "system", "content": "Prompt"},
            {"role": "user", "content": CURRENT["content"]},
        ],
        section_tokens={},
        omitted_message_ids=[],
        retrieved_fact_ids=[],
        estimated_input_tokens=0,
    )
    admission = admit_history(
        base=base,
        ranked_exchanges=[exchange],
        current_user=CURRENT,
        source_messages=[CURRENT],
        facts=[],
        entities=ENTITIES,
        generation_model_key="deepseek::deepseek-flash",
        generation_adapter="deepseek_openai",
        generation_tools={},
        generation_input_limit=1000,
        generation_max_output_tokens=512,
        reviewer_model_key="deepseek::deepseek-flash",
        reviewer_adapter="deepseek_openai",
        reviewer_input_limit=100_000,
        reviewer_max_output_tokens=4096,
    )
    assert admission.exchanges == ()
    assert admission.omitted_capacity == ("history-run",)


def test_paired_serialized_base_packets_differ_only_by_history() -> None:
    base = BuiltContext(
        messages=[
            {"role": "system", "content": "Stay in character."},
            {"role": "user", "content": CURRENT["content"]},
        ],
        section_tokens={},
        omitted_message_ids=[],
        retrieved_fact_ids=[],
        estimated_input_tokens=0,
    )

    def admit(exchanges):
        return admit_history(
            base=base,
            ranked_exchanges=exchanges,
            current_user=CURRENT,
            source_messages=[CURRENT],
            facts=[],
            entities=ENTITIES,
            generation_model_key="deepseek::deepseek-flash",
            generation_adapter="deepseek_openai",
            generation_tools={},
            generation_input_limit=10_000,
            generation_max_output_tokens=512,
            reviewer_model_key="deepseek::deepseek-flash",
            reviewer_adapter="deepseek_openai",
            reviewer_input_limit=100_000,
            reviewer_max_output_tokens=4096,
        )

    empty, automatic = admit([]), admit([_exchange()])

    def generation(admission):
        payload = initial_conversation_request(
            model_key="deepseek::deepseek-flash",
            messages=admission.context.messages,
            max_output_tokens=512,
            tools={},
            provider_adapter="deepseek_openai",
        )
        payload["messages"][0]["content"] = payload["messages"][0]["content"].split(
            "\nHistorical evidence (read-only):", 1
        )[0]
        return payload

    assert generation(empty) == generation(automatic)
    assert HISTORY_DATA_INSTRUCTION in generation(empty)["messages"][0]["content"]

    def review(admission):
        payload = natural_review_request(
            model_key="deepseek::deepseek-flash",
            provider_adapter="deepseek_openai",
            current_user_message=CURRENT,
            source_messages=[CURRENT],
            facts=[],
            entities=ENTITIES,
            candidate_reply="Okay.",
            max_output_tokens=4096,
            history_exchanges=list(admission.exchanges),
            history_capable=True,
        )
        packet = json.loads(payload["messages"][1]["content"])
        packet["history"] = []
        payload["messages"][1]["content"] = json.dumps(packet, ensure_ascii=False)
        return payload

    assert review(empty) == review(automatic)


def test_actual_h_reviewer_overflow_rejects_without_stripping_or_dispatch() -> None:
    exchange = _exchange()
    short = natural_review_request(
        model_key="deepseek::deepseek-flash",
        provider_adapter="deepseek_openai",
        current_user_message=CURRENT,
        source_messages=[CURRENT],
        facts=[],
        entities=ENTITIES,
        candidate_reply="Okay.",
        history_exchanges=[exchange],
        history_capable=True,
    )

    class NoDispatch:
        calls = 0

        async def chat_completion(self, _payload, *, timeout_seconds):
            self.calls += 1
            raise AssertionError("overflow must not dispatch")

    transport = NoDispatch()
    with pytest.raises(RuntimeValidationError) as error:
        asyncio.run(
            NaturalMemoryReviewer(
                transport,
                provider_adapter="deepseek_openai",  # type: ignore[arg-type]
            ).review(
                model_key="deepseek::deepseek-flash",
                current_user_message=CURRENT,
                source_messages=[CURRENT],
                facts=[],
                entities=ENTITIES,
                candidate_reply="x" * 8000,
                timeout_seconds=10,
                validate_decision=lambda _decision: None,
                input_token_limit=serialized_review_tokens(short) + 100,
                binding_map=build_natural_binding_map(
                    current_user_message=CURRENT,
                    source_messages=[CURRENT],
                    facts=[],
                    entities=ENTITIES,
                    history_exchanges=[exchange],
                ),
                history_capable=True,
            )
        )
    assert error.value.detail_code == "natural_reviewer_capacity"
    assert transport.calls == 0
