from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

import httpx

from .contracts import (
    MemoryEntity,
    MemoryEntityKind,
    MemoryFact,
    MemoryOperation,
    MemoryProposal,
    Message,
    MessageRole,
)
from .fact_registry import (
    FACT_TYPE_REGISTRY,
    FactRegistryError,
    fact_key,
    fact_type_spec,
    normalize_qualifier,
)
from .memory import normalize_text
from .repository import InMemoryStudyRepository, NotFoundError


class MemoryReviewError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ReviewProtocolError(MemoryReviewError):
    pass


@dataclass(frozen=True)
class MemoryReviewProposal:
    operation: MemoryOperation
    fact_type: str
    value: str | None
    evidence_quote: str
    qualifier: str | None = None
    fact_id: str | None = None
    target_fact_ids: tuple[str, ...] = ()
    entity_ref: str | None = None
    new_entity_label: str = ""


@dataclass(frozen=True)
class MemoryReviewRequest:
    current_user_message: Message
    recent_user_messages: tuple[Message, ...]
    active_facts: tuple[MemoryFact, ...]
    entities: tuple[MemoryEntity, ...]
    timeout_seconds: float


@dataclass(frozen=True)
class MemoryReviewDecision:
    reviewer_model_key: str
    proposals: tuple[MemoryReviewProposal, ...]
    raw_responses: tuple[str, ...]
    usage: dict[str, int]
    model_request_count: int
    protocol_repaired: bool


@dataclass(frozen=True)
class PreparedMemoryReview:
    decision: MemoryReviewDecision
    new_entities: tuple[MemoryEntity, ...]
    proposals: tuple[MemoryProposal, ...]


class MemoryReviewer(Protocol):
    model_key: str

    async def review(self, request: MemoryReviewRequest) -> MemoryReviewDecision: ...


class ReviewerTransport(Protocol):
    async def complete(
        self, payload: dict[str, object], *, timeout_seconds: float
    ) -> dict[str, object]: ...


class NoopMemoryReviewer:
    model_key = "none"

    async def review(self, request: MemoryReviewRequest) -> MemoryReviewDecision:
        return MemoryReviewDecision(
            reviewer_model_key=self.model_key,
            proposals=(),
            raw_responses=(),
            usage={},
            model_request_count=0,
            protocol_repaired=False,
        )


class HttpxReviewerTransport:
    def __init__(self, *, base_url: str, api_key: str = "") -> None:
        self.url = f"{base_url.rstrip('/')}/chat/completions"
        self.api_key = api_key

    async def complete(
        self, payload: dict[str, object], *, timeout_seconds: float
    ) -> dict[str, object]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(self.url, headers=headers, json=payload)
        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.RemoteProtocolError,
        ) as exc:
            raise MemoryReviewError(str(exc), retryable=True) from exc
        if response.status_code == 429 or response.status_code >= 500:
            raise MemoryReviewError(
                f"Memory reviewer temporary failure ({response.status_code}): "
                f"{response.text[:500]}",
                retryable=True,
            )
        if response.status_code >= 400:
            raise MemoryReviewError(
                f"Memory reviewer request failed ({response.status_code}): "
                f"{response.text[:500]}"
            )
        try:
            value = response.json()
        except ValueError as exc:
            raise ReviewProtocolError(
                "Memory reviewer returned non-JSON HTTP content"
            ) from exc
        if not isinstance(value, dict):
            raise ReviewProtocolError("Memory reviewer returned a non-object response")
        return value


_PROPOSAL_FIELDS = {
    "operation",
    "fact_type",
    "value",
    "evidence_quote",
    "qualifier",
    "fact_id",
    "target_fact_ids",
    "entity_ref",
    "new_entity_label",
}


