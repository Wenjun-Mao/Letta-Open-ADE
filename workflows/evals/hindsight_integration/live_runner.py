"""Approved Stage 1 six-slot product demonstration, not a quality-acceptance runner."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import time

import httpx

from .casebook import load_suite
from .live_bindings import preflight, wire_records
from .operations import Lease
from .product_slot import run_product_slot, safe_failure
from .public_http import PublicRecordingTransport
from .records import seal, write_new
from .report import write_report
from .reviews import review_template
from .runs import prepare_run, start_attempt
from .startup import require_supervision


CASES = ("q01-relevant", "q02-correction", "q02-change")


def require_admission(activation_root, lease, seconds):
    if (
        activation_root / "closed.json"
    ).exists() or time.time() + seconds >= lease.dispatch_deadline:
        raise ValueError("Product work will not fit the unclosed activation window")
    require_supervision(activation_root, lease, now=time.time())


async def run_live(
    root: Path, *, activation_root: Path, run_id: str, slot_timeout=1200
):
    if (
        not re.fullmatch(r"[a-z][a-z0-9-]{0,79}", run_id)
        or not 600 <= slot_timeout <= 1800
    ):
        raise ValueError("Use the bounded approved six-slot demonstration contract")
    lease = Lease.load(activation_root)
    revision = os.environ["ADE_INTEGRATION_SOURCE_REVISION"]
    fingerprint = os.environ["ADE_INTEGRATION_SOURCE_FINGERPRINT"]
    if revision != lease.source_revision or not re.fullmatch(
        r"[a-f0-9]{64}", fingerprint
    ):
        raise ValueError("Product runner does not match the activation source")
    urls = {
        "api": os.environ["ADE_INTEGRATION_API_URL"],
        "router": os.environ["ADE_INTEGRATION_ROUTER_URL"],
        "native": os.environ["ADE_INTEGRATION_HINDSIGHT_URL"],
    }
    if urls != {
        "api": "http://ade-api:8000",
        "router": "http://model-router:8010",
        "native": "http://hindsight:8888",
    }:
        raise ValueError("Use only the isolated candidate's internal service endpoints")
    require_admission(activation_root, lease, slot_timeout * 6 + 240)
    source = {
        "source_revision": revision,
        "source_fingerprint": fingerprint,
        "source_dirty": "false",
        "activation_id": lease.activation_id,
    }
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    write_new(
        root / "invocation.json",
        {
            "source": source,
            "cases": list(CASES),
            "repeats": 2,
            "slot_timeout_seconds": slot_timeout,
            "scope": "approved_stage1_demonstration",
            "character_review": "UNREVIEWED",
        },
    )
    keys = {
        "api": os.environ["ADE_INTEGRATION_API_KEY"],
        "router": os.environ["ADE_INTEGRATION_ROUTER_KEY"],
        "native": os.environ["ADE_INTEGRATION_HINDSIGHT_KEY"],
    }
    prepared = False
    try:
        async with (
            httpx.AsyncClient(
                base_url=urls["api"],
                headers={"Authorization": "Bearer " + keys["api"]},
                transport=PublicRecordingTransport(root / "preflight/api-http"),
                timeout=30,
            ) as api,
            httpx.AsyncClient(
                base_url=urls["router"],
                headers={"Authorization": "Bearer " + keys["router"]},
                transport=PublicRecordingTransport(root / "preflight/router-http"),
                timeout=30,
            ) as router,
            httpx.AsyncClient(
                base_url=urls["native"],
                headers={"Authorization": "Bearer " + keys["native"]},
                transport=PublicRecordingTransport(root / "preflight/native-http"),
                timeout=30,
            ) as native,
        ):
            runtime, environment = await preflight(api, router, native, source=source)
        write_new(
            root / "environment.json",
            seal(
                "product-environment-binding",
                {
                    "source": source,
                    "runtime": runtime.model_dump(mode="json"),
                    "observed": environment,
                },
            ),
        )
        plan = prepare_run(
            root / "run",
            run_id=run_id,
            mode="live_capture",
            runtime=runtime,
            repeats=2,
            case_ids=list(CASES),
            evaluator_revision=revision,
        )
        (root / "run").chmod(0o700)
        prepared = True
        for case in plan.cases:
            for repeat in range(1, plan.repeats + 1):
                require_admission(activation_root, lease, slot_timeout + 30)
                path = start_attempt(root / "run", case.case_id, repeat)
                observation, issues = await run_product_slot(
                    path=path,
                    case=case,
                    repeat=repeat,
                    runtime=runtime,
                    source=source,
                    api_url=urls["api"],
                    api_key=keys["api"],
                    router_url=urls["router"],
                    router_key=keys["router"],
                    timeout=slot_timeout,
                )
                write_new(path / "human-review-template.json", review_template(path))
                print(
                    json.dumps(
                        {
                            "case_id": case.case_id,
                            "repeat": repeat,
                            "execution_status": observation.status,
                            "stage": observation.stage,
                            "mechanical_issues": issues,
                            "character_review": "UNREVIEWED",
                        }
                    ),
                    flush=True,
                )
    except Exception as exc:
        write_new(
            root / "failure.json", {"error": safe_failure(exc), "time": time.time()}
        )
        raise
    finally:
        await capture_traffic(root, urls["router"], keys["router"])
        if prepared:
            report = write_report(root / "run", root / "report")
            print(
                json.dumps(
                    {
                        "reported_slots": len(report["attempts"]),
                        "report": str(root / "report"),
                        "character_review": "UNREVIEWED",
                    }
                ),
                flush=True,
            )
    return report


async def capture_traffic(root, router_url, router_key):
    started = time.time()
    try:
        async with httpx.AsyncClient(
            base_url=router_url,
            headers={"Authorization": "Bearer " + router_key},
            transport=PublicRecordingTransport(root / "traffic/router-http"),
            timeout=30,
        ) as router:
            records = await wire_records(router)
        write_new(
            root / "traffic/snapshot.json",
            seal(
                "product-traffic-snapshot",
                {
                    "started_at": started,
                    "finished_at": time.time(),
                    "records": records,
                    "missing_outcome_request_ids": [
                        row["request"]["request_id"]
                        for row in records
                        if row["outcome"] is None
                    ],
                    "limitation": (
                        "Time-bounded observation of all candidate Router traffic; "
                        "native work may continue. Not a quiescent closeout or billing receipt."
                    ),
                },
            ),
        )
    except Exception as exc:
        write_new(
            root / "traffic/failure.json",
            {"error": safe_failure(exc), "started_at": started, "time": time.time()},
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--activation-root", type=Path, default=Path("/activation"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--slot-timeout", type=int, default=1200)
    args = parser.parse_args()
    load_suite()
    asyncio.run(
        run_live(
            args.out,
            activation_root=args.activation_root,
            run_id=args.run_id,
            slot_timeout=args.slot_timeout,
        )
    )


if __name__ == "__main__":
    main()
