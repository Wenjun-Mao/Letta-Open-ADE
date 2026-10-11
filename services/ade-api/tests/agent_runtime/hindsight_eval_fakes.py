"""Synthetic inputs and fake HTTP providers for the Hindsight boundary."""

import asyncio
import json
import httpx
from ade_api.features.agent_runtime import hindsight_evaluation as evaluation
from ade_api.features.agent_runtime.hindsight_eval_capture import EvaluationCapture
from ade_api.features.agent_runtime.hindsight_eval_contracts import (
    CONTRACT,
    EvaluationInput,
)
from ade_api.features.agent_runtime.hindsight_eval_recall import HindsightRecall
from ade_api.features.agent_runtime.router_transport import RouterTransport


def memory(**changes):
    return {
        "id": "fact-1",
        "text": "小棠说她曾独自去看海。",
        "type": "experience",
        "tags": ["character:C"],
        "document_id": "committed-exchange-1",
        "mentioned_at": "2026-10-01T00:00:00Z",
        "entities": ["小棠"],
        "context": "speaker=assistant; solo story, not a shared user event",
        "metadata": {"speaker": "assistant", "source_id": "exchange-1"},
        **changes,
    }


def inputs(**changes):
    return EvaluationInput.model_validate(
        {
            "contract": CONTRACT,
            "synthetic": True,
            "case_id": "story-detail",
            "scope": {
                "workspace_id": "campaign-1",
                "subject_id": "S",
                "character_root_id": "C",
            },
            "model_key": "deepseek::deepseek-flash",
            "persona": "你是林小棠。",
            "dialogue": [
                {"role": "user", "content": "你之前说看海那次是和谁一起去的？"}
            ],
            "query": "看海",
            "query_timestamp": "2026-10-11T12:00:00Z",
            "arms": ["hindsight", "empty", "adequate"],
            "adequate_memories": [memory()],
            **changes,
        }
    )


def profile():
    result = {key: None for key in evaluation.PROFILE_FIELDS}
    result.update(
        {
            "router_model_id": "deepseek::deepseek-flash",
            "provider_model_id": "deepseek-flash",
            "source_id": "deepseek",
            "source_adapter": "deepseek_openai",
            "model_type": "llm",
            "profile_applied": True,
            "sampling_defaults": {},
            "scenario_sampling_defaults": {},
            "thinking_default_enabled": True,
            "reasoning_effort_default": "high",
            "route_aliases": ["deepseek::deepseek-flash"],
        }
    )
    return result


class FakeProviders:
    def __init__(
        self,
        *,
        recalled=None,
        recall_status=200,
        malformed=False,
        tool_call=False,
        finish="stop",
        drift_at=None,
    ):
        self.recalled = [memory()] if recalled is None else recalled
        self.recall_status = recall_status
        self.malformed = malformed
        self.tool_call = tool_call
        self.finish = finish
        self.drift_at = drift_at
        self.catalog_calls = 0
        self.recalls = []
        self.generations = []

    def handle(self, request):
        if request.url.path.endswith("/router/model-catalog"):
            self.catalog_calls += 1
            item = profile()
            if self.drift_at and self.catalog_calls >= self.drift_at:
                item["reasoning_effort_default"] = "low"
            return httpx.Response(200, json={"items": [item]})
        payload = json.loads(request.content)
        if request.url.path.endswith("/memories/recall"):
            assert request.headers["Authorization"] == "Bearer hindsight-secret"
            self.recalls.append((str(request.url), payload))
            body = (
                {"error": "invalid"}
                if self.malformed
                else {
                    "results": self.recalled,
                    "trace": {
                        "reranked": [
                            {
                                "node_id": "fact-1",
                                "text": "TRACE-ONLY-CANDIDATE",
                                "score_components": {
                                    "cross_encoder_score": 0.7,
                                    "cross_encoder_score_normalized": 0.8,
                                },
                            }
                        ],
                        "summary": {
                            "phase_metrics": [
                                {
                                    "phase_name": "reranking",
                                    "duration_seconds": 0.1,
                                    "details": {
                                        "candidates_reranked": 1,
                                        "reranker_type": "cross-encoder",
                                    },
                                }
                            ]
                        },
                    },
                }
            )
            return httpx.Response(self.recall_status, json=body)
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer router-secret"
        self.generations.append(payload)
        message = {
            "role": "assistant",
            "content": "那次是我自己去的。",
            "reasoning_content": "PRIVATE-REASONING-MUST-NOT-BE-CAPTURED",
        }
        if self.tool_call:
            message["tool_calls"] = [
                {"id": "tool-1", "function": {"name": "search_memory"}}
            ]
        return httpx.Response(
            200,
            json={
                "id": "reply-1",
                "choices": [{"message": message, "finish_reason": self.finish}],
                "usage": {
                    "prompt_tokens": 123,
                    "completion_tokens": 10,
                    "total_tokens": 133,
                },
            },
        )


def run(monkeypatch, tmp_path, fake, request=None, capture=None):
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(fake.handle), **kwargs
        ),
    )

    async def execute():
        async with httpx.AsyncClient() as client:
            return await evaluation.evaluate(
                request or inputs(),
                router=RouterTransport("http://router/v1", "router-secret"),
                recall=HindsightRecall(
                    client, base_url="http://hindsight", api_key="hindsight-secret"
                ),
                capture=capture or EvaluationCapture(tmp_path / "receipts"),
            )

    return asyncio.run(execute())


def read(tmp_path, name):
    return json.loads((tmp_path / "receipts" / name).read_text())
