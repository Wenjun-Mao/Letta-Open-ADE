"""Fixed six-stage D04 sequence with fail-closed interrupted-dispatch semantics."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import traceback
import copy
from pathlib import Path

from .contracts import digest, load_prepared, review_request, route_receipt
from .evidence import (
    STAGES,
    classify,
    response_object,
    status,
    validate_receipts,
    visible,
)
from .evidence import audit as audit
from .receipts import now, read, require_private, source_receipt, write_once
from .transport import Router


async def run(directory: Path, router, configuration: dict, *, source=source_receipt):
    directory = require_private(directory)
    prepared = load_prepared()
    origin = source()
    if configuration != {
        "source_head": origin["head"],
        "isolated_loopback": True,
        "router_request_timeout_seconds": 180,
        "transport_retries": 0,
        "configuration_sha256": prepared["configuration_sha256"],
    }:
        raise ValueError("Isolated router configuration attestation mismatch")
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / "stop.json").exists():
        raise ValueError("Recorded preflight/capacity stop; no continuation")
    freeze = {"source": origin, "configuration": configuration}
    if (directory / "freeze.json").exists():
        if read(directory / "freeze.json") != freeze:
            raise ValueError("Source/configuration drift since launch")
    else:
        write_once(directory / "freeze.json", freeze)
    for intent in directory.glob("preflight-*.intent.json"):
        if not intent.with_name(intent.name.replace(".intent.", ".outcome.")).exists():
            raise ValueError("Interrupted preflight capture; refuse continuation")
    terminal = validate_receipts(directory, prepared["packets"])
    if terminal:
        raise ValueError(f"Recorded {terminal}; no continuation or resend")
    if all((directory / f"{key}.outcome.json").exists() for key in STAGES):
        return status(directory)
    number = len(list(directory.glob("preflight-*.intent.json"))) + 1
    key = f"preflight-{number:02d}"
    write_once(
        directory / f"{key}.intent.json",
        {"operation": "fresh_catalog", "at": now(), **freeze},
    )
    try:
        raw = await router.catalog()
        write_once(directory / f"{key}.raw.json", raw)
        if not 200 <= raw["status"] < 300:
            raise ValueError("Catalog HTTP/auth failure")
        route = route_receipt(response_object(raw))
    except Exception as exc:
        write_once(
            directory / f"{key}.outcome.json",
            {
                "disposition": "preflight_stop",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        write_once(
            directory / "stop.json",
            {"at": now(), "reason": "catalog_preflight_failure", "stage": key},
        )
        return status(directory)
    write_once(
        directory / f"{key}.outcome.json", {"disposition": "ready", "route": route}
    )
    for packet in prepared["packets"]:
        for stage in ("generation", "reviewer"):
            key = f"{packet['arm']}.{stage}"
            outcome_path = directory / f"{key}.outcome.json"
            if outcome_path.exists():
                continue
            try:
                current_source = source()
            except Exception:
                write_once(
                    directory / "stop.json",
                    {"at": now(), "reason": "source_preflight_failure", "stage": key},
                )
                raise
            if current_source != origin:
                write_once(
                    directory / "stop.json",
                    {"at": now(), "reason": "source_drift", "stage": key},
                )
                raise ValueError("Source drift before dispatch")
            if stage == "generation":
                request = packet["generation"]
            else:
                generation = read(
                    directory / f"{packet['arm']}.generation.outcome.json"
                )
                if generation["classification"]["disposition"] != "captured":
                    write_once(
                        outcome_path,
                        {
                            "classification": {
                                "disposition": "skipped",
                                "reason": "No complete usable visible generation",
                            }
                        },
                    )
                    continue
                try:
                    request = review_request(packet, visible(generation["raw"]))
                except ValueError:
                    # A real reply can exceed the ASCII reserve under UTF-8/JSON
                    # serialization. Capacity failure is a global preflight stop.
                    write_once(
                        directory / "stop.json",
                        {
                            "at": now(),
                            "reason": "actual_reviewer_capacity",
                            "stage": key,
                        },
                    )
                    return status(directory)
            intent = {
                "stage": key,
                "at": now(),
                "source": origin,
                "route": route,
                "request_sha256": digest(request),
                "request": request,
                "deadline_seconds": 180,
                "attempt": 1,
            }
            write_once(directory / f"{key}.intent.json", intent)
            try:
                raw = await router.send(copy.deepcopy(request))
            except Exception as exc:
                write_once(
                    outcome_path,
                    {
                        "intent_sha256": digest(intent),
                        "at": now(),
                        "classification": {
                            "disposition": "transport_stop",
                            "error_type": type(exc).__name__,
                        },
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                )
                return status(directory)
            # Capture before interpretation. Failure here leaves a consumed intent,
            # so restart cannot replay a possibly successful provider request.
            write_once(directory / f"{key}.raw.json", raw)
            classification = classify(raw, stage)
            write_once(
                outcome_path,
                {
                    "intent_sha256": digest(intent),
                    "raw": raw,
                    "at": now(),
                    "classification": classification,
                },
            )
            if classification["disposition"] == "infrastructure_stop":
                return status(directory)
    return status(directory)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--router-url", required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    args = parser.parse_args()
    router = Router(args.router_url, os.environ["D04_ROUTER_TOKEN"])
    try:
        print(json.dumps(await run(args.directory, router, read(args.configuration))))
    finally:
        await router.close()


if __name__ == "__main__":
    asyncio.run(main())