def parse_review_payload(
    payload: object,
    *,
    reviewer_model_key: str,
    raw_responses: tuple[str, ...] = (),
    usage: dict[str, int] | None = None,
    model_request_count: int = 1,
    protocol_repaired: bool = False,
) -> MemoryReviewDecision:
    if not isinstance(payload, dict):
        raise ReviewProtocolError("Reviewer output must be an object")
    unexpected_top = set(payload) - {"proposals"}
    if unexpected_top:
        raise ReviewProtocolError(
            f"Unexpected reviewer output fields: {sorted(unexpected_top)}"
        )
    proposals_raw = payload.get("proposals")
    if not isinstance(proposals_raw, list):
        raise ReviewProtocolError("Reviewer output must contain a proposals array")
    proposals: list[MemoryReviewProposal] = []
    for index, raw in enumerate(proposals_raw):
        if not isinstance(raw, dict):
            raise ReviewProtocolError(f"Proposal {index} must be an object")
        unexpected = set(raw) - _PROPOSAL_FIELDS
        if unexpected:
            raise ReviewProtocolError(
                f"Unexpected proposal {index} fields: {sorted(unexpected)}"
            )
        try:
            operation = MemoryOperation(str(raw.get("operation") or ""))
        except ValueError as exc:
            raise ReviewProtocolError(
                f"Proposal {index} has an invalid operation"
            ) from exc
        fact_type = str(raw.get("fact_type") or "").strip()
        try:
            spec = fact_type_spec(fact_type)
            qualifier = normalize_qualifier(spec, _optional_string(raw, "qualifier"))
        except FactRegistryError as exc:
            raise ReviewProtocolError(str(exc)) from exc
        evidence_quote = str(raw.get("evidence_quote") or "").strip()
        if not evidence_quote:
            raise ReviewProtocolError(f"Proposal {index} requires evidence_quote")
        value = _optional_string(raw, "value")
        if (
            operation
            in {
                MemoryOperation.ADD,
                MemoryOperation.CORRECT,
                MemoryOperation.MERGE,
            }
            and not value
        ):
            raise ReviewProtocolError(
                f"Proposal {index} requires value for {operation.value}"
            )
        if operation is MemoryOperation.FORGET and value is not None:
            raise ReviewProtocolError("Forget proposals must use a null value")
        target_fact_ids_raw = raw.get("target_fact_ids") or []
        if not isinstance(target_fact_ids_raw, list):
            raise ReviewProtocolError("target_fact_ids must be an array")
        proposals.append(
            MemoryReviewProposal(
                operation=operation,
                fact_type=spec.name,
                value=value,
                evidence_quote=evidence_quote,
                qualifier=qualifier,
                fact_id=_optional_string(raw, "fact_id"),
                target_fact_ids=tuple(
                    item
                    for item in (str(value).strip() for value in target_fact_ids_raw)
                    if item
                ),
                entity_ref=_optional_string(raw, "entity_ref"),
                new_entity_label=_optional_string(raw, "new_entity_label") or "",
            )
        )
    return MemoryReviewDecision(
        reviewer_model_key=reviewer_model_key,
        proposals=tuple(proposals),
        raw_responses=raw_responses,
        usage=dict(usage or {}),
        model_request_count=model_request_count,
        protocol_repaired=protocol_repaired,
    )


class RouterMemoryReviewer:
    def __init__(
        self,
        *,
        model_key: str,
        base_url: str = "http://model-router:8010/v1",
        api_key: str = "",
        transport: ReviewerTransport | None = None,
        max_output_tokens: int = 2048,
    ) -> None:
        self.model_key = model_key
        self.transport = transport or HttpxReviewerTransport(
            base_url=base_url,
            api_key=api_key,
        )
        self.max_output_tokens = max_output_tokens

    async def review(self, request: MemoryReviewRequest) -> MemoryReviewDecision:
        messages = [
            {"role": "system", "content": _reviewer_system_prompt()},
            {"role": "user", "content": _reviewer_input(request)},
        ]
        raw_responses: list[str] = []
        usage: dict[str, int] = {}
        first_error: ReviewProtocolError | None = None
        for request_index in (1, 2):
            payload = self._payload(messages)
            response = await self.transport.complete(
                payload,
                timeout_seconds=request.timeout_seconds,
            )
            raw = _completion_content(response)
            raw_responses.append(raw)
            _merge_usage(usage, response.get("usage"))
            try:
                decoded = _decode_json_object(raw)
                return parse_review_payload(
                    decoded,
                    reviewer_model_key=self.model_key,
                    raw_responses=tuple(raw_responses),
                    usage=usage,
                    model_request_count=request_index,
                    protocol_repaired=request_index == 2,
                )
            except ReviewProtocolError as exc:
                if request_index == 2:
                    raise ReviewProtocolError(
                        f"Memory review schema remained invalid after one repair: {exc}"
                    ) from exc
                first_error = exc
                messages.extend(
                    (
                        {"role": "assistant", "content": raw},
                        {
                            "role": "user",
                            "content": (
                                "Your output violated the required JSON schema: "
                                f"{exc}. Return one corrected JSON object only."
                            ),
                        },
                    )
                )
        raise ReviewProtocolError(str(first_error or "unknown memory review failure"))

    def _payload(self, messages: list[dict[str, str]]) -> dict[str, object]:
        return {
            "model": self.model_key,
            "messages": messages,
            "stream": False,
            "temperature": 0,
            "max_tokens": self.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ade_memory_review",
                    "strict": True,
                    "schema": _review_schema(),
                },
            },
            "chat_template_kwargs": {"enable_thinking": False},
        }


