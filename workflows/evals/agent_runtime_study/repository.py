from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from threading import RLock
from typing import Iterator
from uuid import uuid4

from .contracts import (
    AgentDefinition,
    Conversation,
    ConversationSummary,
    MemoryEpisode,
    MemoryEntity,
    MemoryEntityKind,
    MemoryFact,
    MemorySubject,
    Message,
    MessageRole,
    Run,
    RunEvent,
    RunEventVisibility,
    RunStatus,
    TurnResult,
    utc_now,
)


class RepositoryError(RuntimeError):
    pass


class NotFoundError(RepositoryError):
    pass


class OptimisticConflictError(RepositoryError):
    pass


class IdempotencyConflictError(RepositoryError):
    pass


class InMemoryStudyRepository:
    """Deterministic state authority for the study, with rollback transactions."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.agent_definitions: dict[str, AgentDefinition] = {}
        self.subjects: dict[str, MemorySubject] = {}
        self.memory_entities: dict[str, MemoryEntity] = {}
        self.conversations: dict[str, Conversation] = {}
        self.messages: dict[str, list[Message]] = {}
        self.facts: dict[str, MemoryFact] = {}
        self.revisions: dict[str, list] = {}
        self.summaries: dict[str, list[ConversationSummary]] = {}
        self.episodes: dict[str, list[MemoryEpisode]] = {}
        self.runs: dict[str, Run] = {}
        self.events: dict[str, list[RunEvent]] = {}
        self.idempotency: dict[tuple[str, str], str] = {}
        self.results: dict[str, TurnResult] = {}

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            snapshot = self._snapshot()
            try:
                yield
            except Exception:
                self._restore(snapshot)
                raise

    def _snapshot(self) -> dict[str, object]:
        return {
            "agent_definitions": dict(self.agent_definitions),
            "subjects": dict(self.subjects),
            "memory_entities": dict(self.memory_entities),
            "conversations": dict(self.conversations),
            "messages": {key: list(value) for key, value in self.messages.items()},
            "facts": dict(self.facts),
            "revisions": {key: list(value) for key, value in self.revisions.items()},
            "summaries": {key: list(value) for key, value in self.summaries.items()},
            "episodes": {key: list(value) for key, value in self.episodes.items()},
            "runs": dict(self.runs),
            "events": {key: list(value) for key, value in self.events.items()},
            "idempotency": dict(self.idempotency),
            "results": dict(self.results),
        }

    def _restore(self, snapshot: dict[str, object]) -> None:
        for name, value in snapshot.items():
            setattr(self, name if name.startswith("_") else f"{name}", value)

    def add_agent_definition(self, value: AgentDefinition) -> None:
        with self._lock:
            if value.id in self.agent_definitions:
                raise RepositoryError(f"Agent definition already exists: {value.id}")
            self.agent_definitions[value.id] = value

    def add_subject(self, value: MemorySubject) -> None:
        with self._lock:
            if value.id in self.subjects:
                raise RepositoryError(f"Memory subject already exists: {value.id}")
            self.subjects[value.id] = value
            self.memory_entities[value.id] = MemoryEntity(
                id=value.id,
                subject_id=value.id,
                kind=MemoryEntityKind.SUBJECT,
                label=value.display_name or value.external_key,
                created_at=value.created_at,
            )

    def add_memory_entity(self, value: MemoryEntity) -> None:
        with self._lock:
            self.get_subject(value.subject_id)
            if value.id in self.memory_entities:
                raise RepositoryError(f"Memory entity already exists: {value.id}")
            if value.kind is MemoryEntityKind.SUBJECT:
                raise RepositoryError("Only add_subject may create a subject entity")
            self.memory_entities[value.id] = value

    def create_memory_entity(
        self,
        *,
        subject_id: str,
        kind: MemoryEntityKind,
        label: str = "",
    ) -> MemoryEntity:
        value = MemoryEntity(
            id=f"entity_{uuid4().hex}",
            subject_id=subject_id,
            kind=kind,
            label=label.strip(),
        )
        self.add_memory_entity(value)
        return value

    def get_memory_entity(self, entity_id: str) -> MemoryEntity:
        try:
            return self.memory_entities[entity_id]
        except KeyError as exc:
            raise NotFoundError(f"Memory entity not found: {entity_id}") from exc

    def list_subject_entities(self, subject_id: str) -> tuple[MemoryEntity, ...]:
        self.get_subject(subject_id)
        return tuple(
            sorted(
                (
                    entity
                    for entity in self.memory_entities.values()
                    if entity.subject_id == subject_id
                ),
                key=lambda entity: (entity.created_at, entity.id),
            )
        )

    def add_conversation(self, value: Conversation) -> None:
        with self._lock:
            if value.id in self.conversations:
                raise RepositoryError(f"Conversation already exists: {value.id}")
            if value.agent_definition_id not in self.agent_definitions:
                raise NotFoundError(value.agent_definition_id)
            if value.memory_subject_id not in self.subjects:
                raise NotFoundError(value.memory_subject_id)
            self.conversations[value.id] = value
            self.messages[value.id] = []

    def get_conversation(self, conversation_id: str) -> Conversation:
        try:
            return self.conversations[conversation_id]
        except KeyError as exc:
            raise NotFoundError(f"Conversation not found: {conversation_id}") from exc

    def get_agent_definition(self, agent_definition_id: str) -> AgentDefinition:
        try:
            return self.agent_definitions[agent_definition_id]
        except KeyError as exc:
            raise NotFoundError(
                f"Agent definition not found: {agent_definition_id}"
            ) from exc

    def get_subject(self, subject_id: str) -> MemorySubject:
        try:
            return self.subjects[subject_id]
        except KeyError as exc:
            raise NotFoundError(f"Memory subject not found: {subject_id}") from exc

    def append_message(
        self,
        *,
        conversation_id: str,
        role: MessageRole,
        content: str,
        run_id: str | None,
    ) -> Message:
        with self._lock:
            self.get_conversation(conversation_id)
            sequence = len(self.messages[conversation_id]) + 1
            message = Message(
                id=f"msg_{uuid4().hex}",
                conversation_id=conversation_id,
                sequence=sequence,
                role=role,
                content=content,
                run_id=run_id,
            )
            self.messages[conversation_id].append(message)
            return message

    def list_messages(self, conversation_id: str) -> tuple[Message, ...]:
        with self._lock:
            self.get_conversation(conversation_id)
            return tuple(self.messages[conversation_id])

    def put_summary(
        self,
        *,
        conversation_id: str,
        through_sequence: int,
        content: str,
        source_message_ids: tuple[str, ...],
        expected_version: int,
    ) -> ConversationSummary:
        with self._lock:
            self.get_conversation(conversation_id)
            versions = self.summaries.setdefault(conversation_id, [])
            current_version = versions[-1].version if versions else 0
            if current_version != expected_version:
                raise OptimisticConflictError(
                    f"Summary version {current_version} != expected {expected_version}"
                )
            messages = self.messages[conversation_id]
            if through_sequence < 0 or through_sequence > len(messages):
                raise RepositoryError("summary range is outside conversation history")
            expected_sources = tuple(
                message.id
                for message in messages
                if message.sequence <= through_sequence
            )
            if source_message_ids != expected_sources:
                raise RepositoryError(
                    "summary sources must cover a contiguous history prefix"
                )
            summary = ConversationSummary(
                id=f"summary_{uuid4().hex}",
                conversation_id=conversation_id,
                version=current_version + 1,
                through_sequence=through_sequence,
                content=content,
                source_message_ids=source_message_ids,
            )
            versions.append(summary)
            return summary

    def get_summary(self, conversation_id: str) -> ConversationSummary | None:
        versions = self.summaries.get(conversation_id, [])
        return versions[-1] if versions else None

    def list_summary_versions(
        self, conversation_id: str
    ) -> tuple[ConversationSummary, ...]:
        return tuple(self.summaries.get(conversation_id, []))

    def list_subject_facts(
        self, subject_id: str, *, active_only: bool = False
    ) -> tuple[MemoryFact, ...]:
        facts = [fact for fact in self.facts.values() if fact.subject_id == subject_id]
        if active_only:
            facts = [fact for fact in facts if fact.status.value == "active"]
        return tuple(sorted(facts, key=lambda item: (item.updated_at, item.id)))

    def get_fact(self, fact_id: str) -> MemoryFact:
        try:
            return self.facts[fact_id]
        except KeyError as exc:
            raise NotFoundError(f"Memory fact not found: {fact_id}") from exc

    def add_episode(self, episode: MemoryEpisode) -> None:
        with self._lock:
            self.get_subject(episode.subject_id)
            conversation = self.get_conversation(episode.conversation_id)
            if conversation.memory_subject_id != episode.subject_id:
                raise RepositoryError("episode conversation belongs to another subject")
            message_ids = {
                message.id for message in self.messages[episode.conversation_id]
            }
            if (
                not episode.source_message_ids
                or not set(episode.source_message_ids) <= message_ids
            ):
                raise RepositoryError(
                    "episode requires source messages from its conversation"
                )
            self.episodes.setdefault(episode.subject_id, []).append(episode)

    def list_episodes(self, subject_id: str) -> tuple[MemoryEpisode, ...]:
        return tuple(self.episodes.get(subject_id, []))

    def start_run(
        self,
        *,
        conversation_id: str,
        idempotency_key: str,
        request_hash: str,
    ) -> tuple[Run, TurnResult | None]:
        with self._lock:
            self.get_conversation(conversation_id)
            key = (conversation_id, idempotency_key)
            existing_run_id = self.idempotency.get(key)
            if existing_run_id:
                existing = self.runs[existing_run_id]
                if existing.request_hash != request_hash:
                    raise IdempotencyConflictError(
                        "Idempotency key was reused with a different request"
                    )
                if existing_run_id in self.results:
                    return existing, self.results[existing_run_id]
                raise IdempotencyConflictError(
                    f"Idempotency key is already in progress: {idempotency_key}"
                )
            run = Run(
                id=f"run_{uuid4().hex}",
                conversation_id=conversation_id,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                status=RunStatus.RUNNING,
            )
            self.runs[run.id] = run
            self.events[run.id] = []
            self.idempotency[key] = run.id
            return run, None

    def update_run(self, run_id: str, **updates: object) -> Run:
        with self._lock:
            current = self.runs[run_id]
            updated = replace(current, **updates)
            self.runs[run_id] = updated
            return updated

    def append_event(
        self, run_id: str, event_type, payload: dict[str, object]
    ) -> RunEvent:
        with self._lock:
            sequence = len(self.events[run_id]) + 1
            causation_id = self.events[run_id][-1].id if self.events[run_id] else None
            event = RunEvent(
                id=f"event_{uuid4().hex}",
                run_id=run_id,
                sequence=sequence,
                schema_version=1,
                type=event_type,
                attempt=(
                    int(payload["attempt"])
                    if isinstance(payload.get("attempt"), int)
                    else None
                ),
                correlation_id=run_id,
                causation_id=causation_id,
                visibility=RunEventVisibility.OPERATOR,
                payload=dict(payload),
            )
            self.events[run_id].append(event)
            return event

    def list_events(self, run_id: str) -> tuple[RunEvent, ...]:
        return tuple(self.events.get(run_id, []))

    def finish_run(
        self,
        run_id: str,
        *,
        status: RunStatus,
        attempt_count: int,
        error: Exception | None = None,
    ) -> Run:
        return self.update_run(
            run_id,
            status=status,
            attempt_count=attempt_count,
            error_type=type(error).__name__ if error else None,
            error_message=str(error) if error else None,
            finished_at=utc_now(),
        )

    def save_result(self, result: TurnResult) -> None:
        with self._lock:
            self.results[result.run.id] = result
