from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol


def utc_now() -> datetime:
    return datetime.now(UTC)


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MemoryOperation(StrEnum):
    ADD = "add"
    CORRECT = "correct"
    MERGE = "merge"
    FORGET = "forget"


class MemoryFactStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    FORGOTTEN = "forgotten"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunEventType(StrEnum):
    RUN_STARTED = "run.started"
    CONTEXT_BUILT = "context.built"
    MODEL_REQUEST = "model.request"
    MODEL_RESPONSE = "model.response"
    PROTOCOL_REPAIR = "protocol.repair"
    TOOL_CALL = "tool.call"
    TOOL_RESULT = "tool.result"
    MEMORY_PROPOSED = "memory.proposed"
    MEMORY_COMMITTED = "memory.committed"
    MESSAGE_COMMITTED = "message.committed"
    RETRY_SCHEDULED = "retry.scheduled"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"


class RunEventVisibility(StrEnum):
    OPERATOR = "operator"
    PRIVATE = "private"


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    model_key: str
    system_prompt: str
    persona: str
    tool_names: tuple[str, ...]
    version: int = 1
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class MemorySubject:
    id: str
    external_key: str
    display_name: str = ""
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Conversation:
    id: str
    agent_definition_id: str
    memory_subject_id: str
    created_at: datetime = field(default_factory=utc_now)
    archived_at: datetime | None = None


@dataclass(frozen=True)
class Message:
    id: str
    conversation_id: str
    sequence: int
    role: MessageRole
    content: str
    run_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class MemoryFact:
    id: str
    subject_id: str
    key: str
    value: str
    status: MemoryFactStatus
    version: int
    current_revision_id: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class MemoryEvidenceSpan:
    message_id: str
    start_char: int
    end_char: int
    quote: str
    message_sha256: str


@dataclass(frozen=True)
class MemoryRevision:
    id: str
    fact_id: str
    subject_id: str
    operation: MemoryOperation
    key: str
    value: str | None
    fact_version: int
    source_message_ids: tuple[str, ...]
    prior_revision_ids: tuple[str, ...]
    run_id: str
    evidence_quote: str
    evidence_spans: tuple[MemoryEvidenceSpan, ...]
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class ConversationSummary:
    id: str
    conversation_id: str
    version: int
    through_sequence: int
    content: str
    source_message_ids: tuple[str, ...]
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class MemoryEpisode:
    id: str
    subject_id: str
    conversation_id: str
    content: str
    source_message_ids: tuple[str, ...]
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Run:
    id: str
    conversation_id: str
    idempotency_key: str
    request_hash: str
    status: RunStatus
    attempt_count: int = 0
    error_type: str | None = None
    error_message: str | None = None
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None


@dataclass(frozen=True)
class RunEvent:
    id: str
    run_id: str
    sequence: int
    schema_version: int
    type: RunEventType
    attempt: int | None
    correlation_id: str
    causation_id: str | None
    visibility: RunEventVisibility
    payload: dict[str, Any]
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters_json_schema: dict[str, Any]

    def openai_payload(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_json_schema,
            },
        }


@dataclass(frozen=True)
class MemoryProposal:
    operation: MemoryOperation
    key: str
    value: str | None
    evidence_quote: str
    fact_id: str | None = None
    target_fact_ids: tuple[str, ...] = ()
    expected_version: int | None = None
    expected_versions: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextBudget:
    total_tokens: int = 8_192
    response_reserve_tokens: int = 1_024
    agent_tokens: int = 1_800
    profile_tokens: int = 1_200
    summary_tokens: int = 1_200
    retrieved_tokens: int = 1_200
    recent_message_tokens: int = 1_700


@dataclass(frozen=True)
class RuntimePolicy:
    timeout_seconds: float = 180.0
    retry_count: int = 0
    max_model_requests: int = 6
    max_output_tokens: int = 1_024
    memory_search_limit: int = 8
    include_episodes: bool = False
    context_budget: ContextBudget = field(default_factory=ContextBudget)

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 0 <= self.retry_count <= 5:
            raise ValueError("retry_count must be between 0 and 5")
        if self.max_model_requests < 1:
            raise ValueError("max_model_requests must be positive")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if self.max_output_tokens > self.context_budget.response_reserve_tokens:
            raise ValueError(
                "max_output_tokens cannot exceed the reserved response budget"
            )


@dataclass(frozen=True)
class ContextSection:
    name: str
    content: str
    estimated_tokens: int
    item_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuiltContext:
    system_prompt: str
    user_prompt: str
    sections: tuple[ContextSection, ...]
    estimated_input_tokens: int
    omitted_message_ids: tuple[str, ...]
    retrieved_fact_ids: tuple[str, ...]
    retrieved_episode_ids: tuple[str, ...]


@dataclass(frozen=True)
class ToolExecution:
    call_id: str
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    succeeded: bool


@dataclass(frozen=True)
class ExecutorRequest:
    run_id: str
    model_key: str
    context: BuiltContext
    tools: tuple[ToolDefinition, ...]
    tool_session: "ToolSession"
    timeout_seconds: float
    max_output_tokens: int
    max_model_requests: int
    cancellation: "CancellationSignal"


@dataclass(frozen=True)
class ExecutorResult:
    assistant_text: str
    reasoning: tuple[str, ...]
    events: tuple[tuple[RunEventType, dict[str, Any]], ...]
    raw_messages: tuple[dict[str, Any], ...]
    usage: dict[str, int]
    model_request_count: int


@dataclass(frozen=True)
class TurnRequest:
    conversation_id: str
    user_content: str
    idempotency_key: str
    policy: RuntimePolicy = field(default_factory=RuntimePolicy)
    cancellation: "CancellationSignal | None" = None


@dataclass(frozen=True)
class TurnResult:
    run: Run
    user_message: Message
    assistant_message: Message | None
    memory_revisions: tuple[MemoryRevision, ...]
    context: BuiltContext | None
    events: tuple[RunEvent, ...]
    tool_executions: tuple[ToolExecution, ...]
    reasoning: tuple[str, ...]
    raw_model_messages: tuple[dict[str, Any], ...]
    usage: dict[str, int]
    elapsed_seconds: float


class CancellationSignal(Protocol):
    def is_set(self) -> bool: ...


class ToolSession(Protocol):
    async def execute(
        self, name: str, arguments: dict[str, Any], call_id: str
    ) -> dict[str, Any]: ...


class AgentRuntime(Protocol):
    async def run_turn(self, request: TurnRequest) -> TurnResult: ...


class ExecutorAdapter(Protocol):
    name: str

    async def execute(self, request: ExecutorRequest) -> ExecutorResult: ...
