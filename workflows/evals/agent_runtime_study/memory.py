from __future__ import annotations

import hashlib
import re
from dataclasses import replace
from uuid import uuid4

from .contracts import (
    MemoryEpisode,
    MemoryFact,
    MemoryFactStatus,
    MemoryEvidenceSpan,
    MemoryOperation,
    MemoryProposal,
    MemoryRevision,
    Message,
    utc_now,
)
from .fact_registry import fact_key, fact_type_spec, normalize_qualifier
from .repository import (
    InMemoryStudyRepository,
    NotFoundError,
    OptimisticConflictError,
    RepositoryError,
)
from .semantic_retrieval import (
    EmbeddingProvider,
    RetrievalConfig,
    RetrievalDocument,
    SemanticRetriever,
)


class MemoryProposalError(ValueError):
    pass


_UNCERTAIN_MARKERS = (
    "maybe",
    "perhaps",
    "might",
    "possibly",
    "guess",
    "假设",
    "也许",
    "可能",
    "大概",
    "猜",
)
_FORGET_MARKERS = ("forget", "remove", "delete", "忘", "删除", "不要记")
_VALUE_STOPWORDS = {"a", "an", "and", "as", "is", "my", "the", "to"}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


class MemoryPolicy:
    """Validates explicit evidence and applies versioned memory operations."""

    def __init__(self, repository: InMemoryStudyRepository):
        self.repository = repository

    def validate_proposal(
        self,
        *,
        subject_id: str,
        proposal: MemoryProposal,
        source_messages: tuple[Message, ...],
    ) -> None:
        if not proposal.key.strip():
            raise MemoryProposalError("key is required")
        if proposal.fact_type:
            spec = fact_type_spec(proposal.fact_type)
            qualifier = normalize_qualifier(spec, proposal.qualifier)
            if not proposal.entity_id:
                raise MemoryProposalError("entity_id is required for typed facts")
            entity = self.repository.get_memory_entity(proposal.entity_id)
            if entity.subject_id != subject_id:
                raise MemoryProposalError("memory entity belongs to another subject")
            if entity.kind is not spec.entity_kind:
                raise MemoryProposalError(
                    f"memory entity kind must be {spec.entity_kind.value}"
                )
            expected_key = fact_key(spec.name, entity.id, qualifier)
            if proposal.key != expected_key:
                raise MemoryProposalError(
                    "typed memory key must be derived from fact type and entity"
                )
        if not proposal.evidence_quote.strip():
            raise MemoryProposalError("evidence_quote is required")
        if any(message.role.value != "user" for message in source_messages):
            raise MemoryProposalError("memory evidence must come from user messages")
        if any(
            self.repository.get_conversation(message.conversation_id).memory_subject_id
            != subject_id
            for message in source_messages
        ):
            raise MemoryProposalError(
                "memory evidence must come from a conversation bound to the subject"
            )
        evidence_spans = _evidence_spans(proposal.evidence_quote, source_messages)
        quote = normalize_text(proposal.evidence_quote)
        source_text = " ".join(
            normalize_text(message.content) for message in source_messages
        )
        if not evidence_spans:
            raise MemoryProposalError(
                "evidence_quote must be an exact excerpt from a bound user message"
            )
        if any(marker in source_text for marker in _UNCERTAIN_MARKERS):
            raise MemoryProposalError(
                "uncertain or hypothetical claims are not durable facts"
            )

        if proposal.operation in {MemoryOperation.ADD, MemoryOperation.MERGE}:
            if not str(proposal.value or "").strip():
                raise MemoryProposalError(f"value is required for {proposal.operation}")
        if proposal.operation is MemoryOperation.FORGET and not any(
            marker in quote for marker in _FORGET_MARKERS
        ):
            raise MemoryProposalError("forget requires explicit user intent")
        if proposal.operation in {MemoryOperation.CORRECT, MemoryOperation.FORGET}:
            if not proposal.fact_id:
                raise MemoryProposalError(
                    f"fact_id is required for {proposal.operation}"
                )
            fact = self.repository.get_fact(proposal.fact_id)
            if fact.subject_id != subject_id:
                raise MemoryProposalError("fact does not belong to the bound subject")
            if fact.status is not MemoryFactStatus.ACTIVE:
                raise MemoryProposalError("only active facts can be changed")
            if proposal.expected_version != fact.version:
                raise OptimisticConflictError(
                    f"Fact version {fact.version} != expected {proposal.expected_version}"
                )
            if proposal.fact_type and (
                fact.fact_type != proposal.fact_type
                or fact.entity_id != proposal.entity_id
                or fact.qualifier != proposal.qualifier
            ):
                raise MemoryProposalError(
                    "typed mutation metadata must match the active fact"
                )
        if (
            proposal.operation is MemoryOperation.CORRECT
            and not str(proposal.value or "").strip()
        ):
            raise MemoryProposalError("value is required for correct")
        if proposal.operation is MemoryOperation.MERGE:
            if len(proposal.target_fact_ids) < 2:
                raise MemoryProposalError("merge requires at least two target facts")
            if len(set(proposal.target_fact_ids)) != len(proposal.target_fact_ids):
                raise MemoryProposalError("merge target facts must be unique")
            for fact_id in proposal.target_fact_ids:
                fact = self.repository.get_fact(fact_id)
                if fact.subject_id != subject_id:
                    raise MemoryProposalError("merge target belongs to another subject")
                if fact.status is not MemoryFactStatus.ACTIVE:
                    raise MemoryProposalError("merge targets must be active")
                if proposal.expected_versions.get(fact_id) != fact.version:
                    raise OptimisticConflictError(
                        f"Fact version {fact.version} != expected "
                        f"{proposal.expected_versions.get(fact_id)}"
                    )

        support_text = quote
        if proposal.operation is MemoryOperation.CORRECT and proposal.fact_id:
            support_text = (
                f"{support_text} {self.repository.get_fact(proposal.fact_id).value}"
            )
        elif proposal.operation is MemoryOperation.MERGE:
            support_text = " ".join(
                (
                    support_text,
                    *(
                        self.repository.get_fact(item).value
                        for item in proposal.target_fact_ids
                    ),
                )
            )
        if proposal.operation in {
            MemoryOperation.ADD,
            MemoryOperation.CORRECT,
            MemoryOperation.MERGE,
        } and not _value_supported_by_evidence(str(proposal.value or ""), support_text):
            raise MemoryProposalError(
                "value is not supported by current or prior bound evidence"
            )

    def apply_batch(
        self,
        *,
        subject_id: str,
        proposals: tuple[MemoryProposal, ...],
        source_messages: tuple[Message, ...],
        run_id: str,
    ) -> tuple[MemoryRevision, ...]:
        self.validate_batch(
            subject_id=subject_id,
            proposals=proposals,
            source_messages=source_messages,
        )

        revisions: list[MemoryRevision] = []
        for proposal in proposals:
            if proposal.operation is MemoryOperation.ADD:
                revisions.append(
                    self._add(subject_id, proposal, source_messages, run_id)
                )
            elif proposal.operation is MemoryOperation.CORRECT:
                revisions.append(
                    self._correct(subject_id, proposal, source_messages, run_id)
                )
            elif proposal.operation is MemoryOperation.MERGE:
                revisions.append(
                    self._merge(subject_id, proposal, source_messages, run_id)
                )
            elif proposal.operation is MemoryOperation.FORGET:
                revisions.append(
                    self._forget(subject_id, proposal, source_messages, run_id)
                )
        return tuple(revisions)

    def validate_batch(
        self,
        *,
        subject_id: str,
        proposals: tuple[MemoryProposal, ...],
        source_messages: tuple[Message, ...],
    ) -> None:
        for proposal in proposals:
            self.validate_proposal(
                subject_id=subject_id,
                proposal=proposal,
                source_messages=source_messages,
            )

        projected_keys = {
            normalize_text(fact.key): fact.id
            for fact in self.repository.list_subject_facts(subject_id, active_only=True)
        }
        mutated_fact_ids: set[str] = set()
        for index, proposal in enumerate(proposals):
            target_ids: tuple[str, ...]
            if proposal.operation in {MemoryOperation.CORRECT, MemoryOperation.FORGET}:
                target_ids = (str(proposal.fact_id),)
            elif proposal.operation is MemoryOperation.MERGE:
                target_ids = proposal.target_fact_ids
            else:
                target_ids = ()

            repeated_targets = mutated_fact_ids.intersection(target_ids)
            if repeated_targets:
                raise MemoryProposalError(
                    "a fact can be changed only once in one memory batch: "
                    f"{sorted(repeated_targets)}"
                )
            mutated_fact_ids.update(target_ids)
            for fact_id in target_ids:
                fact = self.repository.get_fact(fact_id)
                projected_keys.pop(normalize_text(fact.key), None)

            if proposal.operation is MemoryOperation.FORGET:
                continue
            key = normalize_text(proposal.key)
            if key in projected_keys:
                raise MemoryProposalError(
                    f"Active or staged fact already uses key '{proposal.key}'"
                )
            projected_keys[key] = proposal.fact_id or f"staged_{index}"

    def _revision(
        self,
        *,
        fact_id: str,
        subject_id: str,
        proposal: MemoryProposal,
        fact_version: int,
        prior_revision_ids: tuple[str, ...],
        source_messages: tuple[Message, ...],
        run_id: str,
    ) -> MemoryRevision:
        revision = MemoryRevision(
            id=f"revision_{uuid4().hex}",
            fact_id=fact_id,
            subject_id=subject_id,
            operation=proposal.operation,
            key=proposal.key.strip(),
            value=str(proposal.value).strip() if proposal.value is not None else None,
            fact_version=fact_version,
            source_message_ids=tuple(message.id for message in source_messages),
            prior_revision_ids=prior_revision_ids,
            run_id=run_id,
            evidence_quote=proposal.evidence_quote.strip(),
            evidence_spans=_evidence_spans(
                proposal.evidence_quote,
                source_messages,
            ),
            fact_type=proposal.fact_type,
            entity_id=proposal.entity_id,
            qualifier=proposal.qualifier,
        )
        self.repository.revisions.setdefault(fact_id, []).append(revision)
        return revision

    def _add(
        self,
        subject_id: str,
        proposal: MemoryProposal,
        source_messages: tuple[Message, ...],
        run_id: str,
    ) -> MemoryRevision:
        key = normalize_text(proposal.key)
        duplicate = next(
            (
                fact
                for fact in self.repository.list_subject_facts(
                    subject_id, active_only=True
                )
                if normalize_text(fact.key) == key
            ),
            None,
        )
        if duplicate:
            raise MemoryProposalError(
                f"Active fact already uses key '{proposal.key}'; correct it instead"
            )
        fact_id = f"fact_{uuid4().hex}"
        revision = self._revision(
            fact_id=fact_id,
            subject_id=subject_id,
            proposal=proposal,
            fact_version=1,
            prior_revision_ids=(),
            source_messages=source_messages,
            run_id=run_id,
        )
        now = utc_now()
        self.repository.facts[fact_id] = MemoryFact(
            id=fact_id,
            subject_id=subject_id,
            key=proposal.key.strip(),
            value=str(proposal.value or "").strip(),
            status=MemoryFactStatus.ACTIVE,
            version=1,
            current_revision_id=revision.id,
            created_at=now,
            updated_at=now,
            fact_type=proposal.fact_type,
            entity_id=proposal.entity_id,
            qualifier=proposal.qualifier,
        )
        return revision

    def _correct(
        self,
        subject_id: str,
        proposal: MemoryProposal,
        source_messages: tuple[Message, ...],
        run_id: str,
    ) -> MemoryRevision:
        if not proposal.fact_id:
            raise MemoryProposalError("fact_id is required")
        fact = self.repository.get_fact(proposal.fact_id)
        prior = tuple(
            revision.id for revision in self.repository.revisions.get(fact.id, [])
        )
        revision = self._revision(
            fact_id=fact.id,
            subject_id=subject_id,
            proposal=proposal,
            fact_version=fact.version + 1,
            prior_revision_ids=prior,
            source_messages=source_messages,
            run_id=run_id,
        )
        self.repository.facts[fact.id] = replace(
            fact,
            key=proposal.key.strip(),
            value=str(proposal.value or "").strip(),
            fact_type=proposal.fact_type or fact.fact_type,
            entity_id=proposal.entity_id or fact.entity_id,
            qualifier=(proposal.qualifier if proposal.fact_type else fact.qualifier),
            version=fact.version + 1,
            current_revision_id=revision.id,
            updated_at=utc_now(),
        )
        return revision

    def _merge(
        self,
        subject_id: str,
        proposal: MemoryProposal,
        source_messages: tuple[Message, ...],
        run_id: str,
    ) -> MemoryRevision:
        targets = [self.repository.get_fact(item) for item in proposal.target_fact_ids]
        for target in targets:
            self.repository.facts[target.id] = replace(
                target,
                status=MemoryFactStatus.SUPERSEDED,
                updated_at=utc_now(),
            )
        fact_id = f"fact_{uuid4().hex}"
        prior = tuple(target.current_revision_id for target in targets)
        revision = self._revision(
            fact_id=fact_id,
            subject_id=subject_id,
            proposal=proposal,
            fact_version=1,
            prior_revision_ids=prior,
            source_messages=source_messages,
            run_id=run_id,
        )
        now = utc_now()
        self.repository.facts[fact_id] = MemoryFact(
            id=fact_id,
            subject_id=subject_id,
            key=proposal.key.strip(),
            value=str(proposal.value or "").strip(),
            status=MemoryFactStatus.ACTIVE,
            version=1,
            current_revision_id=revision.id,
            created_at=now,
            updated_at=now,
            fact_type=proposal.fact_type,
            entity_id=proposal.entity_id,
            qualifier=proposal.qualifier,
        )
        return revision

    def _forget(
        self,
        subject_id: str,
        proposal: MemoryProposal,
        source_messages: tuple[Message, ...],
        run_id: str,
    ) -> MemoryRevision:
        if not proposal.fact_id:
            raise MemoryProposalError("fact_id is required")
        fact = self.repository.get_fact(proposal.fact_id)
        prior = tuple(
            revision.id for revision in self.repository.revisions.get(fact.id, [])
        )
        revision = self._revision(
            fact_id=fact.id,
            subject_id=subject_id,
            proposal=proposal,
            fact_version=fact.version + 1,
            prior_revision_ids=prior,
            source_messages=source_messages,
            run_id=run_id,
        )
        self.repository.facts[fact.id] = replace(
            fact,
            status=MemoryFactStatus.FORGOTTEN,
            version=fact.version + 1,
            current_revision_id=revision.id,
            updated_at=utc_now(),
        )
        return revision


