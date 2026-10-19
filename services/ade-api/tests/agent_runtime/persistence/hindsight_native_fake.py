"""Recording native HTTP substitute for real-SQL delivery control tests only."""

import json

from sqlalchemy import select, text

from ade_api.integrations.hindsight import HindsightError
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_deliveries,
    memory_relationships,
)


class NativeDeliveryFake:
    def __init__(self, db):
        self.db = db
        self.configurations = {}
        self.operations = {}
        self.documents = {}
        self.submissions = []
        self.retries = []
        self.creations = []
        self.lose_ack = False
        self.initial_status = "completed"
        self.release_submission = None
        self.submission_started = None
        self.corrupt_document = False
        self.network_checks = 0

    async def outside_transaction(self, bank):
        # A separate connection must be able to lock both ownership and outbox
        # while the would-be HTTP call is executing, not after it finishes.
        async with self.db.begin() as connection:
            await connection.execute(text("SET LOCAL lock_timeout = '100ms'"))
            await connection.execute(
                select(memory_relationships)
                .where(
                    memory_relationships.c.bank_id == bank,
                )
                .with_for_update()
            )
            await connection.execute(
                select(memory_deliveries)
                .where(
                    memory_deliveries.c.bank_id == bank,
                )
                .with_for_update()
            )
        self.network_checks += 1

    async def bank_config(self, bank):
        await self.outside_transaction(bank)
        if bank not in self.configurations:
            raise HindsightError("hindsight_http_error", status_code=404)
        return {"bank_id": bank, "config": self.configurations[bank]}

    async def create_bank(self, bank, **kwargs):
        await self.outside_transaction(bank)
        self.creations.append(bank)
        self.configurations[bank] = {}

    async def configure_bank(self, bank, configuration):
        await self.outside_transaction(bank)
        self.configurations[bank] = configuration

    async def statistics(self, bank):
        await self.outside_transaction(bank)
        return {
            "bank_id": bank,
            "total_nodes": 0,
            "total_documents": 0,
            "pending_operations": 0,
            "failed_operations": 0,
        }

    async def operation(self, bank, operation):
        await self.outside_transaction(bank)
        return {
            "operation_id": operation,
            "status": self.operations.get(operation, "not_found"),
        }

    async def submit(self, bank, *, operation_id, payload):
        await self.outside_transaction(bank)
        self.submissions.append((operation_id, payload))
        self.operations[operation_id] = self.initial_status
        item = json.loads(payload)["items"][0]
        self.documents[item["document_id"]] = {
            "bank_id": bank,
            "id": item["document_id"],
            "original_text": item["content"],
            "retain_params": {"context": item["context"]},
        }
        if self.submission_started is not None:
            self.submission_started.set()
            await self.release_submission.wait()
        if self.lose_ack:
            self.lose_ack = False
            raise HindsightError("hindsight_unavailable")

    async def retry_operation(self, bank, operation):
        await self.outside_transaction(bank)
        self.retries.append(operation)
        self.operations[operation] = "completed"

    async def document(self, bank, document):
        await self.outside_transaction(bank)
        value = self.documents[document]
        return {**value, "original_text": "changed"} if self.corrupt_document else value