class MemoryReviewCoordinator:
    def __init__(
        self,
        repository: InMemoryStudyRepository,
        *,
        entity_id_factory=None,
    ) -> None:
        self.repository = repository
        self.entity_id_factory = entity_id_factory or (lambda: f"entity_{uuid4().hex}")

    def prepare(
        self,
        *,
        subject_id: str,
        current_user_message: Message,
        decision: MemoryReviewDecision,
    ) -> PreparedMemoryReview:
        conversation = self.repository.get_conversation(
            current_user_message.conversation_id
        )
        if current_user_message.role is not MessageRole.USER:
            raise MemoryReviewError("Memory review evidence must be a user message")
        if conversation.memory_subject_id != subject_id:
            raise MemoryReviewError(
                "Memory review evidence is not bound to the requested subject"
            )
        current_text = normalize_text(current_user_message.content)
        active_facts = {
            fact.id: fact
            for fact in self.repository.list_subject_facts(subject_id, active_only=True)
        }
        entities = {
            entity.id: entity
            for entity in self.repository.list_subject_entities(subject_id)
        }
        new_by_ref: dict[str, MemoryEntity] = {}
        prepared: list[MemoryProposal] = []
        for proposal in decision.proposals:
            quote = normalize_text(proposal.evidence_quote)
            if not quote or quote not in current_text:
                raise MemoryReviewError(
                    "evidence_quote must be an exact excerpt from the current user message"
                )
            spec = fact_type_spec(proposal.fact_type)
            qualifier = normalize_qualifier(spec, proposal.qualifier)
            fact = active_facts.get(proposal.fact_id or "")
            if proposal.operation in {MemoryOperation.CORRECT, MemoryOperation.FORGET}:
                if fact is None:
                    raise MemoryReviewError(
                        f"{proposal.operation.value} requires an active fact_id"
                    )
                if fact.fact_type != spec.name or fact.qualifier != qualifier:
                    raise MemoryReviewError(
                        "reviewed fact metadata does not match the selected active fact"
                    )
                entity = self._bound_entity(
                    subject_id, fact.entity_id, spec.entity_kind, entities
                )
                if proposal.entity_ref:
                    raise MemoryReviewError(
                        "correction and forget operations derive entity from fact_id"
                    )
            else:
                entity = self._resolve_entity(
                    subject_id=subject_id,
                    spec_kind=spec.entity_kind,
                    proposal=proposal,
                    entities=entities,
                    new_by_ref=new_by_ref,
                )
            target_facts = tuple(
                active_facts.get(fact_id) for fact_id in proposal.target_fact_ids
            )
            if proposal.operation is MemoryOperation.MERGE:
                if len(target_facts) < 2 or any(item is None for item in target_facts):
                    raise MemoryReviewError("merge requires at least two active facts")
            key = fact_key(spec.name, entity.id, qualifier)
            prepared.append(
                MemoryProposal(
                    operation=proposal.operation,
                    key=key,
                    value=proposal.value,
                    evidence_quote=proposal.evidence_quote,
                    fact_id=fact.id if fact else proposal.fact_id,
                    target_fact_ids=proposal.target_fact_ids,
                    expected_version=fact.version if fact else None,
                    expected_versions={
                        item.id: item.version
                        for item in target_facts
                        if item is not None
                    },
                    fact_type=spec.name,
                    entity_id=entity.id,
                    qualifier=qualifier,
                )
            )
        return PreparedMemoryReview(
            decision=decision,
            new_entities=tuple(new_by_ref.values()),
            proposals=tuple(prepared),
        )

    def _resolve_entity(
        self,
        *,
        subject_id: str,
        spec_kind: MemoryEntityKind,
        proposal: MemoryReviewProposal,
        entities: dict[str, MemoryEntity],
        new_by_ref: dict[str, MemoryEntity],
    ) -> MemoryEntity:
        if spec_kind is MemoryEntityKind.SUBJECT:
            if proposal.entity_ref:
                raise MemoryReviewError("subject facts cannot select another entity")
            return self._bound_entity(
                subject_id,
                subject_id,
                spec_kind,
                entities,
            )
        ref = str(proposal.entity_ref or "").strip()
        if ref.startswith("existing:"):
            entity_id = ref.removeprefix("existing:").strip()
            if not entity_id:
                raise MemoryReviewError("existing entity_ref requires an entity id")
            return self._bound_entity(subject_id, entity_id, spec_kind, entities)
        spec = fact_type_spec(proposal.fact_type)
        if not ref and proposal.operation is MemoryOperation.ADD:
            if spec.defines_entity_identity:
                ref = f"new:auto-{len(new_by_ref) + 1}"
        if not ref.startswith("new:") or not ref.removeprefix("new:").strip():
            raise MemoryReviewError(
                f"{proposal.fact_type} requires existing:<id> or new:<local-ref>"
            )
        existing = new_by_ref.get(ref)
        if existing:
            if existing.kind is not spec_kind:
                raise MemoryReviewError("entity_ref was reused with another kind")
            return existing
        label = proposal.new_entity_label.strip()
        if not label and proposal.fact_type.endswith(".name"):
            label = str(proposal.value or "").strip()
        entity = MemoryEntity(
            id=self.entity_id_factory(),
            subject_id=subject_id,
            kind=spec_kind,
            label=label,
        )
        new_by_ref[ref] = entity
        return entity

    @staticmethod
    def _bound_entity(
        subject_id: str,
        entity_id: str,
        expected_kind: MemoryEntityKind,
        entities: dict[str, MemoryEntity],
    ) -> MemoryEntity:
        entity = entities.get(entity_id)
        if entity is None:
            try:
                raise NotFoundError(entity_id)
            except NotFoundError as exc:
                raise MemoryReviewError(
                    "reviewed entity does not belong to the bound subject"
                ) from exc
        if entity.subject_id != subject_id:
            raise MemoryReviewError(
                "reviewed entity does not belong to the bound subject"
            )
        if entity.kind is not expected_kind:
            raise MemoryReviewError(
                f"reviewed entity kind must be {expected_kind.value}"
            )
        return entity


