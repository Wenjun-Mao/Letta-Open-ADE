from __future__ import annotations

import time
from typing import Any

import httpx


class LettaBaselineProbe:
    """Black-boxes pinned Letta only through the supported ADE API."""

    def __init__(
        self,
        *,
        ade_api_base_url: str,
        ade_api_key: str,
        timeout_seconds: float,
    ) -> None:
        headers = {"Authorization": f"Bearer {ade_api_key}"} if ade_api_key else {}
        self.client = httpx.Client(
            base_url=ade_api_base_url,
            headers=headers,
            timeout=max(timeout_seconds + 30, 60),
        )
        self.timeout_seconds = timeout_seconds

    def close(self) -> None:
        self.client.close()

    def run(self, *, model_key: str) -> dict[str, Any]:
        model_handle = (
            model_key
            if model_key.startswith("openai-proxy/")
            else f"openai-proxy/{model_key}"
        )
        timeline: list[dict[str, Any]] = []
        agent_id = ""
        archived = False
        purged = False
        try:
            options = self._request(
                "GET",
                "/api/v2/model-catalog/options",
                params={"scenario": "chat", "refresh": "true"},
            )
            timeline.append({"operation": "options", **options})
            created = self._request(
                "POST",
                "/api/v2/agent-studio/agents",
                json={
                    "scenario": "chat",
                    "name": f"agent-runtime-study-{int(time.time())}",
                    "model": model_handle,
                    "prompt_key": "chat_v20260516",
                    "persona_key": "chat_linxiaotang",
                    "embedding": "letta/letta-free",
                },
            )
            timeline.append({"operation": "create", **created})
            agent_id = str((created.get("payload") or {}).get("id") or "")
            if not agent_id:
                return self._summary(timeline, agent_id, archived, purged)

            initial = self._request(
                "GET",
                f"/api/v2/agent-studio/agents/{agent_id}/persistent-state",
                params={"limit": "500"},
            )
            timeline.append({"operation": "initial_state", **initial})
            for index, message in enumerate(
                (
                    "你好，我叫张伟。",
                    "我有一只叫Rocky的狗。",
                    "Rocky是一只哈士奇。",
                    (
                        "请必须调用 conversation_search 工具搜索我们之前的对话，"
                        "然后告诉我第一句话是什么。"
                    ),
                ),
                1,
            ):
                sent = self._request(
                    "POST",
                    f"/api/v2/agent-studio/agents/{agent_id}/messages",
                    json={
                        "message": message,
                        "timeout_seconds": self.timeout_seconds,
                        "retry_count": 0,
                    },
                )
                timeline.append({"operation": f"message_{index}", **sent})
                state = self._request(
                    "GET",
                    f"/api/v2/agent-studio/agents/{agent_id}/persistent-state",
                    params={"limit": "500"},
                )
                timeline.append({"operation": f"state_after_{index}", **state})
                raw_prompt = self._request(
                    "GET",
                    f"/api/v2/agent-studio/agents/{agent_id}/raw-prompt",
                )
                timeline.append(
                    {"operation": f"raw_prompt_after_{index}", **raw_prompt}
                )

            edited = self._request(
                "PATCH",
                f"/api/v2/agent-studio/agents/{agent_id}/memory/human",
                json={"value": "Study manual memory edit marker."},
            )
            timeline.append({"operation": "manual_memory_edit", **edited})
            invalid_model = self._request(
                "POST",
                f"/api/v2/agent-studio/agents/{agent_id}/runtime-messages",
                json={
                    "input": "This request should fail without ADE retries.",
                    "override_model": "openai-proxy/__missing_study_model__",
                    "timeout_seconds": 5,
                    "retry_count": 0,
                },
            )
            timeline.append({"operation": "failure_handling", **invalid_model})
            archive = self._request(
                "POST", f"/api/v2/agent-studio/agents/{agent_id}/archive"
            )
            archived = archive["status_code"] < 400
            timeline.append({"operation": "archive", **archive})
            blocked = self._request(
                "POST",
                f"/api/v2/agent-studio/agents/{agent_id}/messages",
                json={"message": "blocked", "retry_count": 0},
            )
            timeline.append({"operation": "archived_agent_block", **blocked})
        finally:
            if agent_id:
                if not archived:
                    archive = self._request(
                        "POST", f"/api/v2/agent-studio/agents/{agent_id}/archive"
                    )
                    archived = archive["status_code"] < 400
                    timeline.append({"operation": "cleanup_archive", **archive})
                if archived:
                    purge = self._request(
                        "DELETE", f"/api/v2/agent-studio/agents/{agent_id}/purge"
                    )
                    purged = purge["status_code"] < 400
                    timeline.append({"operation": "purge", **purge})
        return self._summary(timeline, agent_id, archived, purged)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        started = time.monotonic()
        try:
            response = self.client.request(method, path, **kwargs)
            try:
                payload: object = response.json()
            except ValueError:
                payload = response.text
            return {
                "status_code": response.status_code,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "payload": payload,
            }
        except Exception as exc:
            return {
                "status_code": 0,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

    @staticmethod
    def _summary(
        timeline: list[dict[str, Any]],
        agent_id: str,
        archived: bool,
        purged: bool,
    ) -> dict[str, Any]:
        return {
            "agent_id": agent_id,
            "archived": archived,
            "purged": purged,
            "timeline": timeline,
            "observations": _analyze_timeline(timeline),
            "operation_count": len(timeline),
            "failed_operations": [
                item["operation"]
                for item in timeline
                if int(item.get("status_code", 0)) >= 400
                or int(item.get("status_code", 0)) == 0
            ],
        }


def _analyze_timeline(timeline: list[dict[str, Any]]) -> dict[str, Any]:
    tool_calls: list[dict[str, str]] = []
    assistant_outputs: list[str] = []
    memory_snapshots: list[dict[str, Any]] = []
    context_snapshots: list[dict[str, Any]] = []
    for item in timeline:
        operation = str(item.get("operation", ""))
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        if operation.startswith("message_"):
            for event in payload.get("sequence") or ():
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "tool_call":
                    tool_calls.append(
                        {
                            "operation": operation,
                            "name": str(event.get("name", "")),
                            "arguments": str(event.get("arguments", "")),
                        }
                    )
                if event.get("type") == "assistant":
                    assistant_outputs.append(str(event.get("content", "")))
        if operation.startswith("state_after_"):
            human = next(
                (
                    block.get("value", "")
                    for block in payload.get("memory_blocks") or ()
                    if isinstance(block, dict) and block.get("label") == "human"
                ),
                "",
            )
            history = payload.get("conversation_history") or {}
            memory_snapshots.append({"operation": operation, "human": human})
            context_snapshots.append(
                {
                    "operation": operation,
                    "total_persisted": int(history.get("total_persisted", 0)),
                    "displayed": int(history.get("displayed", 0)),
                    "counts_by_type": history.get("counts_by_type") or {},
                }
            )
        if operation.startswith("raw_prompt_after_"):
            messages = payload.get("messages") or ()
            context_snapshots.append(
                {
                    "operation": operation,
                    "message_count": len(messages),
                    "character_count": sum(
                        len(str(message.get("content", "")))
                        for message in messages
                        if isinstance(message, dict)
                    ),
                }
            )
    tool_names = [call["name"] for call in tool_calls]
    return {
        "tool_calls": tool_calls,
        "tool_names": tool_names,
        "conversation_search_observed": "conversation_search" in tool_names,
        "memory_write_observed": any(
            name in {"memory_insert", "memory_replace"} for name in tool_names
        ),
        "assistant_outputs": assistant_outputs,
        "human_memory_snapshots": memory_snapshots,
        "context_snapshots": context_snapshots,
    }
