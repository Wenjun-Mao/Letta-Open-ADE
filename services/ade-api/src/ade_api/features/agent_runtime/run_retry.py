"""Retry one accepted input; never append or redeliver a second user message."""

from uuid import uuid4

from .contracts import RetryRunRequest
from .errors import RuntimeConflict
from .events import append_run_event
from .persistence.conversations import ConversationRepository
from .persistence.leases import ConversationLeaseRepository
from .persistence.memory import MemoryRepository
from .persistence.run_lifecycle import RunLifecycleRepository, lock_run
from .persistence.runs import RunRepository
from .presenters import turn_accepted_response


async def retry_saved_input(database, run_id: str, request: RetryRunRequest) -> dict:
    await database.ensure_ready()
    async with database.translated_errors():
        async with database.engine.begin() as connection:
            conversation, run = await lock_run(connection, run_id)
            database.require_workspace(run)
            lifecycle = RunLifecycleRepository(connection)
            # Receipt replays do not requeue, reacquire a lease or append events.
            prior = await lifecycle.retry(
                run,
                idempotency_key=request.idempotency_key,
                expected_attempt_count=request.expected_attempt_count,
            )
            if prior:
                return turn_accepted_response(run, replayed=True)
            subject = await MemoryRepository(connection).lock_subject(
                str(conversation["memory_subject_id"])
            )
            if (
                conversation["archived_at"]
                or subject["archived_at"]
                or int(conversation["version"])
                != int(run["accepted_conversation_version"])
            ):
                raise RuntimeConflict(
                    "Saved reply is no longer compatible with the conversation"
                )
            messages = await ConversationRepository(connection).list_messages(
                str(conversation["id"])
            )
            if len(
                [
                    row
                    for row in messages
                    if str(row.get("run_id")) == run_id and row["role"] == "user"
                ]
            ) != 1 or any(
                row["role"] == "assistant" and str(row.get("run_id")) == run_id
                for row in messages
            ):
                raise RuntimeConflict(
                    "Saved reply no longer has one unanswered immutable input"
                )
            await ConversationLeaseRepository(connection).create_pending(
                lease_id=str(uuid4()),
                conversation_id=str(conversation["id"]),
                run_id=run_id,
                lease_token=str(uuid4()),
            )
            await append_run_event(
                RunRepository(connection),
                run_id=run_id,
                event_type="run.retry_requested",
                payload={"expected_attempt_count": request.expected_attempt_count},
            )
            current = await RunRepository(connection).get(run_id)
    return turn_accepted_response(current, replayed=False)