def _optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _completion_content(payload: dict[str, object]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ReviewProtocolError("Memory reviewer completion has no choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ReviewProtocolError("Memory reviewer completion has no message")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(item.get("text") or "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    raise ReviewProtocolError("Memory reviewer completion has no text content")


def _decode_json_object(raw: str) -> dict[str, object]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReviewProtocolError("Memory reviewer output is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ReviewProtocolError("Memory reviewer output must be a JSON object")
    return value


def _merge_usage(target: dict[str, int], raw: object) -> None:
    if not isinstance(raw, dict):
        return
    for key, value in raw.items():
        if isinstance(value, (int, float)):
            target[str(key)] = target.get(str(key), 0) + int(value)


def _review_schema() -> dict[str, object]:
    proposal_properties: dict[str, object] = {
        "operation": {
            "type": "string",
            "enum": [item.value for item in MemoryOperation],
        },
        "fact_type": {"type": "string", "enum": sorted(FACT_TYPE_REGISTRY)},
        "value": {"type": ["string", "null"]},
        "evidence_quote": {"type": "string", "minLength": 1},
        "qualifier": {"type": ["string", "null"]},
        "fact_id": {"type": ["string", "null"]},
        "target_fact_ids": {"type": "array", "items": {"type": "string"}},
        "entity_ref": {"type": ["string", "null"]},
        "new_entity_label": {"type": ["string", "null"]},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "proposals": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": proposal_properties,
                    "required": [
                        "operation",
                        "fact_type",
                        "value",
                        "evidence_quote",
                        "qualifier",
                        "fact_id",
                        "target_fact_ids",
                        "entity_ref",
                        "new_entity_label",
                    ],
                },
            }
        },
        "required": ["proposals"],
    }


