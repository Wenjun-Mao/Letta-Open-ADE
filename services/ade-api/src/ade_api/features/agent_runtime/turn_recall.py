"""Required native recall and discretionary search share one scoped failure contract."""

import asyncio
import time

from ade_api.integrations.hindsight import HindsightClient, HindsightError

from .memory_banks import MemoryBankAccess, MemoryBankError


class MemoryLookupError(RuntimeError):
    error_code = "memory_lookup_failed"

    def __init__(self, detail_code: str):
        super().__init__("Memory lookup failed; retry the saved message")
        self.detail_code = detail_code


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

    async def lookup(
        self, query: str, *, limit: int = 20, phase: str = "automatic"
    ) -> list[dict]:
        if self.trace is not None:
            self.trace.memory_lookup_active = True
        try:
            async with asyncio.timeout(max(0, self.deadline - time.monotonic())):
                await self.banks.ensure_ready(self.bank_id, deadline=self.deadline)
                value = await self.client.recall(
                    self.bank_id,
                    {"query": query, "budget": "mid", "max_tokens": 1800},
                )
        except (HindsightError, MemoryBankError, TimeoutError) as exc:
            raise MemoryLookupError(
                getattr(exc, "code", "memory_lookup_timeout")
            ) from exc
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
            raise MemoryLookupError("hindsight_recall_invalid")
        selected = results[:limit]
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
