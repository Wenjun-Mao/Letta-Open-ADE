"""Actor-only native source fixtures, explicitly separate from ADE establishment."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from ade_api.integrations.hindsight_sources import (
    MemoryRelationship,
    MemorySourceMessage,
)

from .casebook import actor_material, load_suite


EXTRA_CASES = {
    "reference": {
        "history": [
            {"role": "user", "content": "我平时最常点乌龙茶。"},
            {"role": "assistant", "content": "那糖量呢？"},
            {"role": "user", "content": "无糖，还是刚才说的那种茶。"},
        ],
        "prompt": "我平时那杯茶的茶底和糖量是什么？",
    },
    "attribution": {
        "history": [
            {
                "role": "assistant",
                "content": "昨天傍晚我一个人在花店收完花，用蓝色棉线补好了自己的旧布袋。你当时没有在场。",
            },
            {"role": "user", "content": "听起来挺有生活气的。"},
        ],
        "prompt": "林小棠补布袋时用了什么线？用户当时在不在场？",
    },
}


def freeze_native_case(case_id: str) -> tuple[dict, list[MemorySourceMessage]]:
    suite = load_suite()
    if case_id in EXTRA_CASES:
        actor = EXTRA_CASES[case_id]
    else:
        case = suite["cases"][case_id]
        if case.history_kind != "user_dialogue":
            raise ValueError(
                "Native source gate uses user seeds or explicitly controlled sources"
            )
        actor = actor_material(case)
    relationship = MemoryRelationship(str(uuid4()), str(uuid4()), str(uuid4()))
    conversation, definition = str(uuid4()), str(uuid4())
    started = datetime.now(timezone.utc) - timedelta(seconds=len(actor["history"]) + 1)
    sources = [
        MemorySourceMessage(
            message_id=str(uuid4()),
            conversation_id=conversation,
            definition_version_id=definition,
            relationship=relationship,
            sequence=index,
            role=item["role"],
            content=item["content"],
            occurred_at=started + timedelta(seconds=index),
            status="accepted" if item["role"] == "user" else "committed",
        )
        for index, item in enumerate(actor["history"], 1)
    ]
    return {
        "case_id": case_id,
        "suite_sha256": suite["sha256"],
        "provenance": "controlled_native_sources_not_product_dialogue",
        "actor": actor,
        "relationship": relationship.as_dict(),
        "sources": [source.as_dict() for source in sources],
    }, sources
