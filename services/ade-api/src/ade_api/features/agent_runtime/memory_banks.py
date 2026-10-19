"""Concrete native-bank availability without holding SQL locks during HTTP."""

import asyncio
from contextlib import suppress
import time
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.integrations.hindsight import HindsightClient, HindsightError
from ade_api.integrations.hindsight_bank import (
    bank_configuration,
    bank_configuration_sha256,
)

from .persistence.base import LeaseUnavailableError
from .persistence.memory_relationships import MemoryRelationshipRepository


INITIALIZATION_LEASE_SECONDS = 180


class MemoryBankError(RuntimeError):
    def __init__(self, code: str, *, retryable=False):
        super().__init__(code)
        self.code = code
        self.retryable = retryable


def require_native_configuration(value: dict, expected: dict) -> None:
    configuration = value.get("config")
    if not isinstance(configuration, dict) or any(
        configuration.get(key) != item for key, item in expected.items()
    ):
        raise MemoryBankError("memory_bank_configuration_changed")


class MemoryBankAccess:
    def __init__(
        self, *, engine: AsyncEngine, client: HindsightClient, workspace_id: str
    ):
        self.engine = engine
        self.client = client
        self.workspace_id = workspace_id

    async def ensure_ready(self, bank_id: str, *, deadline: float) -> dict:
        while time.monotonic() < deadline:
            async with self.engine.connect() as connection:
                row = await MemoryRelationshipRepository(connection).get(
                    bank_id, workspace_id=self.workspace_id
                )
            if (
                row["configuration_sha256"] != bank_configuration_sha256()
                or row["configuration"] != bank_configuration()
            ):
                raise MemoryBankError("memory_bank_configuration_changed")
            if row["state"] == "ready":
                await self._check_established(row, deadline=deadline)
                return row
            if row["state"] in {"missing", "failed"}:
                raise MemoryBankError(
                    row["last_error_code"] or "memory_bank_unavailable"
                )
            token = str(uuid4())
            async with self.engine.begin() as connection:
                claimed = await MemoryRelationshipRepository(
                    connection
                ).claim_initialization(
                    bank_id,
                    workspace_id=self.workspace_id,
                    token=token,
                    lease_seconds=INITIALIZATION_LEASE_SECONDS,
                )
            if claimed is not None:
                await self._initialize(claimed, token=token, deadline=deadline)
                continue
            await asyncio.sleep(min(0.1, max(0, deadline - time.monotonic())))
        raise MemoryBankError("memory_bank_initialization_timeout", retryable=True)

    async def _check_established(self, row, *, deadline):
        try:
            async with asyncio.timeout(max(0, deadline - time.monotonic())):
                value = await self.client.bank_config(row["bank_id"])
                require_native_configuration(value, row["configuration"])
        except HindsightError as exc:
            if exc.status_code == 404:
                async with self.engine.begin() as connection:
                    await MemoryRelationshipRepository(connection).mark_missing(
                        row["bank_id"], workspace_id=self.workspace_id
                    )
                raise MemoryBankError("established_memory_bank_missing") from exc
            raise
        except MemoryBankError:
            async with self.engine.begin() as connection:
                await MemoryRelationshipRepository(
                    connection
                ).mark_configuration_changed(
                    row["bank_id"], workspace_id=self.workspace_id
                )
            raise

    async def _initialize(self, row, *, token, deadline):
        finished = False
        reset_state, error = "new", None
        bank_id = row["bank_id"]
        try:
            async with asyncio.timeout(max(0, deadline - time.monotonic())):
                try:
                    await self.client.bank_config(bank_id)
                except HindsightError as exc:
                    if exc.status_code != 404:
                        raise
                    await self.client.create_bank(
                        bank_id, name="ADE character-local memory"
                    )
                # An interrupted empty-bank creation may be reconciled. Populated
                # unestablished state must never be adopted as a fresh relationship.
                statistics = await self.client.statistics(bank_id)
                if any(
                    statistics.get(key) != 0
                    for key in (
                        "total_nodes",
                        "total_documents",
                        "pending_operations",
                        "failed_operations",
                    )
                ):
                    raise MemoryBankError("unestablished_memory_bank_not_empty")
                await self.client.configure_bank(bank_id, row["configuration"])
                require_native_configuration(
                    await self.client.bank_config(bank_id), row["configuration"]
                )
            async with self.engine.begin() as connection:
                await MemoryRelationshipRepository(connection).finish_initialization(
                    bank_id,
                    workspace_id=self.workspace_id,
                    token=token,
                    state="ready",
                )
            finished = True
        except MemoryBankError as exc:
            reset_state, error = "failed", exc.code
            raise
        finally:
            if not finished:
                with suppress(LeaseUnavailableError):
                    async with self.engine.begin() as connection:
                        await MemoryRelationshipRepository(
                            connection
                        ).finish_initialization(
                            bank_id,
                            workspace_id=self.workspace_id,
                            token=token,
                            state=reset_state,
                            error=error or "memory_bank_initialization_interrupted",
                        )