def _terms(value: str) -> set[str]:
    normalized = normalize_text(value).replace("_", " ")
    latin = set(re.findall(r"[a-z0-9_]+", normalized))
    cjk = set(re.findall(r"[\u4e00-\u9fff]", normalized))
    return latin | cjk


def _value_supported_by_evidence(value: str, evidence_quote: str) -> bool:
    normalized_value = normalize_text(value)
    normalized_quote = normalize_text(evidence_quote)
    if normalized_value and normalized_value in normalized_quote:
        return True
    value_terms = _terms(normalized_value) - _VALUE_STOPWORDS
    quote_terms = _terms(normalized_quote) - _VALUE_STOPWORDS
    return bool(value_terms) and value_terms <= quote_terms


def _evidence_spans(
    evidence_quote: str,
    source_messages: tuple[Message, ...],
) -> tuple[MemoryEvidenceSpan, ...]:
    quote = evidence_quote.strip()
    if not quote:
        return ()
    spans: list[MemoryEvidenceSpan] = []
    for message in source_messages:
        start = message.content.casefold().find(quote.casefold())
        if start < 0:
            continue
        spans.append(
            MemoryEvidenceSpan(
                message_id=message.id,
                start_char=start,
                end_char=start + len(quote),
                quote=message.content[start : start + len(quote)],
                message_sha256=hashlib.sha256(
                    message.content.encode("utf-8")
                ).hexdigest(),
            )
        )
    return tuple(spans)


