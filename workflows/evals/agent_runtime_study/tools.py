from __future__ import annotations

from typing import Any

from .contracts import (
    MemoryOperation,
    MemoryProposal,
    Message,
    ToolDefinition,
    ToolExecution,
)
from .memory import MemoryPolicy, MemoryProposalError, MemoryRetriever


MEMORY_PROPOSAL_TOOL = ToolDefinition(
    name="propose_memory_change",
    description=(
        "Propose an evidence-backed durable-memory add, correction, merge, or "
        "forget operation for the current subject. Subject identity is bound by "
        "the runtime and is intentionally not an argument."
    ),
    parameters_json_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "correct", "merge", "forget"],
            },
            "key": {"type": "string", "minLength": 1},
            "value": {"type": ["string", "null"]},
            "evidence_quote": {"type": "string", "minLength": 1},
            "fact_id": {"type": ["string", "null"]},
            "target_fact_ids": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
            "expected_version": {"type": ["integer", "null"], "minimum": 1},
            "expected_versions": {
                "type": "object",
                "additionalProperties": {"type": "integer", "minimum": 1},
                "default": {},
            },
        },
        "required": ["operation", "key", "evidence_quote"],
    },
)

MEMORY_SEARCH_TOOL = ToolDefinition(
    name="search_memory",
    description=(
        "Search older committed memory for the current subject. The subject is "
        "bound by the runtime and cannot be selected by model arguments."
    ),
    parameters_json_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "required": ["query"],
    },
)

WEATHER_TOOL = ToolDefinition(
    name="get_weather",
    description="Return deterministic study weather for a named city.",
    parameters_json_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {"city": {"type": "string", "minLength": 1}},
        "required": ["city"],
    },
)

CURATED_TOOL_DEFINITIONS = (
    MEMORY_PROPOSAL_TOOL,
    MEMORY_SEARCH_TOOL,
    WEATHER_TOOL,
)

_WEATHER_FIXTURES = {
    "toronto": {"condition": "clear", "temperature_c": 21},
    "beijing": {"condition": "partly cloudy", "temperature_c": 26},
    "北京": {"condition": "partly cloudy", "temperature_c": 26},
    "多伦多": {"condition": "clear", "temperature_c": 21},
}


class TurnToolSession:
    """Subject-bound, attempt-local tool state; writes commit only on run success."""

    def __init__(
        self,
        *,
        subject_id: str,
        conversation_id: str,
        source_messages: tuple[Message, ...],
        memory_policy: MemoryPolicy,
        memory_retriever: MemoryRetriever,
        search_limit: int,
        include_episodes: bool,
    ) -> None:
        self.subject_id = subject_id
        self.conversation_id = conversation_id
        self.source_messages = source_messages
        self.memory_policy = memory_policy
        self.memory_retriever = memory_retriever
        self.search_limit = search_limit
        self.include_episodes = include_episodes
        self.pending_proposals: list[MemoryProposal] = []
        self.executions: list[ToolExecution] = []

    async def execute(
        self, name: str, arguments: dict[str, Any], call_id: str
    ) -> dict[str, Any]:
        try:
            if "subject_id" in arguments or "memory_subject_id" in arguments:
                raise MemoryProposalError(
                    "subject selection is forbidden in model-controlled arguments"
                )
            if name == MEMORY_PROPOSAL_TOOL.name:
                result = self._propose(arguments)
            elif name == MEMORY_SEARCH_TOOL.name:
                result = self._search(arguments)
            elif name == WEATHER_TOOL.name:
                result = self._weather(arguments)
            else:
                raise ValueError(f"Unknown curated tool: {name}")
            succeeded = bool(result.get("ok", True))
        except Exception as exc:
            result = {
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            succeeded = False
        self.executions.append(
            ToolExecution(
                call_id=call_id,
                name=name,
                arguments=dict(arguments),
                result=result,
                succeeded=succeeded,
            )
        )
        return result

    def _propose(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation = MemoryOperation(str(arguments.get("operation") or ""))
        expected_versions_raw = arguments.get("expected_versions") or {}
        if not isinstance(expected_versions_raw, dict):
            raise MemoryProposalError("expected_versions must be an object")
        proposal = MemoryProposal(
            operation=operation,
            key=str(arguments.get("key") or "").strip(),
            value=(
                str(arguments["value"]).strip()
                if arguments.get("value") is not None
                else None
            ),
            evidence_quote=str(arguments.get("evidence_quote") or "").strip(),
            fact_id=str(arguments.get("fact_id") or "").strip() or None,
            target_fact_ids=tuple(
                str(item).strip()
                for item in (arguments.get("target_fact_ids") or [])
                if str(item).strip()
            ),
            expected_version=(
                int(arguments["expected_version"])
                if arguments.get("expected_version") is not None
                else None
            ),
            expected_versions={
                str(key): int(value) for key, value in expected_versions_raw.items()
            },
        )
        self.memory_policy.validate_batch(
            subject_id=self.subject_id,
            proposals=(*self.pending_proposals, proposal),
            source_messages=self.source_messages,
        )
        self.pending_proposals.append(proposal)
        return {
            "ok": True,
            "status": "staged",
            "proposal_index": len(self.pending_proposals) - 1,
            "operation": proposal.operation.value,
            "key": proposal.key,
        }

    def _search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        requested_limit = int(arguments.get("limit") or self.search_limit)
        limit = max(1, min(self.search_limit, requested_limit))
        facts = self.memory_retriever.search_facts(self.subject_id, query, limit=limit)
        episodes = (
            self.memory_retriever.search_episodes(self.subject_id, query, limit=limit)
            if self.include_episodes
            else ()
        )
        return {
            "ok": True,
            "facts": [
                {
                    "id": fact.id,
                    "key": fact.key,
                    "value": fact.value,
                    "version": fact.version,
                }
                for fact in facts
            ],
            "episodes": [
                {"id": episode.id, "content": episode.content} for episode in episodes
            ],
        }

    @staticmethod
    def _weather(arguments: dict[str, Any]) -> dict[str, Any]:
        city = str(arguments.get("city") or "").strip()
        if not city:
            raise ValueError("city is required")
        if city.casefold() in {"fail_city", "failure", "故障城市"}:
            raise RuntimeError("deterministic weather provider failure")
        weather = _WEATHER_FIXTURES.get(city.casefold()) or {
            "condition": "unknown",
            "temperature_c": None,
        }
        return {"ok": True, "city": city, **weather}

    def commit(self, *, run_id: str):
        return self.memory_policy.apply_batch(
            subject_id=self.subject_id,
            proposals=tuple(self.pending_proposals),
            source_messages=self.source_messages,
            run_id=run_id,
        )


def curated_tools(names: tuple[str, ...]) -> tuple[ToolDefinition, ...]:
    allowed = {definition.name: definition for definition in CURATED_TOOL_DEFINITIONS}
    unknown = sorted(set(names) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown curated tool definitions: {unknown}")
    return tuple(allowed[name] for name in names)
