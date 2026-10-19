"""Finite product safety cases; this controller does not qualify semantics."""

import argparse
import asyncio
import hashlib
import os
from pathlib import Path
import re
import time

import httpx

from .live_bindings import preflight
from .live_runner import capture_traffic, require_admission
from .operations import Lease
from .product_slot import safe_failure
from .public_http import PublicRecordingTransport
from .records import seal, write_new
from .safety_protocol import SafetyContext
from .safety_scenarios import PROXIED_SCENARIOS
from .host_scenarios import HOST_SCENARIOS
from .stale_worker_scenario import stale_worker
from .isolation_scenario import isolation
from .wire_capture import require


SCENARIOS = (
    PROXIED_SCENARIOS
    | HOST_SCENARIOS
    | {"stale-worker": stale_worker, "isolation": isolation}
)


async def run_safety(root, *, activation_root, controller_revision, scenarios):
    if not re.fullmatch(r"[a-f0-9]{40}", controller_revision):
        raise ValueError("A committed controller revision is required")
    if (
        not scenarios
        or len(set(scenarios)) != len(scenarios)
        or any(name not in SCENARIOS for name in scenarios)
    ):
        raise ValueError("Use unique predeclared Stage 1 safety scenarios")
    if Path(__file__).resolve().parents[3].name != controller_revision:
        raise ValueError("Use the staged committed controller directory")
    lease = Lease.load(activation_root)
    source = {
        "source_revision": os.environ["ADE_INTEGRATION_SOURCE_REVISION"],
        "source_fingerprint": os.environ["ADE_INTEGRATION_SOURCE_FINGERPRINT"],
        "source_dirty": "false",
        "activation_id": lease.activation_id,
    }
    if source["source_revision"] != lease.source_revision:
        raise ValueError("Product image differs from the activation")
    require_admission(activation_root, lease, 600 * len(scenarios) + 240)
    urls = {
        "api": "http://ade-api:8000",
        "router": "http://model-router:8010",
        "native": "http://hindsight:8888",
        "fault": "http://fault-proxy:8020",
    }
    for service in urls:
        variable = "HINDSIGHT" if service == "native" else service.upper()
        if os.environ[f"ADE_INTEGRATION_{variable}_URL"] != urls[service]:
            raise ValueError(
                "Safety controller requires the candidate internal endpoints"
            )
    keys = {
        "api": os.environ["ADE_INTEGRATION_API_KEY"],
        "router": os.environ["ADE_INTEGRATION_ROUTER_KEY"],
        "native": os.environ["ADE_INTEGRATION_HINDSIGHT_KEY"],
        "fault": os.environ["ADE_INTEGRATION_FAULT_KEY"],
    }
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    code = {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in (
            "safety_runner.py",
            "safety_protocol.py",
            "safety_scenarios.py",
            "host_scenarios.py",
            "stale_worker_scenario.py",
            "isolation_scenario.py",
        )
    }
    write_new(
        root / "plan.json",
        seal(
            "product-safety-plan",
            {
                "product_source": source,
                "controller_revision": controller_revision,
                "controller_file_sha256": code,
                "scenarios": scenarios,
                "case_timeout_seconds": 600,
                "scope": "Stage 1 synthetic candidate safety, not semantic qualification",
            },
        ),
    )
    outcomes = []
    try:
        async with (
            client("api", root / "preflight", urls, keys) as api,
            client("router", root / "preflight", urls, keys) as router,
            client("native", root / "preflight", urls, keys) as native,
        ):
            runtime, environment = await preflight(api, router, native, source=source)
        write_new(
            root / "environment.json",
            {"runtime": runtime.model_dump(mode="json"), "observed": environment},
        )
        for name in scenarios:
            require_admission(activation_root, lease, 630)
            outcomes.append(await one_case(root / name, name, runtime, urls, keys))
    except Exception as exc:
        write_new(
            root / "failure.json", {"error": safe_failure(exc), "time": time.time()}
        )
        raise
    finally:
        await capture_traffic(root, urls["router"], keys["router"])
        write_new(
            root / "summary.json",
            seal(
                "product-safety-summary",
                {
                    "planned": scenarios,
                    "outcomes": outcomes,
                    "all_passed": len(outcomes) == len(scenarios)
                    and all(row["status"] == "passed" for row in outcomes),
                    "character_review": "UNREVIEWED",
                    "coverage": "declared_scenarios_only_not_all_M6",
                    "limitation": "Safety mechanics only. No general Memory or Character qualification.",
                },
            ),
        )
    return all(row["status"] == "passed" for row in outcomes)


def client(service, root, urls, keys):
    return httpx.AsyncClient(
        base_url=urls[service],
        headers={"Authorization": "Bearer " + keys[service]},
        transport=PublicRecordingTransport(root / (service + "-http")),
        timeout=30,
    )


async def one_case(root, name, runtime, urls, keys):
    root.mkdir(mode=0o700)
    result = {"scenario": name, "status": "failed", "started_at": time.time()}
    write_new(root / "started.json", result)
    async with (
        client("api", root, urls, keys) as api,
        client("router", root, urls, keys) as router,
        client("fault", root, urls, keys) as fault,
    ):
        context = SafetyContext(
            api=api,
            router=router,
            fault=fault,
            root=root,
            deadline=time.monotonic() + 600,
            runtime=runtime,
        )
        try:
            async with asyncio.timeout(600):
                evidence = await SCENARIOS[name](context)
            write_new(root / "evidence.json", evidence)
            result["status"] = "passed"
        except Exception as exc:
            result["error"] = safe_failure(exc)
        finally:
            try:
                await context.restore_host()
            except Exception as exc:
                result["status"] = "failed"
                result["host_restore_error"] = safe_failure(exc)
            for identity in context.rules:
                try:
                    await context.release(identity)
                except Exception as exc:
                    result["status"] = "failed"
                    result.setdefault("release_errors", []).append(safe_failure(exc))
            try:
                capture = await context.capture()
                write_new(root / "readbacks.json", capture)
                if name in {"failed-generation", "cancellation"}:
                    require(
                        not any(row["wires"] for row in capture["payload"]["runs"]),
                        "held_or_rejected_request_reached_router",
                    )
            except Exception as exc:
                result["status"] = "failed"
                result["capture_error"] = safe_failure(exc)
    result["finished_at"] = time.time()
    write_new(root / "outcome.json", seal("product-safety-outcome", result))
    print(f"{name}: {result['status']}", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--controller-revision", required=True)
    parser.add_argument("--scenario", action="append", choices=tuple(SCENARIOS))
    args = parser.parse_args()
    ok = asyncio.run(
        run_safety(
            args.out,
            activation_root=Path("/activation"),
            controller_revision=args.controller_revision,
            scenarios=args.scenario or list(PROXIED_SCENARIOS),
        )
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
