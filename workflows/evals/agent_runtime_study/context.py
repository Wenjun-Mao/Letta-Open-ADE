from __future__ import annotations

from .contracts import (
    BuiltContext,
    ContextBudget,
    ContextSection,
    MemoryFact,
    Message,
)
from .memory import MemoryRetriever
from .repository import InMemoryStudyRepository


MEMORY_CONTROL_INSTRUCTIONS = """Memory rules:
- Store only durable facts explicitly stated by the user.
- When the user adds, corrects, combines, or asks to forget a durable fact, you
  MUST call propose_memory_change before replying in the same turn.
- The runtime binds every memory operation to the current subject. Never request,
  infer, or invent another subject identifier.
- For add, provide value and an exact evidence_quote from the current user message.
- For correct and forget, copy the fact id and version from the active profile into
  fact_id and expected_version. A correction may preserve prior fact details while
  adding only the newly stated refinement.
- For merge, provide every target fact id and expected version.
- Do not store guesses, implications, temporary plans, or facts about third parties.
- Use search_memory for older details that are not visible in the active profile.
- If a tool returns an error, correct the arguments rather than silently skipping a
  required durable-memory update.
"""


def estimate_tokens(value: str) -> int:
    text = str(value or "")
    if not text:
        return 0
    return max(1, (len(text.encode("utf-8")) + 3) // 4)


def truncate_to_tokens(value: str, token_limit: int, *, keep_end: bool = False) -> str:
    text = str(value or "")
    if token_limit <= 0:
        return ""
    if estimate_tokens(text) <= token_limit:
        return text
    low, high = 0, len(text)
    while low < high:
        midpoint = (low + high + 1) // 2
        candidate = text[-midpoint:] if keep_end else text[:midpoint]
        if estimate_tokens(candidate) <= token_limit:
            low = midpoint
        else:
            high = midpoint - 1
    selected = text[-low:] if keep_end else text[:low]
    marker = "[...truncated...]"
    if keep_end:
        return f"{marker}\n{selected}" if selected else marker
    return f"{selected}\n{marker}" if selected else marker


def _fact_line(fact: MemoryFact) -> str:
    return f"- [{fact.id} v{fact.version}] {fact.key}: {fact.value}"


def _fit_lines(
    lines: list[tuple[str, str]], token_limit: int
) -> tuple[str, tuple[str, ...]]:
    selected: list[str] = []
    item_ids: list[str] = []
    used = 0
    for item_id, line in lines:
        cost = estimate_tokens(line)
        if selected and used + cost > token_limit:
            continue
        if not selected and cost > token_limit:
            selected.append(truncate_to_tokens(line, token_limit))
            item_ids.append(item_id)
            break
        selected.append(line)
        item_ids.append(item_id)
        used += cost
    return "\n".join(selected), tuple(item_ids)


class ContextBuilder:
    def __init__(
        self,
        repository: InMemoryStudyRepository,
        retriever: MemoryRetriever,
    ) -> None:
        self.repository = repository
        self.retriever = retriever

    def build(
        self,
        *,
        conversation_id: str,
        current_user_message: Message,
        budget: ContextBudget,
        search_limit: int,
        include_episodes: bool,
    ) -> BuiltContext:
        conversation = self.repository.get_conversation(conversation_id)
        agent = self.repository.get_agent_definition(conversation.agent_definition_id)
        subject = self.repository.get_subject(conversation.memory_subject_id)
        max_input_tokens = budget.total_tokens - budget.response_reserve_tokens
        if max_input_tokens <= 0:
            raise ValueError("context budget leaves no room for input")

        sections: list[ContextSection] = []
        agent_text = (
            f"Agent definition: {agent.name} (version {agent.version})\n\n"
            f"System prompt:\n{agent.system_prompt}\n\n"
            f"Persona:\n{agent.persona}\n\n{MEMORY_CONTROL_INSTRUCTIONS}"
        )
        sections.append(
            self._section(
                "agent_prompt_and_persona",
                truncate_to_tokens(agent_text, budget.agent_tokens),
                (agent.id,),
            )
        )

        active_facts = sorted(
            self.repository.list_subject_facts(subject.id, active_only=True),
            key=lambda item: (item.updated_at, item.id),
            reverse=True,
        )
        profile_lines = [(fact.id, _fact_line(fact)) for fact in active_facts]
        profile_text, profile_ids = _fit_lines(profile_lines, budget.profile_tokens)
        profile_header = (
            f"Active memory subject: {subject.display_name or subject.external_key} "
            f"(id={subject.id})\n"
        )
        profile_content = f"{profile_header}{profile_text or '- No committed facts.'}"
        sections.append(
            self._section("active_subject_profile", profile_content, profile_ids)
        )

        summary = self.repository.get_summary(conversation_id)
        if summary:
            summary_text = (
                f"Conversation summary v{summary.version}, through message "
                f"{summary.through_sequence}:\n{summary.content}"
            )
            summary_ids = (summary.id,)
        else:
            summary_text = "No conversation summary has been created."
            summary_ids = ()
        sections.append(
            self._section(
                "conversation_summary",
                truncate_to_tokens(summary_text, budget.summary_tokens),
                summary_ids,
            )
        )

        retrieved_facts = tuple(
            fact
            for fact in self.retriever.search_facts(
                subject.id,
                current_user_message.content,
                limit=search_limit + len(profile_ids),
            )
            if fact.id not in profile_ids
        )[:search_limit]
        retrieved_episodes = (
            self.retriever.search_episodes(
                subject.id, current_user_message.content, limit=search_limit
            )
            if include_episodes
            else ()
        )
        retrieval_lines = [
            (fact.id, f"- fact {_fact_line(fact)[2:]}") for fact in retrieved_facts
        ] + [
            (episode.id, f"- episode [{episode.id}] {episode.content}")
            for episode in retrieved_episodes
        ]
        retrieval_text, retrieval_ids = _fit_lines(
            retrieval_lines, budget.retrieved_tokens
        )
        sections.append(
            self._section(
                "automatically_retrieved_memory",
                retrieval_text or "No additional relevant memory was retrieved.",
                retrieval_ids,
            )
        )

        prior_messages = [
            message
            for message in self.repository.list_messages(conversation_id)
            if message.id != current_user_message.id
            and (not summary or message.sequence > summary.through_sequence)
        ]
        recent_text, recent_ids = self._recent_messages(
            prior_messages, budget.recent_message_tokens
        )
        sections.append(
            self._section(
                "recent_raw_messages",
                recent_text or "No recent raw messages.",
                recent_ids,
            )
        )

        system_prompt = "\n\n".join(
            f"## {section.name}\n{section.content}" for section in sections
        )
        user_prompt = current_user_message.content
        user_tokens = estimate_tokens(user_prompt)
        if user_tokens >= max_input_tokens:
            raise ValueError("current user message exceeds the model input budget")
        total = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
        if total > max_input_tokens:
            overflow = total - max_input_tokens
            last = sections[-1]
            replacement_limit = max(0, last.estimated_tokens - overflow)
            sections[-1] = self._section(
                last.name,
                truncate_to_tokens(last.content, replacement_limit, keep_end=True),
                last.item_ids,
            )
            system_prompt = "\n\n".join(
                f"## {section.name}\n{section.content}" for section in sections
            )
            total = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
        if total > max_input_tokens:
            raise ValueError("context builder could not satisfy the input budget")

        all_prior_ids = {message.id for message in prior_messages}
        omitted_ids = tuple(sorted(all_prior_ids - set(recent_ids)))
        return BuiltContext(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            sections=tuple(sections),
            estimated_input_tokens=total,
            omitted_message_ids=omitted_ids,
            retrieved_fact_ids=tuple(fact.id for fact in retrieved_facts),
            retrieved_episode_ids=tuple(episode.id for episode in retrieved_episodes),
        )

    @staticmethod
    def _section(name: str, content: str, item_ids: tuple[str, ...]) -> ContextSection:
        return ContextSection(
            name=name,
            content=content,
            estimated_tokens=estimate_tokens(content),
            item_ids=item_ids,
        )

    @staticmethod
    def _recent_messages(
        messages: list[Message], token_limit: int
    ) -> tuple[str, tuple[str, ...]]:
        selected: list[Message] = []
        used = 0
        for message in reversed(messages):
            line = f"[{message.sequence}] {message.role.value}: {message.content}"
            cost = estimate_tokens(line)
            if selected and used + cost > token_limit:
                break
            if not selected and cost > token_limit:
                selected.append(message)
                break
            selected.append(message)
            used += cost
        selected.reverse()
        lines = [
            f"[{message.sequence}] {message.role.value}: {message.content}"
            for message in selected
        ]
        content = "\n".join(lines)
        if estimate_tokens(content) > token_limit:
            content = truncate_to_tokens(content, token_limit, keep_end=True)
        return content, tuple(message.id for message in selected)
