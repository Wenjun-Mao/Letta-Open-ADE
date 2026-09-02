from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MEMORY_CONTROL_INSTRUCTIONS = """Memory rules:
- A separate ADE reviewer evaluates durable facts after your response. Never claim
  that you stored, corrected, or forgot memory.
- Use only committed facts shown in context. Never select or invent a subject ID.
- Use search_memory only when older relevant details are absent from the profile.
- Return user-visible dialogue only; never expose private reasoning.
"""


def estimate_tokens(value: str) -> int:
    encoded = str(value or "").encode("utf-8")
    return 0 if not encoded else max(1, (len(encoded) + 3) // 4)


def truncate_to_tokens(value: str, limit: int, *, keep_end: bool = False) -> str:
    text = str(value or "")
    if limit <= 0:
        return ""
    if estimate_tokens(text) <= limit:
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        candidate = text[-middle:] if keep_end else text[:middle]
        if estimate_tokens(candidate) <= limit:
            low = middle
        else:
            high = middle - 1
    selected = text[-low:] if keep_end else text[:low]
    return (
        f"[...truncated...]\n{selected}"
        if keep_end
        else f"{selected}\n[...truncated...]"
    )


@dataclass(frozen=True)
class ContextBudget:
    context_window: int
    max_output_tokens: int
    tool_schema_tokens: int
    prompt_tokens: int = 2_400
    profile_tokens: int = 1_500
    summary_tokens: int = 1_500
    retrieval_tokens: int = 1_500
    recent_tokens: int = 3_000

    @property
    def input_limit(self) -> int:
        safety = max(256, int(self.context_window * 0.05))
        return (
            self.context_window
            - self.max_output_tokens
            - self.tool_schema_tokens
            - safety
        )


def context_budget_from_deployment(deployment: dict[str, Any]) -> ContextBudget:
    context = dict(deployment.get("fingerprint_payload", {})).get(
        "context_settings", {}
    )
    if not isinstance(context, dict):
        context = {}
    context_window = int(
        context.get("total_tokens") or context.get("context_tokens") or 16_384
    )
    max_output = int(
        context.get("max_output_tokens")
        or context.get("response_reserve_tokens")
        or 4_096
    )
    return ContextBudget(
        context_window=max(2_048, context_window),
        max_output_tokens=max(256, min(max_output, context_window // 2)),
        tool_schema_tokens=256,
    )


def validate_current_user_message(
    *,
    system_prompt: str,
    persona: str,
    content: str,
    budget: ContextBudget,
) -> None:
    prompt = truncate_to_tokens(
        f"{system_prompt}\n\nPersona:\n{persona}\n\n{MEMORY_CONTROL_INSTRUCTIONS}",
        budget.prompt_tokens,
    )
    if estimate_tokens(prompt) + estimate_tokens(content) > budget.input_limit:
        raise ValueError("Current message plus mandatory prompt exceeds context window")


@dataclass(frozen=True)
class BuiltContext:
    messages: list[dict[str, str]]
    section_tokens: dict[str, int]
    omitted_message_ids: list[str]
    retrieved_fact_ids: list[str]
    estimated_input_tokens: int


@dataclass(frozen=True)
class ConversationHistoryMetadata:
    completed_user_turns: int
    summary_through_sequence: int


def conversation_history_metadata(
    *,
    messages: list[dict[str, Any]],
    current_sequence: int,
    summary_through_sequence: int,
) -> ConversationHistoryMetadata:
    completed_run_ids = {
        str(message["run_id"])
        for message in messages
        if str(message.get("role")) == "assistant"
        and message.get("run_id") is not None
        and int(message["sequence"]) < current_sequence
    }
    return ConversationHistoryMetadata(
        completed_user_turns=sum(
            1
            for message in messages
            if str(message.get("role")) == "user"
            and int(message["sequence"]) < current_sequence
            and message.get("run_id") is not None
            and str(message["run_id"]) in completed_run_ids
        ),
        summary_through_sequence=max(0, int(summary_through_sequence)),
    )


def build_context(
    *,
    system_prompt: str,
    persona: str,
    active_facts: list[dict[str, Any]],
    retrieved_facts: list[dict[str, Any]],
    recent_messages: list[dict[str, Any]],
    current_user_content: str,
    budget: ContextBudget,
    conversation_summary: str = "",
    history_metadata: ConversationHistoryMetadata | None = None,
) -> BuiltContext:
    if budget.input_limit <= 0:
        raise ValueError("Context budget leaves no model input capacity")
    prompt = truncate_to_tokens(
        f"{system_prompt}\n\nPersona:\n{persona}\n\n{MEMORY_CONTROL_INSTRUCTIONS}",
        budget.prompt_tokens,
    )
    profile_lines = [
        f"- [{fact['id']} v{fact['version']}] {fact['key']}: {fact['value']}"
        for fact in active_facts
    ]
    profile = truncate_to_tokens(
        "Active subject facts:\n" + ("\n".join(profile_lines) or "- None"),
        budget.profile_tokens,
    )
    metadata = history_metadata or ConversationHistoryMetadata(
        completed_user_turns=0,
        summary_through_sequence=0,
    )
    history = (
        "Conversation history metadata (authoritative):\n"
        "- Exact completed conversation rounds before current: "
        f"{metadata.completed_user_turns}\n"
        "- This excludes the current request and any run without a committed "
        "assistant reply.\n"
        "- Use this exact integer for count questions; do not estimate or include "
        "the current request.\n"
        "- Summary covers messages through sequence: "
        f"{metadata.summary_through_sequence}\n"
        "- For exact counts or boundaries, the metadata above overrides the "
        "narrative summary."
    )
    summary = truncate_to_tokens(
        "Conversation summary (lossy narrative derivative):\n"
        + (conversation_summary.strip() or "No summary has been committed."),
        budget.summary_tokens,
    )
    active_ids = {str(fact["id"]) for fact in active_facts}
    retrieved = [fact for fact in retrieved_facts if str(fact["id"]) not in active_ids]
    retrieval = truncate_to_tokens(
        "Retrieved memory:\n"
        + (
            "\n".join(
                f"- [{fact['id']} v{fact['version']}] {fact['key']}: {fact['value']}"
                for fact in retrieved
            )
            or "- None"
        ),
        budget.retrieval_tokens,
    )
    selected: list[dict[str, Any]] = []
    used = 0
    for message in reversed(recent_messages):
        line = f"{message['role']}: {message['content']}"
        cost = estimate_tokens(line)
        if selected and used + cost > budget.recent_tokens:
            break
        selected.append(message)
        used += cost
    selected.reverse()
    mandatory = estimate_tokens(prompt) + estimate_tokens(current_user_content)
    if mandatory > budget.input_limit:
        raise ValueError("Current message plus mandatory prompt exceeds context window")
    messages = [
        {
            "role": "system",
            "content": (
                f"{prompt}\n\n{profile}\n\n{history}\n\n{summary}\n\n{retrieval}"
            ),
        },
        *[
            {"role": str(message["role"]), "content": str(message["content"])}
            for message in selected
        ],
        {"role": "user", "content": current_user_content},
    ]
    while estimate_tokens(str(messages)) > budget.input_limit and len(messages) > 2:
        messages.pop(1)
        selected.pop(0)
    total = estimate_tokens(str(messages))
    if total > budget.input_limit:
        raise ValueError("Context builder could not satisfy model input budget")
    selected_ids = {str(message["id"]) for message in selected}
    return BuiltContext(
        messages=messages,
        section_tokens={
            "prompt_persona": estimate_tokens(prompt),
            "active_profile": estimate_tokens(profile),
            "conversation_history_metadata": estimate_tokens(history),
            "conversation_summary": estimate_tokens(summary),
            "retrieved_memory": estimate_tokens(retrieval),
            "recent_messages": sum(
                estimate_tokens(str(message["content"])) for message in selected
            ),
            "current_user_message": estimate_tokens(current_user_content),
        },
        omitted_message_ids=[
            str(message["id"])
            for message in recent_messages
            if str(message["id"]) not in selected_ids
        ],
        retrieved_fact_ids=[str(fact["id"]) for fact in retrieved],
        estimated_input_tokens=total,
    )
