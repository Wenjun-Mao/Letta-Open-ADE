"""Command-line capture and verification for bounded restart readback."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

from .driver_support import HindsightHTTP
from .receipts import ReceiptStore
from .restart_readback import capture, compare, read_selection
from .restart_selection import sha256_file


async def run(args) -> int:
    selection = read_selection(args.selection)
    if args.command == "verify":
        before, after = json.loads(args.before.read_text()), json.loads(args.after.read_text())
        result = compare(before, after, selection)
        result.update({
            "selection_file_sha256": sha256_file(args.selection),
            "before_file_sha256": sha256_file(args.before),
            "after_file_sha256": sha256_file(args.after),
        })
        ReceiptStore(args.output.parent).write(args.output.name, result)
        return 0
    run_identity = {
        "release_sha": os.environ.get("PROBE_RELEASE_SHA", ""),
        "registry_sha256": os.environ.get("ADE_PROBE_REGISTRY_SHA256", ""),
        "epoch_sha256": os.environ.get("ADE_PROBE_EPOCH_SHA256", ""),
    }
    base_url = os.environ.get("ADE_EVAL_HINDSIGHT_BASE_URL", "")
    api_key = os.environ.get("ADE_EVAL_HINDSIGHT_API_KEY", "")
    async with httpx.AsyncClient() as http:
        snapshot = await capture(selection, HindsightHTTP(http, base_url, api_key), run_identity)
    ReceiptStore(args.output.parent).write(args.output.name, snapshot)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture_parser = sub.add_parser("capture")
    verify_parser = sub.add_parser("verify")
    for selected in (capture_parser, verify_parser):
        selected.add_argument("--selection", type=Path, required=True)
        selected.add_argument("--output", type=Path, required=True)
    verify_parser.add_argument("--before", type=Path, required=True)
    verify_parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except Exception:
        print("restart_readback_failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
