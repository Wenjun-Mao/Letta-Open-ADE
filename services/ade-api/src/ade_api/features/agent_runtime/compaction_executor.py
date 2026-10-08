"""Dispatch the existing summary protocol through the bound model transport."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .compaction import (
    COMPACTION_RESPONSE_SCHEMA,
    COMPACTION_SYSTEM,
    CompactionPlan,
    ModelCompaction,
    compaction_content_sha256,
    compaction_input_sha256,
    compaction_model_input_json,
    compaction_policy_sha256,
    compaction_prompt_sha256,
    parse_compaction_response,
)
from .model_response import first_choice, merge_usage
from .provider_tracing import safe_provider_request_id
from .router_transport import RouterTransport


class CompactionExecutor:
    def __init__(
        self, transport: RouterTransport, *, provider_adapter: str = ""
    ) -> None:
        self.transport = transport
        self.provider_adapter = provider_adapter

    async def compact(
        self,
        *,
        model_key: str,
        model_fingerprint: str,
        plan: CompactionPlan,
        timeout_seconds: float,
        max_output_tokens: int,
        summary_token_budget: int,
        observe_request: Callable[[dict[str, Any]], None] | None = None,
    ) -> ModelCompaction:
        compaction_system = COMPACTION_SYSTEM
        if self.provider_adapter == "deepseek_openai":
            compaction_system += (
                "\nReturn a JSON object matching this schema: "
                f"{json.dumps(COMPACTION_RESPONSE_SCHEMA, ensure_ascii=False)}"
                '\nExample JSON: {"summary":"A concise factual summary."}'
            )
        payload = {
            "model": model_key,
            "messages": [
                {"role": "system", "content": compaction_system},
                {"role": "user", "content": compaction_model_input_json(plan)},
            ],
            "max_tokens": max(
                256,
                min(
                    max_output_tokens,
                    4096 if self.provider_adapter == "deepseek_openai" else 1024,
                ),
            ),
            "stream": False,
        }
        if self.provider_adapter == "deepseek_openai":
            payload.update(
                {
                    "thinking": {"type": "enabled"},
                    "reasoning_effort": "high",
                    "response_format": {"type": "json_object"},
                }
            )
        else:
            payload.update(
                {
                    "temperature": 0,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "ade_conversation_compaction",
                            "strict": True,
                            "schema": COMPACTION_RESPONSE_SCHEMA,
                        },
                    },
                    "chat_template_kwargs": {"enable_thinking": False},
                }
            )
        if observe_request is not None:
            observe_request(payload)
        response = await self.transport.chat_completion(
            payload, timeout_seconds=timeout_seconds
        )
        message, _ = first_choice(response)
        content = parse_compaction_response(
            str(message.get("content", "") or "").strip(),
            summary_token_budget=summary_token_budget,
        )
        usage: dict[str, int] = {}
        merge_usage(usage, response.get("usage"))
        provider_request_id = safe_provider_request_id(response.get("id"))
        return ModelCompaction(
            plan=plan,
            content=content,
            model_key=model_key,
            model_fingerprint=model_fingerprint,
            provider_request_id=provider_request_id,
            content_sha256=compaction_content_sha256(content),
            prompt_sha256=compaction_prompt_sha256(compaction_system),
            input_sha256=compaction_input_sha256(plan),
            policy_sha256=compaction_policy_sha256(compaction_system),
            usage=usage,
        )