def _reviewer_system_prompt() -> str:
    registry = "\n".join(
        f"- {name}: entity={spec.entity_kind.value}; "
        f"qualifiers={','.join(spec.allowed_qualifiers) or 'none'}; "
        f"implicit_new_entity={str(spec.defines_entity_identity).lower()}"
        for name, spec in FACT_TYPE_REGISTRY.items()
    )
    return f"""You are ADE's dedicated durable-memory reviewer.
Return only the required JSON object. The conversational model does not write memory.

Evidence policy:
- Store only durable user facts explicitly stated or explicitly corrected in the CURRENT user message.
- evidence_quote must be an exact current-message excerpt. Prior USER turns and active facts may resolve references, but are never valid evidence for a new write.
- value must use the user's exact wording from the current message. Never translate, paraphrase, normalize, or copy an answer from active memory.
- Do not store guesses, hypotheticals, temporary plans, assistant claims, or inferred facts.
- Questions about existing memory do not create or re-add facts.
- Forget only when the current message explicitly asks to forget/remove a fact.
- Never output a subject id or a free-form key. Fact keys and optimistic versions are server-owned.
- Use fact_id only for an active correction/forget; leave entity_ref null because ADE derives the entity from fact_id.
- For a subject fact, leave entity_ref null. A new pet.name or relationship.person may also leave entity_ref null; ADE creates that entity. For existing non-subject entities, use inventory values like existing:<id>. When one turn proposes multiple facts for the same new entity, reuse one new:<local-ref> across them. ADE assigns persistent IDs and entity kinds.
- Example: after an existing pet.name=Rocky, 'it is a Husky' adds pet.breed=Husky using Rocky's existing:<id> reference. It must preserve both facts.
- Example: '我最喜欢的颜色是蓝色' stores value '蓝色', never 'blue'.
- Hard negative: '也许以后我会养一只叫Milo的猫，但现在没有' produces an empty proposals array.
- Hard negative: '我最喜欢哪一家博物馆？' produces no proposal even when active memory contains the answer.

Fact registry:
{registry}
"""


def _reviewer_input(request: MemoryReviewRequest) -> str:
    entity_by_id = {entity.id: entity for entity in request.entities}
    facts = [
        {
            "fact_id": fact.id,
            "fact_type": fact.fact_type,
            "entity_ref": (
                f"existing:{fact.entity_id}"
                if entity_by_id[fact.entity_id].kind is not MemoryEntityKind.SUBJECT
                else None
            ),
            "qualifier": fact.qualifier,
            "value": fact.value,
            "version": fact.version,
        }
        for fact in request.active_facts
    ]
    entities = [
        {
            "entity_ref": f"existing:{entity.id}",
            "kind": entity.kind.value,
            "label": entity.label,
        }
        for entity in request.entities
        if entity.kind is not MemoryEntityKind.SUBJECT
    ]
    recent = [
        {"role": message.role.value, "content": message.content}
        for message in request.recent_user_messages[-8:]
        if message.role is MessageRole.USER
    ]
    return json.dumps(
        {
            "current_user_message": request.current_user_message.content,
            "recent_user_messages_for_reference_resolution_only": recent,
            "active_facts": facts,
            "non_subject_entities": entities,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


__all__ = [
    "FactRegistryError",
    "MemoryEntityKind",
    "MemoryReviewCoordinator",
    "MemoryReviewDecision",
    "MemoryReviewError",
    "MemoryReviewProposal",
    "MemoryReviewRequest",
    "MemoryReviewer",
    "NoopMemoryReviewer",
    "PreparedMemoryReview",
    "ReviewProtocolError",
    "RouterMemoryReviewer",
    "fact_key",
    "parse_review_payload",
]
