"""Explicitly approved native PC-11 execution; offline prepare remains network-free."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
import os
from pathlib import Path

from .native_artifacts import (
    annotate,
    check_preparation,
    clean_preparation,
    read,
    require_output_directory,
    write_once,
)
from .native_environment import NativeEnvironment, remove_owned_database
from .native_sequence import run_sequence
from .native_transport import NativeADE


async def dispatch(environment: NativeEnvironment) -> dict:
    api = NativeADE(environment.api_url, environment.api_key)
    try:
        return await run_sequence(api, environment.directory, environment.launch)
    finally:
        await api.close()


def start(directory: Path, *, approved: bool) -> None:
    if not approved:
        raise ValueError("Separate explicit live approval is required")
    preparation = clean_preparation()
    directory.mkdir(mode=0o700)
    write_once(directory / "preparation.json", preparation)
    write_once(
        directory / "authorization.json",
        {
            "approved_at": datetime.now(UTC).isoformat(),
            "scope": "One frozen PC-11 native sequence, at most ten target turns, one attempt each; no rerolls or baseline edits",
            "approval": "User explicitly approved the bounded live probe and its isolated runner preparation in this chat",
            "source_revision": preparation["source_revision"],
            "fixture_sha256": preparation["fixture_sha256"],
            "roles": preparation["isolated_baseline"]["roles"],
            "request_envelope": {
                "target_turn_ceiling": 10,
                "attempts_per_turn": 1,
                "retry_count": 0,
                "timeout_seconds": 180,
                "runtime_conversation_requests_per_turn": 2,
                "runtime_reviewer_requests_per_turn": 1,
                "context_window_per_role": 16384,
                "max_output_tokens_per_role": 4096,
                "provider_requests": "Observed, not a spending gate; unchanged finite runtime tool loop, native retrieval embeddings and reviewer",
            },
            "human_annotation_frontiers": [1, 3],
            "retained_trial_access": False,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["start", "resume", "annotate", "cleanup"])
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--turn", type=int, choices=[1, 3])
    parser.add_argument("--annotation", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    directory = require_output_directory(args.directory)
    if args.command == "cleanup":
        remove_owned_database(directory)
        print(json.dumps({"status": "owned_database_removed"}))
        return
    if args.command == "annotate":
        if args.turn is None or args.annotation is None:
            parser.error("annotate requires --turn and --annotation")
        check_preparation(directory)
        result = annotate(directory, args.turn, read(args.annotation))
        print(
            json.dumps(
                {"status": "human_annotation_frozen", "usable": result["usable"]}
            )
        )
        return
    if args.command == "start":
        start(directory, approved=args.approved)
    check_preparation(directory)
    authorization = read(directory / "authorization.json")
    preparation = read(directory / "preparation.json")
    if (
        authorization["source_revision"] != preparation["source_revision"]
        or authorization["fixture_sha256"] != preparation["fixture_sha256"]
    ):
        raise ValueError("Authorization does not bind this source/schedule")
    with NativeEnvironment(directory) as environment:
        result = asyncio.run(dispatch(environment))
        write_once(environment.launch / "result.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
