"""Append labeled synthetic transcript rows to test real UI citation paging."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from uuid import uuid4

from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)

from workflows.evals.deepseek_dev_smoke.isolation import isolated_database_url


async def seed(database_url: str, conversation_id: str) -> None:
    checked_url, database_name = isolated_database_url(database_url)
    if database_name != "ade_m2_memory_test_01a0ca1b":
        raise ValueError("M3 pagination seed is bound to the current disposable DB")
    if conversation_id != "e8bfba7e-6018-5f51-9797-07972a71a41d":
        raise ValueError("M3 pagination seed is bound to its synthetic source")
    engine = create_persistence_engine(checked_url)
    try:
        await RuntimeDatabase(engine).ensure_ready()
        async with engine.begin() as connection:
            repository = ConversationRepository(connection)
            conversation = await repository.get(conversation_id)
            if (
                conversation["purpose"] != "agent_studio"
                or str(conversation["memory_subject_id"])
                != "97472172-9388-5711-ab08-0ee9c0812e31"
                or conversation["archived_at"] is not None
            ):
                raise ValueError("Synthetic citation source identity changed")
            messages = await repository.list_messages(conversation_id)
            if len(messages) != 6 or messages[0]["content"] != "我喜欢喝红茶。":
                raise ValueError(
                    "Synthetic citation source is not at its native baseline"
                )
            for index in range(1, 126):
                content = f"Synthetic pagination fixture message {index:03d}; not a native turn."
                await repository.append_message(
                    {
                        "id": str(uuid4()),
                        "workspace_id": str(conversation["workspace_id"]),
                        "conversation_id": conversation_id,
                        "role": "user" if index % 2 else "assistant",
                        "content": content,
                        "content_sha256": hashlib.sha256(
                            content.encode("utf-8")
                        ).hexdigest(),
                        "run_id": None,
                    }
                )
            total = len(await repository.list_messages(conversation_id))
            if total != 131:
                raise RuntimeError("Synthetic citation pagination count changed")
        print(
            f"Seeded 125 labeled messages after the six native messages; "
            f"source {conversation_id} now has 131 messages."
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--conversation-id", required=True)
    arguments = parser.parse_args()
    asyncio.run(seed(arguments.database_url, arguments.conversation_id))
