"""Prepare, inspect or stop only a registered integration activation."""

import argparse
from pathlib import Path
import time

from .operations import (
    DockerOperations,
    Lease,
    MAX_LEASE_SECONDS,
    check_lease,
    encoded,
    prepare_lease,
    resources,
    stop_owned,
    supervise,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["prepare", "check", "supervise", "start", "start-product", "stop"],
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--project", default="ade-hindsight-integration")
    parser.add_argument("--revision")
    parser.add_argument("--environment", type=Path)
    parser.add_argument("--disk-path", default="/mnt/projects")
    parser.add_argument("--duration", type=int, default=MAX_LEASE_SECONDS)
    args = parser.parse_args()
    docker = DockerOperations()
    if args.action == "prepare":
        if not args.revision:
            parser.error("--revision is required for prepare")
        lease = prepare_lease(
            args.root,
            docker=docker,
            project=args.project,
            source_revision=args.revision,
            disk_path=args.disk_path,
            duration=args.duration,
        )
        print(
            encoded(
                {
                    "activation_id": lease.activation_id,
                    "dispatch_deadline": lease.dispatch_deadline,
                    "expires_at": lease.expires_at,
                    "prepared_at": int(time.time()),
                }
            ).decode()
        )
        return 0
    if args.action == "supervise":
        return supervise(args.root)
    if args.action in {"start", "start-product"}:
        from .startup import start_native, start_product

        if args.environment is None:
            parser.error("--environment is required for start")
        start = start_product if args.action == "start-product" else start_native
        start(args.root, args.environment)
        return 0
    lease = Lease.load(args.root)
    if args.action == "check":
        issues = check_lease(
            lease,
            docker=docker,
            capacity=resources(lease.disk_path),
            closed=(args.root / "closed.json").exists(),
        )
        print(
            encoded({"issues": issues, "activation_id": lease.activation_id}).decode()
        )
        return int(bool(issues))
    result = stop_owned(
        lease, docker=docker, root=args.root, reason="operator_closeout"
    )
    print(encoded(result).decode())
    return int(bool(result["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
