"""Hindsight reply contracts, independent from semantic Memory/Character judgments."""

import asyncio
import json
import time
import hashlib
from uuid import uuid4

import pytest

from ade_api.features.agent_runtime.context import ContextBudget, estimate_tokens
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.executor import ConversationExecutor, curated_tools
from ade_api.features.agent_runtime.hindsight_context import build_hindsight_context
from ade_api.features.agent_runtime.memory_progress import native_progress
from ade_api.features.agent_runtime.retry import is_retryable
from ade_api.features.agent_runtime.turn_recall import MemoryLookupError, TurnRecall
from ade_api.integrations.hindsight import HindsightError
from content.prompts.system.chat.chat_v20260516 import PROMPT as ORIGINAL_PROMPT
from content.prompts.system.chat.chat_v20261019 import PROMPT as HINDSIGHT_PROMPT


def test_native_progress_cannot_expose_error_bodies_or_task_payloads():
    child = str(uuid4())
    value = native_progress(
        {
            "status": "failed",
            "error_message": "secret response",
            "task_payload": {"credential": "secret"},
            "progress": {
                "stage": "storing",
                "processed": 1,
                "total": 15,
                "at": "2026-10-19T04:00:00+00:00",
                "detail": {"provider_error": "secret"},
            },
            "child_operations": [
                {
                    "operation_id": child,
                    "status": "failed",
                    "items_count": 1,
                    "error_message": "secret",
                }
            ],
        }
    )
    assert "secret" not in json.dumps(value)
    assert value["progress"]["processed"] == 1
    assert value["child_operations"] == [
        {"operation_id": child, "status": "failed", "items_count": 1}
    ]
    assert native_progress(
        {
            "status": "completed",
            "progress": {"stage": "secret", "at": "secret", "processed": True},
            "child_operations": [{"operation_id": "secret", "status": "completed"}],
        }
    ) == {"status": "completed", "progress": {}, "child_operations": []}


@pytest.mark.parametrize(
    "section", ["style", "basic_functions", "output_formatting_rules"]
)
def test_hindsight_prompt_changes_memory_contract_not_authored_dialogue_style(section):
    def body(prompt):
        return prompt.split(f"<{section}>", 1)[1].split(f"</{section}>", 1)[0]

    assert body(HINDSIGHT_PROMPT) == body(ORIGINAL_PROMPT)
    assert "update the human memory block immediately" not in HINDSIGHT_PROMPT
    assert "asynchronously" in HINDSIGHT_PROMPT


def test_required_lookup_failure_is_not_an_automatic_retry_or_empty_result():
    async def check():
        class Banks:
            async def ensure_ready(self, *args, **kwargs):
                pass

        class Native:
            async def recall(self, *args, **kwargs):
                raise HindsightError("hindsight_unavailable")

        recall = TurnRecall(
            banks=Banks(),
            client=Native(),
            bank_id="owned",
            deadline=time.monotonic() + 1,
        )
        with pytest.raises(MemoryLookupError) as failure:
            await recall.lookup("current input")
        assert not is_retryable(failure.value)
        assert not recall.observations

    asyncio.run(check())


def test_tool_recall_failure_propagates_before_any_apology_continuation():
    async def check():
        class Transport:
            calls = 0

            async def chat_completion(self, *args, **kwargs):
                self.calls += 1
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "id": "tool-1",
                                        "type": "function",
                                        "function": {
                                            "name": "search_memory",
                                            "arguments": '{"query":"earlier"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                }

        async def failed(query, limit):
            raise MemoryLookupError("hindsight_unavailable")

        transport = Transport()
        with pytest.raises(MemoryLookupError):
            await ConversationExecutor(transport).execute(
                model_key="fake::chat",
                messages=[{"role": "user", "content": "earlier"}],
                timeout_seconds=1,
                max_output_tokens=256,
                tools=curated_tools(["search_memory"], search_memory=failed),
                input_token_limit=2048,
            )
        assert transport.calls == 1

    asyncio.run(check())


def test_whole_serialized_tool_continuation_is_bounded():
    async def check():
        class Transport:
            calls = 0

            async def chat_completion(self, payload, **kwargs):
                self.calls += 1
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "tool_calls": [
                                    {
                                        "id": "tool-1",
                                        "type": "function",
                                        "function": {
                                            "name": "search_memory",
                                            "arguments": '{"query":"earlier"}',
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                }

        async def large(query, limit):
            return [{"id": "memory", "text": "x" * 30_000}]

        transport = Transport()
        with pytest.raises(RuntimeValidationError, match="Serialized conversation"):
            await ConversationExecutor(transport).execute(
                model_key="fake::chat",
                messages=[{"role": "user", "content": "earlier"}],
                timeout_seconds=1,
                max_output_tokens=256,
                tools=curated_tools(["search_memory"], search_memory=large),
                input_token_limit=2048,
            )
        assert transport.calls == 1

    asyncio.run(check())


def test_context_keeps_persona_input_attribution_and_serialized_bounds():
    budget = ContextBudget(
        context_window=4096,
        max_output_tokens=512,
        tool_schema_tokens=256,
        recent_tokens=100,
    )
    context = build_hindsight_context(
        definition={
            "id": "definition-version",
            "prompt_content": "Authored instructions",
            "persona_content": "Authored persona",
        },
        messages=[
            {
                "id": "older",
                "sequence": 1,
                "role": "user",
                "content": "Earlier user statement",
            }
        ],
        current_user={"id": "current", "sequence": 2, "content": "Exact current input"},
        summary=None,
        memories=[
            {
                "id": "memory",
                "text": "Solo character history",
                "type": "experience",
                "occurred_start": "2025-01-01",
            }
        ],
        budget=budget,
        tools={},
        provider_adapter="",
        model_key="fake::chat",
    )
    assert context.messages[-1] == {"role": "user", "content": "Exact current input"}
    assert "Authored persona" in context.messages[0]["content"]
    assert "reviewer" not in context.messages[0]["content"]
    assert "Solo character history" in context.messages[0]["content"]
    assert context.omitted_message_ids == []
    assert context.estimated_input_tokens <= budget.input_limit
    system = context.messages[0]["content"]
    offset = 0
    for component in context.components:
        text = context.messages[component["message_index"]]["content"][
            component["start"] : component["end"]
        ]
        assert hashlib.sha256(text.encode()).hexdigest() == component["sha256"]
        if component["message_index"] == 0:
            assert component["start"] == offset
            offset = component["end"]
    assert offset == len(system)
    assert (
        estimate_tokens(json.dumps(context.messages, ensure_ascii=False))
        <= budget.input_limit
    )
