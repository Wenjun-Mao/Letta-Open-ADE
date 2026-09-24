from __future__ import annotations

import re


_DETAIL_CODE_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,127}")


class AgentRuntimeError(RuntimeError):
    code = "agent_runtime_error"
    status_code = 500


class RuntimeFeatureDisabled(AgentRuntimeError):
    code = "agent_runtime_disabled"
    status_code = 503


class RuntimeNotReady(AgentRuntimeError):
    code = "agent_runtime_not_ready"
    status_code = 503


class RuntimeNotFound(AgentRuntimeError):
    code = "not_found"
    status_code = 404


class RuntimeConflict(AgentRuntimeError):
    code = "conflict"
    status_code = 409


class IdempotencyConflict(RuntimeConflict):
    code = "idempotency_conflict"


class ConversationBusy(RuntimeConflict):
    code = "conversation_busy"


class MemoryGenerationConflict(RuntimeConflict):
    code = "memory_generation_conflict"


class MemoryTargetConflict(RuntimeConflict):
    code = "memory_target_conflict"


class MemoryActionIdempotencyConflict(IdempotencyConflict):
    code = "memory_action_idempotency_conflict"


class UnqualifiedDeployment(AgentRuntimeError):
    code = "unqualified_deployment"
    status_code = 422


class RuntimeValidationError(AgentRuntimeError):
    code = "validation_error"
    status_code = 422

    def __init__(self, message: str, *, detail_code: str | None = None) -> None:
        super().__init__(message)
        if detail_code is not None and not _DETAIL_CODE_PATTERN.fullmatch(detail_code):
            raise ValueError("detail_code must be a bounded snake-case identifier")
        self.detail_code = detail_code
