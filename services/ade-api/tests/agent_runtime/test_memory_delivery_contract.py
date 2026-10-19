"""Source integrity and immutable retry identities, without a semantic reviewer."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from ade_api.integrations.hindsight_sources import (
    MemoryRelationship,
    MemorySourceMessage,
    prepare_memory_delivery,
)


RELATIONSHIP = MemoryRelationship("workspace-a", "subject-a", "character-a")
START = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


def source(sequence=1, **overrides):
    values = {
        "message_id": f"message-{sequence}",
        "conversation_id": "conversation-a",
        "definition_version_id": "definition-v1",
        "relationship": RELATIONSHIP,
        "sequence": sequence,
        "role": "user",
        "content": f"Original source {sequence}",
        "occurred_at": START + timedelta(seconds=sequence),
        "status": "accepted",
    }
    return MemorySourceMessage(**(values | overrides))


def test_delivery_preserves_source_and_separates_antecedents():
    first = source(content="我平时最常点茉莉茶。")
    second = source(2, role="assistant", status="committed", content="记下啦。")
    current = source(3, content="刚才说错了，我想说的是乌龙，不是茉莉。")
    delivery = prepare_memory_delivery(current, earlier_messages=(first, second))
    item = delivery.verify()["items"][0]
    assert json.loads(item["content"]) == current.as_dict()
    context = json.loads(item["context"])
    assert context["earlier_context_only"] == [first.as_dict(), second.as_dict()]
    assert item["timestamp"] == current.as_dict()["occurred_at"]
    assert item["metadata"]["speaker"] == "user"
    assert item["metadata"]["character_root_id"] == "character-a"
    assert item["metadata"]["definition_version_id"] == "definition-v1"
    assert item["document_id"] == "ade-message-message-3"
    assert item["update_mode"] == "replace"


def test_rebuilding_identical_source_keeps_operation_payload_and_original_time():
    current = source()
    first = prepare_memory_delivery(current)
    second = prepare_memory_delivery(current)
    assert first == second
    assert first.payload_sha256 == second.payload_sha256
    assert first.verify()["operation_id"] == first.operation_id
    assert first.verify()["items"][0]["timestamp"] == current.occurred_at.isoformat()


@pytest.mark.parametrize("field", ["workspace_id", "subject_id", "character_root_id"])
def test_every_ownership_component_changes_the_bank_and_operation(field):
    changed = replace(RELATIONSHIP, **{field: "different"})
    original = prepare_memory_delivery(source())
    other = prepare_memory_delivery(source(relationship=changed))
    assert original.bank_id != other.bank_id
    assert original.operation_id != other.operation_id


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "committed"},
        {"role": "assistant", "status": "accepted"},
        {"role": "system"},
        {"sequence": 0},
        {"occurred_at": datetime(2026, 10, 18)},
        {"content": "contains\x00nul"},
    ],
)
def test_only_valid_original_accepted_or_committed_sources_qualify(overrides):
    with pytest.raises(ValueError):
        source(**overrides)


@pytest.mark.parametrize(
    "earlier",
    [
        (source(conversation_id="other-chat"),),
        (source(relationship=replace(RELATIONSHIP, subject_id="other-person")),),
        (source(2), source(1)),
        (source(1), source(1)),
        (source(3),),
        (source(occurred_at=START + timedelta(days=1)),),
    ],
)
def test_antecedents_cannot_cross_conversations_owners_or_order(earlier):
    with pytest.raises(ValueError, match="Antecedents"):
        prepare_memory_delivery(source(3), earlier_messages=earlier)


def test_context_budget_keeps_whole_messages_and_never_truncates_current_source():
    earlier = (source(1, content="a" * 100), source(2, content="b" * 100))
    current = source(3, content="c" * 10_000)
    delivery = prepare_memory_delivery(
        current, earlier_messages=earlier, antecedent_characters=1
    )
    item = delivery.verify()["items"][0]
    assert json.loads(item["context"])["earlier_context_only"] == []
    assert json.loads(item["content"])["content"] == current.content


def test_corrupted_bytes_or_ownership_cannot_be_reused_as_a_delivery():
    delivery = prepare_memory_delivery(source())
    with pytest.raises(ValueError, match="payload changed"):
        replace(delivery, payload=delivery.payload + b" ").verify()
    with pytest.raises(ValueError, match="ownership"):
        replace(delivery, bank_id="another-bank").verify()


def test_definition_updates_preserve_bank_ownership_and_original_source_binding():
    first = prepare_memory_delivery(source())
    second = prepare_memory_delivery(source(2, definition_version_id="definition-v2"))
    assert first.bank_id == second.bank_id
    assert (
        first.verify()["items"][0]["metadata"]["definition_version_id"]
        == "definition-v1"
    )
    assert (
        second.verify()["items"][0]["metadata"]["definition_version_id"]
        == "definition-v2"
    )
