"""Native source/replay feasibility, with original HTTP evidence and no Character call."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import time

import httpx

from ade_api.integrations.hindsight import HindsightClient, HindsightError
from ade_api.integrations.hindsight_bank import (
    bank_configuration,
    bank_configuration_sha256,
)
from ade_api.integrations.hindsight_sources import prepare_memory_delivery

from .native_cases import freeze_native_case
from .native_checks import require_document_source, require_full_chinese_reranking
from .native_transport import NativeRecordingTransport
from .operations import Lease
from .records import write_new


async def operation_done(client, bank_id, operation_id, *, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = await client.operation(bank_id, operation_id)
        status = value["status"]
        if status == "completed":
            return value
        if status not in {"pending", "processing"}:
            raise ValueError(f"native_operation_{status}")
        await asyncio.sleep(2)
    raise TimeoutError("Native retention did not finish within its admitted deadline")


async def consolidated(client, bank_id, *, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        page = await client.operations(bank_id, kind="consolidation")
        if page["total"] > len(page["operations"]):
            raise ValueError("Native consolidation operation page is incomplete")
        operations = page["operations"]
        if any(item["status"] in {"failed", "cancelled"} for item in operations):
            raise ValueError("native_automatic_consolidation_failed")
        if operations and all(item["status"] == "completed" for item in operations):
            return operations
        await asyncio.sleep(2)
    raise TimeoutError("Native automatic consolidation did not finish")


async def memories(client, bank_id):
    items, offset = [], 0
    while True:
        page = await client.memories(bank_id, offset=offset)
        items.extend(page["items"])
        offset += len(page["items"])
        if offset >= page["total"]:
            return items
        if not page["items"]:
            raise ValueError("Native memory pagination ended before total")


def require_admission(lease, *, operation_seconds):
    if time.time() + operation_seconds >= lease.dispatch_deadline:
        raise ValueError("Native operation will not fit the activation window")


async def run_native_case(case_id, root, *, activation_root, timeout, lose_ack):
    if root.exists():
        raise ValueError("A native attempt needs a new evidence directory")
    lease = Lease.load(activation_root)
    revision = os.environ["ADE_INTEGRATION_SOURCE_REVISION"]
    if revision != lease.source_revision:
        raise ValueError("Native runner source does not match activation")
    plan, sources = freeze_native_case(case_id)
    deliveries = [
        prepare_memory_delivery(source, earlier_messages=tuple(sources[:index]))
        for index, source in enumerate(sources)
    ]
    write_new(
        root / "plan.json",
        {
            **plan,
            "mode": "native_feasibility",
            "synthetic": True,
            "source_revision": revision,
            "activation_id": lease.activation_id,
            "memory_config_sha256": bank_configuration_sha256(),
            "deliveries": [
                {
                    "bank_id": delivery.bank_id,
                    "operation_id": delivery.operation_id,
                    "payload_sha256": delivery.payload_sha256,
                    "payload": delivery.verify(),
                }
                for delivery in deliveries
            ],
        },
    )
    transport = NativeRecordingTransport(root / "http", lose_first_ack=lose_ack)
    result = {
        "case_id": case_id,
        "mechanical_status": "failed",
        "semantic_review": "pending",
    }
    try:
        async with httpx.AsyncClient(transport=transport) as http:
            client = HindsightClient(
                base_url=os.environ["ADE_INTEGRATION_HINDSIGHT_URL"],
                api_key=os.environ["ADE_INTEGRATION_HINDSIGHT_KEY"],
                client=http,
            )
            bank_id = deliveries[0].bank_id
            await client.create_bank(
                bank_id, name="Lin Xiaotang / native source feasibility"
            )
            await client.configure_bank(bank_id, bank_configuration())
            observed_config = (await client.bank_config(bank_id))["config"]
            if any(
                observed_config.get(key) != value
                for key, value in bank_configuration().items()
            ):
                raise ValueError(
                    "Native bank configuration does not match frozen Memory configuration"
                )
            query = {
                "query": plan["actor"]["prompt"],
                "budget": "mid",
                "max_tokens": 2048,
                "types": ["world", "experience", "observation"],
                "trace": True,
                "prefer_observations": False,
                "include": {"entities": None, "chunks": None, "source_facts": None},
            }
            require_admission(lease, operation_seconds=timeout)
            empty = await client.recall(bank_id, query)
            if empty["results"]:
                raise ValueError("New native relationship bank was not empty")
            documents = []
            for delivery in deliveries:
                require_admission(lease, operation_seconds=timeout)
                try:
                    await client.submit(
                        bank_id,
                        operation_id=delivery.operation_id,
                        payload=delivery.payload,
                    )
                except HindsightError as exc:
                    if (
                        exc.code != "hindsight_unavailable"
                        or transport.lost_operation_id != delivery.operation_id
                    ):
                        raise
                    # The injected acknowledgement was lost after real server acceptance.
                    state = await client.operation(bank_id, delivery.operation_id)
                    if state["status"] == "not_found":
                        raise ValueError(
                            "Accepted native operation could not be reconciled"
                        )
                await operation_done(
                    client, bank_id, delivery.operation_id, timeout=timeout
                )
                document = await client.document(bank_id, delivery.document_id)
                require_document_source(document, delivery.verify()["items"][0])
                documents.append(document)
            maintenance = await consolidated(client, bank_id, timeout=timeout)
            before = await memories(client, bank_id)
            before_operations = await client.operations(bank_id)
            replay = deliveries[-1]
            await client.submit(
                bank_id, operation_id=replay.operation_id, payload=replay.payload
            )
            after = await memories(client, bank_id)
            after_operations = await client.operations(bank_id)
            if {item["id"] for item in before} != {item["id"] for item in after}:
                raise ValueError(
                    "Immutable operation replay changed learned-memory identities"
                )
            if before_operations["total"] != after_operations["total"]:
                raise ValueError("Immutable replay created another native operation")
            require_admission(lease, operation_seconds=120)
            recall = await client.recall(bank_id, query)
            reranked = require_full_chinese_reranking(recall)
            write_new(
                root / "memory-readback.json", {"items": after, "documents": documents}
            )
            write_new(root / "recall.json", recall)
            result.update(
                {
                    "mechanical_status": "passed",
                    "retained_sources": len(deliveries),
                    "automatic_consolidation_operations": len(maintenance),
                    "replayed_same_operation": True,
                    "lost_ack_reconciled": transport.ack_lost,
                    "reranked_candidates": reranked,
                    "recall_result_count": len(recall["results"]),
                    "bank_id": bank_id,
                }
            )
    except Exception as exc:
        result.update({"error_type": type(exc).__name__, "error": str(exc)})
    finally:
        write_new(root / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--activation-root", type=Path, default=Path("/activation"))
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--lose-first-ack", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(
        run_native_case(
            args.case,
            args.out,
            activation_root=args.activation_root,
            timeout=args.timeout,
            lose_ack=args.lose_first_ack,
        )
    )
    print(json.dumps(result, ensure_ascii=False))
    return int(result["mechanical_status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