class MemoryRetriever:
    def __init__(
        self,
        repository: InMemoryStudyRepository,
        *,
        embeddings: EmbeddingProvider | None = None,
        semantic_config: RetrievalConfig | None = None,
    ):
        self.repository = repository
        self.embeddings = embeddings
        self.semantic_config = semantic_config

    @staticmethod
    def _score(query: str, text: str) -> float:
        query_terms = _terms(query)
        if not query_terms:
            return 0.0
        text_terms = _terms(text)
        overlap = len(query_terms & text_terms)
        phrase_bonus = 1.0 if normalize_text(query) in normalize_text(text) else 0.0
        return overlap / len(query_terms) + phrase_bonus

    def search_facts(
        self,
        subject_id: str,
        query: str,
        *,
        limit: int,
        minimum_score: float | None | object = ...,
    ) -> tuple[MemoryFact, ...]:
        candidates = self.repository.list_subject_facts(subject_id, active_only=True)
        if self.embeddings is not None:
            documents = tuple(
                RetrievalDocument(
                    id=fact.id,
                    subject_id=fact.subject_id,
                    text=f"{fact.fact_type or fact.key}: {fact.value}",
                    aliases=tuple(
                        value
                        for value in (
                            fact.key,
                            fact.value,
                            fact.qualifier,
                        )
                        if value
                    ),
                )
                for fact in candidates
            )
            ranked_ids = self._semantic_ids(
                documents,
                subject_id=subject_id,
                query=query,
                limit=limit,
                minimum_score=minimum_score,
            )
            by_id = {fact.id: fact for fact in candidates}
            return tuple(by_id[fact_id] for fact_id in ranked_ids)
        ranked = sorted(
            candidates,
            key=lambda fact: (
                self._score(query, f"{fact.key} {fact.value}"),
                fact.updated_at,
            ),
            reverse=True,
        )
        return tuple(
            fact
            for fact in ranked
            if self._score(query, f"{fact.key} {fact.value}") > 0
        )[:limit]

    def search_episodes(
        self,
        subject_id: str,
        query: str,
        *,
        limit: int,
        minimum_score: float | None | object = ...,
    ) -> tuple[MemoryEpisode, ...]:
        candidates = self.repository.list_episodes(subject_id)
        if self.embeddings is not None:
            documents = tuple(
                RetrievalDocument(
                    id=episode.id,
                    subject_id=episode.subject_id,
                    text=episode.content,
                )
                for episode in candidates
            )
            ranked_ids = self._semantic_ids(
                documents,
                subject_id=subject_id,
                query=query,
                limit=limit,
                minimum_score=minimum_score,
            )
            by_id = {episode.id: episode for episode in candidates}
            return tuple(by_id[episode_id] for episode_id in ranked_ids)
        ranked = sorted(
            candidates,
            key=lambda episode: (
                self._score(query, episode.content),
                episode.created_at,
            ),
            reverse=True,
        )
        return tuple(
            episode for episode in ranked if self._score(query, episode.content) > 0
        )[:limit]

    def _semantic_ids(
        self,
        documents: tuple[RetrievalDocument, ...],
        *,
        subject_id: str,
        query: str,
        limit: int,
        minimum_score: float | None | object,
    ) -> tuple[str, ...]:
        if not documents:
            return ()
        retriever = SemanticRetriever(
            documents,
            self.embeddings,
            config=self.semantic_config,
        )
        return tuple(
            result.document.id
            for result in retriever.search(
                subject_id,
                query,
                limit=limit,
                minimum_score=minimum_score,
            )
        )


def assert_fact_subject(fact: MemoryFact, subject_id: str) -> None:
    if fact.subject_id != subject_id:
        raise RepositoryError("Cross-subject memory access was blocked")


def find_fact(repository: InMemoryStudyRepository, fact_id: str) -> MemoryFact:
    try:
        return repository.get_fact(fact_id)
    except NotFoundError as exc:
        raise MemoryProposalError(str(exc)) from exc
