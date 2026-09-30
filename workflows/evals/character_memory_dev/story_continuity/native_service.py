"""Launch existing public service entrypoints with an isolated host alias."""

from __future__ import annotations

import argparse
import ipaddress
import os
import runpy
import socket


def install_spark_alias(host: str) -> None:
    address = str(ipaddress.IPv4Address(host))
    original = socket.getaddrinfo

    def resolve(name, *args, **kwargs):
        return original(
            address if name in {"dgx-spark", b"dgx-spark"} else name, *args, **kwargs
        )

    socket.getaddrinfo = resolve


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("service", choices=["router", "api", "worker"])
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    if args.service == "worker":
        runpy.run_module("ade_api.features.agent_runtime.worker", run_name="__main__")
        return
    if not args.port or not 1024 <= args.port <= 65535:
        parser.error("An explicit unprivileged loopback port is required")
    if args.service == "router":
        install_spark_alias(os.environ["DGX_SPARK_HOST"])
    import uvicorn

    uvicorn.run(
        "model_router.app:app" if args.service == "router" else "ade_api.main:app",
        host="127.0.0.1",
        port=args.port,
        access_log=False,
    )


if __name__ == "__main__":
    main()
