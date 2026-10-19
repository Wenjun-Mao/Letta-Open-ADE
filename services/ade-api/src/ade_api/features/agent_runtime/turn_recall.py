"""Required native recall and discretionary search share one scoped failure contract."""

import asyncio
import time

from sqlalchemy.exc import (
    DBAPIError,
    DisconnectionError,
    InterfaceError,
    OperationalError,
    TimeoutError as PoolTimeoutError,
)

from ade_api.integrations.hindsight import HindsightClient, HindsightError

from .memory_banks import MemoryBankAccess, MemoryBankError


LOOKUP_OBSERVATION_CONTRACT = "ade-memory-lookup-v2"


class MemoryLookupError(RuntimeError):
    error_code = "memory_lookup_failed"

    def __init__(self, detail_code: str):
        super().__init__("Memory lookup failed; retry the saved message")
        self.detail_code = detail_code


def lookup_failure_code(exc: Exception) -> str | None:
    if isinstance(
        exc,
        (
            OperationalError,
            InterfaceError,
            DisconnectionError,
            PoolTimeoutError,
            ConnectionError,
        ),
    ) or (isinstance(exc, DBAPIError) and exc.connection_invalidated):
        return "memory_lookup_database_unavailable"
    if isinstance(exc, (HindsightError, MemoryBankError)):
        return exc.code
    if isinstance(exc, TimeoutError):
        return "memory_lookup_timeout"
    return None


class TurnRecall:
    def __init__(
        self,
        *,
        banks: MemoryBankAccess,
        client: HindsightClient,
        bank_id: str,
        deadline: float,
        trace=None,
    ):
        self.banks = banks
        self.client = client
        self.bank_id = bank_id
        self.deadline = deadline
        self.trace = trace
        self.observations: list[dict] = []
        self._lookup_number = 0

    async def lookup(
        self, query: str, *, limit: int = 20, phase: str = "automatic"
    ) -> list[dict]:
        self._lookup_number += 1
        identity = {
            "lookup_contract": LOOKUP_OBSERVATION_CONTRACT,
            "lookup_number": self._lookup_number,
            "phase": phase,
            "bank_id": self.bank_id,
            "query": query,
            "limit": limit,
        }
        if self.trace is not None:
            self.trace.memory_lookup_active = True
            self.trace.record_private("memory_lookup.started", identity)
        try:
            async with asyncio.timeout(max(0, self.deadline - time.monotonic())):
                await self.banks.ensure_ready(self.bank_id, deadline=self.deadline)
                payload = {"query": query, "budget": "mid", "max_tokens": 1800}
                if self.trace is not None and self.trace.private_observer is not None:
                    payload["trace"] = True
                value = await self.client.recall(
                    self.bank_id,
                    payload,
                )
        except (
            HindsightError,
            MemoryBankError,
            TimeoutError,
            DBAPIError,
            DisconnectionError,
            PoolTimeoutError,
            ConnectionError,
        ) as exc:
            detail_code = lookup_failure_code(exc)
            if detail_code is None:
                raise
            if self.trace is not None:
                self.trace.record_private(
                    "memory_lookup.failed",
                    {
                        **identity,
                        "error_code": detail_code,
                    },
                )
            raise MemoryLookupError(detail_code) from exc
        finally:
            if self.trace is not None:
                self.trace.memory_lookup_active = False
        results = value.get("results")
        if not isinstance(results, list) or any(
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("text"), str)
            for item in results
        ):
            if self.trace is not None:
                self.trace.record_private(
                    "memory_lookup.failed",
                    {
                        **identity,
                        "error_code": "hindsight_recall_invalid",
                    },
                )
            raise MemoryLookupError("hindsight_recall_invalid")
        selected = results[:limit]
        if self.trace is not None:
            self.trace.record_private(
                "memory_lookup.completed",
                {
                    **identity,
                    "response": value,
                    "selected_ids": [item["id"] for item in selected],
                },
            )
        self.observations.append(
            {
                "phase": phase,
                "bank_id": self.bank_id,
                "result_ids": [item["id"] for item in selected],
            }
        )
        return selected

    async def search(self, query: str, limit: int) -> list[dict]:
        return await self.lookup(query, limit=limit, phase="tool")
