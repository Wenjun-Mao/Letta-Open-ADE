"""Collect through ADE/Router public boundaries, preserving records before validation."""

from pathlib import Path
import hashlib
import time

from .capture_validation import qualify_run_capture, require
from .checks import reject_sensitive_fields
from .records import seal, write_new


class PublicReadJournal:
    def __init__(self, root: Path):
        self.root = root
        self.sequence = 0

    async def read(self, client, path: str, **kwargs):
        self.sequence += 1
        prefix = self.root / f"{self.sequence:05d}"
        write_new(
            prefix.with_suffix(".request.json"),
            {
                "method": "GET",
                "path": path,
                "params": kwargs.get("params"),
                "time": time.time(),
            },
        )
        try:
            response = await client.get(path, **kwargs)
        except Exception as exc:
            write_new(
                prefix.with_suffix(".failure.json"),
                {"error_type": type(exc).__name__, "time": time.time()},
            )
            raise
        record = {
            "status": response.status_code,
            "time": time.time(),
            "body_sha256": hashlib.sha256(response.content).hexdigest(),
        }
        try:
            value = response.json()
            reject_sensitive_fields(value)
        except (ValueError, TypeError):
            write_new(
                prefix.with_suffix(".response.json"),
                {
                    **record,
                    "input_complete": False,
                    "limitation": "unsafe_or_non_json_response_excluded",
                },
            )
            raise ValueError("unsafe_or_non_json_public_observation") from None
        write_new(
            prefix.with_suffix(".response.json"),
            {**record, "input_complete": True, "body": value},
        )
        response.raise_for_status()
        return value


async def collect_saved_run(
    *,
    api,
    router,
    run_id: str,
    phase: str,
    state_path: str,
    scope: dict,
    source: dict,
    expected_input: str,
    fresh_probe: bool,
    out: Path,
):
    require(phase in {"setup", "probe", "diagnostic"}, "invalid_phase_group")
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    out.chmod(0o700)
    journal = PublicReadJournal(out / "http")
    run = await journal.read(api, f"/api/v3/runs/{run_id}")
    export = await journal.read(api, f"/api/v3/private-observations/runs/{run_id}")
    state = await journal.read(api, state_path, params={"message_limit": 200})
    events = []
    after = 0
    while True:
        page = await journal.read(
            api,
            f"/api/v3/runs/{run_id}/event-log",
            params={"limit": 500, "after_sequence": after},
        )
        if not page["items"]:
            break
        events.extend(page["items"])
        next_after = page["items"][-1]["sequence"]
        require(next_after > after, "event_pagination_did_not_advance")
        after = next_after
    wires = []
    offset = 0
    while True:
        page = await journal.read(
            router,
            "/v1/router/observations",
            params={"run_id": run_id, "limit": 100, "offset": offset},
        )
        require(page["enabled"] is True, "router_capture_disabled")
        for item in page["items"]:
            wires.append(
                await journal.read(
                    router, f"/v1/router/observations/{item['request_id']}"
                )
            )
        offset += len(page["items"])
        if offset >= page["total"]:
            break
        require(bool(page["items"]), "router_pagination_did_not_advance")
    bundle = {
        "schema_version": 1,
        "phase_group": phase,
        "phase_run_id": run_id,
        "run": run,
        "export": export,
        "state": state,
        "events": events,
        "wires": wires,
        "scope": scope,
        "source": source,
        "expected_input": expected_input,
        "fresh_probe": fresh_probe,
    }
    write_new(out / "collection.json", seal("product-run-collection", bundle))
    try:
        result = qualify_run_capture(
            run=run,
            export=export,
            state=state["conversation"],
            wires=wires,
            events=events,
            scope=scope,
            source=source,
            expected_input=expected_input,
            fresh_probe=fresh_probe,
        )
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        write_new(
            out / "validation.json",
            {
                "complete": False,
                "error_type": type(exc).__name__,
                "error_code": str(exc)
                if type(exc) is ValueError
                else "invalid_capture_structure",
            },
        )
        raise
    write_new(out / "validation.json", {"complete": True, **result})
    return bundle, result
