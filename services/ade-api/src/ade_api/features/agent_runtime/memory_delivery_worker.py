"""Independent Hindsight delivery scheduling; reply execution never awaits this loop."""

import asyncio
import logging
import time
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ade_api.integrations.hindsight import HindsightClient, HindsightError

from .memory_banks import MemoryBankAccess, MemoryBankError
from .persistence.base import LeaseUnavailableError
from .persistence.memory_deliveries import MemoryDeliveryRepository, verified_delivery


logger = logging.getLogger(__name__)


def native_progress(value: dict) -> dict:
    return {
        key: value[key]
        for key in ("status", "progress", "child_operations")
        if key in value
    }


class MemoryDeliveryWorker:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        client: HindsightClient,
        workspace_id: str,
        lease_seconds=60,
        poll_seconds=0.5,
        concurrency=2,
    ):
        self.engine = engine
        self.client = client
        self.workspace_id = workspace_id
        self.lease_seconds = lease_seconds
        self.poll_seconds = poll_seconds
        self.concurrency = concurrency
        self.banks = MemoryBankAccess(
            engine=engine, client=client, workspace_id=workspace_id
        )

    async def process_once(self) -> bool:
        token = str(uuid4())
        async with self.engine.begin() as connection:
            row = await MemoryDeliveryRepository(connection).claim(
                workspace_id=self.workspace_id,
                token=token,
                lease_seconds=self.lease_seconds,
            )
        if row is None:
            return False
        stop = asyncio.Event()
        operation = str(row["operation_id"])
        task = asyncio.create_task(self._perform(row, token))
        heartbeat = asyncio.create_task(self._heartbeat(operation, token, stop))
        try:
            done, _ = await asyncio.wait(
                {task, heartbeat}, return_when=asyncio.FIRST_COMPLETED
            )
            if heartbeat in done:
                await heartbeat
                raise LeaseUnavailableError("Memory delivery heartbeat stopped")
            await task
        except LeaseUnavailableError:
            pass
        except Exception as exc:
            permanent = isinstance(exc, MemoryBankError) and not exc.retryable
            code = "memory_delivery_internal_error"
            if isinstance(exc, HindsightError):
                code = exc.code
                permanent = exc.code not in {
                    "hindsight_unavailable",
                    "hindsight_http_error",
                } or (exc.status_code in {400, 401, 403, 404, 422})
            elif isinstance(exc, MemoryBankError):
                code = exc.code
            elif isinstance(exc, TimeoutError):
                code = "memory_delivery_timeout"
            elif isinstance(exc, IntegrityError):
                code, permanent = "memory_delivery_persistence_contract_error", True
            elif isinstance(exc, SQLAlchemyError):
                code, permanent = "memory_delivery_database_error", False
            else:
                permanent = True
            try:
                async with self.engine.begin() as connection:
                    await MemoryDeliveryRepository(connection).record_error(
                        operation, token, error_code=code, permanent=permanent
                    )
            except LeaseUnavailableError:
                return True
            logger.warning(
                "Memory delivery check failed: %s (%s)", code, type(exc).__name__
            )
        finally:
            stop.set()
            for current in (task, heartbeat):
                if not current.done():
                    current.cancel()
            await asyncio.gather(task, heartbeat, return_exceptions=True)
        return True

    async def _perform(self, row, token):
        delivery = verified_delivery(row)
        operation, bank = delivery.operation_id, delivery.bank_id
        await self.banks.ensure_ready(bank, deadline=time.monotonic() + 180)
        value = await self.client.operation(bank, operation)
        state = value["status"]
        if state == "not_found":
            await self._start_dispatch(operation, token)
            await self.client.submit(
                bank, operation_id=operation, payload=delivery.payload
            )
            await self._record(
                operation,
                token,
                status="processing",
                native_status="pending",
                progress={"status": "pending"},
                acknowledgement="response",
            )
        elif state in {"failed", "cancelled"} and row["retry_requested"]:
            await self._start_dispatch(operation, token)
            await self.client.retry_operation(bank, operation)
            await self._record(
                operation,
                token,
                status="processing",
                native_status="pending",
                progress={"status": "pending"},
                acknowledgement="reconciliation",
            )
        elif state == "completed":
            document = await self.client.document(bank, delivery.document_id)
            item = delivery.verify()["items"][0]
            if (
                document.get("original_text") != item["content"]
                or (document.get("retain_params") or {}).get("context")
                != item["context"]
            ):
                raise MemoryBankError("memory_document_source_changed")
            await self._record(
                operation,
                token,
                status="retained",
                native_status=state,
                progress=native_progress(value),
                acknowledgement="reconciliation",
            )
        else:
            await self._record(
                operation,
                token,
                status="failed" if state in {"failed", "cancelled"} else "processing",
                native_status=state,
                progress=native_progress(value),
                acknowledgement="reconciliation",
            )

    async def _start_dispatch(self, operation, token):
        async with self.engine.begin() as connection:
            await MemoryDeliveryRepository(connection).start_dispatch(operation, token)

    async def _record(self, operation, token, **values):
        async with self.engine.begin() as connection:
            await MemoryDeliveryRepository(connection).record_native(
                operation, token, **values
            )

    async def _heartbeat(self, operation, token, stop):
        while not stop.is_set():
            try:
                await asyncio.wait_for(
                    stop.wait(), timeout=max(1, self.lease_seconds / 3)
                )
            except TimeoutError:
                async with self.engine.begin() as connection:
                    owned = await MemoryDeliveryRepository(connection).heartbeat(
                        operation, token, lease_seconds=self.lease_seconds
                    )
                if not owned:
                    raise LeaseUnavailableError("Memory delivery lease was lost")

    async def run_forever(self, stop: asyncio.Event) -> None:
        async def consume():
            while not stop.is_set():
                try:
                    worked = await self.process_once()
                except Exception as exc:
                    logger.warning(
                        "Memory delivery scheduler unavailable (%s)", type(exc).__name__
                    )
                    worked = False
                if not worked:
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=self.poll_seconds)
                    except TimeoutError:
                        pass

        async with asyncio.TaskGroup() as group:
            for _ in range(self.concurrency):
                group.create_task(consume())
