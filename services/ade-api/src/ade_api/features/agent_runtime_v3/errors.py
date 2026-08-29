from __future__ import annotations


class AgentRuntimeV3Error(RuntimeError):
    code = "agent_runtime_error"
    status_code = 500


class RuntimeFeatureDisabled(AgentRuntimeV3Error):
    code = "agent_runtime_v3_disabled"
    status_code = 503


class RuntimeNotReady(AgentRuntimeV3Error):
    code = "agent_runtime_v3_not_ready"
    status_code = 503


class RuntimeNotFound(AgentRuntimeV3Error):
    code = "not_found"
    status_code = 404


class RuntimeConflict(AgentRuntimeV3Error):
    code = "conflict"
    status_code = 409


class IdempotencyConflict(RuntimeConflict):
    code = "idempotency_conflict"


class ConversationBusy(RuntimeConflict):
    code = "conversation_busy"


class UnqualifiedDeployment(AgentRuntimeV3Error):
    code = "unqualified_deployment"
    status_code = 422


class RuntimeValidationError(AgentRuntimeV3Error):
    code = "validation_error"
    status_code = 422
