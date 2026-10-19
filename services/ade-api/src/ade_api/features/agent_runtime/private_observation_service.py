"""Operator-only export, scoped to the configured product workspace and real run."""

from sqlalchemy import select

from .errors import RuntimeNotFound, RuntimeNotReady
from .persistence.metadata import messages, run_attempts
from .persistence.runs import RunRepository
from .private_observations import capture_root, read_attempts


class PrivateObservationService:
    def __init__(self, *, database, settings):
        self.database = database
        self.settings = settings

    async def read(self, run_id: str) -> dict:
        try:
            root = capture_root(self.settings)
        except ValueError as exc:
            raise RuntimeNotReady("Private capture configuration is invalid") from exc
        if root is None:
            raise RuntimeNotFound("Private capture is disabled")
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                run = await RunRepository(connection).get(run_id)
                self.database.require_workspace(run)
                attempts = (
                    (
                        await connection.execute(
                            select(
                                run_attempts.c.id,
                                run_attempts.c.attempt_number,
                                run_attempts.c.status,
                            )
                            .where(run_attempts.c.run_id == run_id)
                            .order_by(run_attempts.c.attempt_number)
                        )
                    )
                    .mappings()
                    .all()
                )
                committed = (
                    (
                        await connection.execute(
                            select(messages.c.id).where(
                                messages.c.run_id == run_id,
                                messages.c.role == "assistant",
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
        try:
            observations = read_attempts(root, run_id, self.database.workspace_id)
            saved_ids = {str(row["id"]) for row in attempts}
            if any(item["attempt_id"] not in saved_ids for item in observations):
                raise ValueError("Capture refers to an unsaved attempt")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise RuntimeNotReady("Private capture is incomplete or invalid") from exc
        return {
            "schema_version": 1,
            "run_id": run_id,
            "workspace_id": self.database.workspace_id,
            "run_status": run["status"],
            "saved_attempts": [
                {
                    "id": str(row["id"]),
                    "attempt_number": row["attempt_number"],
                    "status": row["status"],
                }
                for row in attempts
            ],
            "committed_assistant_message_ids": [str(value) for value in committed],
            "observations": observations,
        }
