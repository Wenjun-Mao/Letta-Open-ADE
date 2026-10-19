"""Runner half of real native failure recovery; the host owns Router interruption."""

import argparse
import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import time

import httpx

from ade_api.integrations.hindsight import HindsightClient
from ade_api.integrations.hindsight_bank import bank_configuration
from ade_api.integrations.hindsight_sources import prepare_memory_delivery

from .native_cases import freeze_native_case
from .native_checks import has_processing_work, require_document_source
from .native_gate import memories, operation_done, require_admission
from .native_transport import NativeRecordingTransport
from .operations import Lease
from .records import write_new


def recovery_source(partial: bool):
    plan, sources = freeze_native_case("q01-relevant")
    source = sources[0]
    if partial:
        # Enough independent chunks for a real committed-prefix interruption.
        lines = [
            f"记录 {index}: 我的第 {index} 个收纳盒是蓝色，标签编号为 AX-{index:03d}，"
            "放在自己的工作间。我每周整理一次，盒子只用于保存自己的纸质笔记。"
            for index in range(1, 41)
        ]
        source = replace(source, content="\n".join(lines))
    return plan, source


async def wait_file(path: Path, *, deadline: float):
    while time.monotonic() < deadline:
        if path.is_file():
            return json.loads(path.read_bytes())
        await asyncio.sleep(0.2)
    raise TimeoutError("Native fault host did not restore the owned Router")


async def run_recovery(root: Path, *, partial: bool, timeout: int):
    lease = Lease.load(Path("/activation"))
    if os.environ["ADE_INTEGRATION_SOURCE_REVISION"] != lease.source_revision:
        raise ValueError("Recovery source does not match activation")
    require_admission(lease, operation_seconds=timeout)
    plan, source = recovery_source(partial)
    delivery = prepare_memory_delivery(source)
    configuration = bank_configuration()
    configuration.update({"enable_auto_consolidation": False})
    if partial:
        configuration.update(
            {
                "retain_chunk_size": 250,
                "retain_structured_chunk_size": 250,
                "retain_chunk_batch_size": 1,
            }
        )
    write_new(
        root / "plan.json",
        {
            "case_id": "native_partial_recovery"
            if partial
            else "native_failed_recovery",
            "mode": "native_feasibility",
            "synthetic": True,
            "source_revision": lease.source_revision,
            "activation_id": lease.activation_id,
            "relationship": plan["relationship"],
            "source": source.as_dict(),
            "payload": delivery.verify(),
            "payload_sha256": delivery.payload_sha256,
            "bank_id": delivery.bank_id,
            "operation_id": delivery.operation_id,
            "configuration": configuration,
            "diagnostic_divergence": "Automatic consolidation disabled to isolate retention recovery; small streaming chunks only in the partial-failure bank.",
        },
    )
    result = {"mechanical_status": "failed", "semantic_review": "not_assessed"}
    transport = NativeRecordingTransport(root / "http")
    deadline = time.monotonic() + timeout
    try:
        async with httpx.AsyncClient(transport=transport) as http:
            client = HindsightClient(
                base_url=os.environ["ADE_INTEGRATION_HINDSIGHT_URL"],
                api_key=os.environ["ADE_INTEGRATION_HINDSIGHT_KEY"],
                client=http,
            )
            bank = delivery.bank_id
            await client.create_bank(bank, name="Native interruption and retry")
            await client.configure_bank(bank, configuration)
            if await memories(client, bank):
                raise ValueError("Recovery fixture bank was not empty")
            await client.submit(
                bank, operation_id=delivery.operation_id, payload=delivery.payload
            )
            signalled = False
            while time.monotonic() < deadline:
                state = await client.operation(bank, delivery.operation_id)
                current = await memories(client, bank)
                if partial and current and not signalled and has_processing_work(state):
                    write_new(
                        root / "fault-ready.json",
                        {
                            "operation_id": delivery.operation_id,
                            "bank_id": bank,
                            "partial_memory_ids": [item["id"] for item in current],
                            "state": state,
                        },
                    )
                    signalled = True
                if state["status"] == "failed":
                    break
                if state["status"] not in {"pending", "processing"}:
                    raise ValueError("No genuine failed native operation was observed")
                await asyncio.sleep(0.15 if partial else 1)
            else:
                raise TimeoutError("Injected native failure did not become terminal")
            before = await memories(client, bank)
            if partial != bool(before):
                raise ValueError(
                    "Fault did not produce the required empty/partial state"
                )
            before_operations = await client.operations(bank)
            write_new(
                root / "fault-observed.json",
                {
                    "operation": state,
                    "memories": before,
                    "operations": before_operations,
                },
            )
            resumed = await wait_file(root / "router-restored.json", deadline=deadline)
            if resumed.get("activation_id") != lease.activation_id:
                raise ValueError("Restored Router belongs to another activation")
            await client.retry_operation(bank, delivery.operation_id)
            await operation_done(
                client,
                bank,
                delivery.operation_id,
                timeout=max(1, deadline - time.monotonic()),
            )
            after = await memories(client, bank)
            after_operations = await client.operations(bank)
            document = await client.document(bank, delivery.document_id)
            require_document_source(document, delivery.verify()["items"][0])
            before_ids = {item["id"] for item in before}
            after_ids = {item["id"] for item in after}
            if not after_ids or not before_ids <= after_ids:
                raise ValueError("Retry lost already committed native memories")
            if partial and not after_ids - before_ids:
                raise ValueError("Partial retry did not complete missing extraction")
            identities = lambda page: {item["id"] for item in page["operations"]}
            if identities(before_operations) != identities(after_operations):
                raise ValueError("Retry minted replacement native operation identities")
            write_new(
                root / "recovered.json",
                {
                    "memories": after,
                    "document": document,
                    "operations": after_operations,
                },
            )
            result.update(
                {
                    "mechanical_status": "passed",
                    "bank_id": bank,
                    "operation_id": delivery.operation_id,
                    "partial_memories_preserved": len(before_ids),
                    "completed_memories": len(after_ids),
                    "same_operation_retried": True,
                }
            )
    except Exception as exc:
        result.update({"error_type": type(exc).__name__, "error": str(exc)})
    write_new(root / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    result = asyncio.run(
        run_recovery(args.out, partial=args.partial, timeout=args.timeout)
    )
    print(json.dumps(result))
    return int(result["mechanical_status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
