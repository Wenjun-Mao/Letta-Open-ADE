"""Read-only public recovery observations; no replay, recall, or provider dispatch."""

import json
import re
import time
import urllib.request
import urllib.error
from uuid import UUID

from .operations import create_record


class PublicReads:
    def __init__(self, root, environment):
        self.root, self.sequence = root, 0
        self.keys = {
            "api": environment["INTEGRATION_ADE_OPERATOR_KEY"],
            "native": environment["INTEGRATION_HINDSIGHT_KEY"],
            "router": environment["INTEGRATION_ROUTER_KEY"],
        }

    def get(self, service, path):
        ports = {"api": 18021, "native": 18889, "router": 18019}
        request = urllib.request.Request(
            f"http://127.0.0.1:{ports[service]}{path}",
            headers={"Authorization": "Bearer " + self.keys[service]},
        )
        try:
            response = urllib.request.urlopen(request, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            value = json.loads(response.read())
            status = response.status
        self.sequence += 1
        # Native task payloads/error bodies are not needed to preserve operation IDs.
        if service == "native":
            value = {
                "bank_id": value.get("bank_id"),
                "total": value.get("total"),
                "operations": [
                    {
                        key: row.get(key)
                        for key in (
                            "id",
                            "operation_id",
                            "status",
                            "operation_type",
                            "task_type",
                        )
                    }
                    for row in value.get("operations", [])
                ],
            }
        create_record(
            self.root / f"{self.sequence:05d}.json",
            {
                "service": service,
                "path": path,
                "status": status,
                "time": time.time(),
                "body": value,
            },
        )
        if status != 200:
            raise RuntimeError("paired_checkpoint_public_read_failed")
        return value


def product_readbacks(reads, product_run):
    rows = []
    for path in sorted((product_run / "run/attempts").glob("*/capture.json")):
        observation = json.loads(path.read_text())["payload"]["observation"]
        scope = observation.get("source_scope")
        if scope is None:
            continue
        subject, character = (
            str(UUID(scope["subject"])),
            str(UUID(scope["character_root"])),
        )
        route = f"/api/v3/memory/subjects/{subject}/characters/{character}"
        row = {"attempt": path.parent.name}
        for name in ("source_conversation_id", "probe_conversation_id"):
            identity = str(UUID(observation[name]))
            row[name] = reads.get(
                "api", f"/api/v3/evaluation-sessions/{identity}/state?message_limit=200"
            )
        row["deliveries"] = reads.get("api", route + "/deliveries?limit=100&offset=0")
        row["operations"] = reads.get("api", route + "/operations?limit=100&offset=0")
        rows.append(row)
    return rows


def native_pending(reads, banks):
    pending, failed, incomplete = [], [], []
    for bank in banks:
        if not re.fullmatch(r"ade-[a-f0-9]{32}", bank):
            raise ValueError("paired_checkpoint_bank_identity_invalid")
        value = reads.get(
            "native", f"/v1/default/banks/{bank}/operations?limit=100&offset=0"
        )
        if value["total"] != len(value["operations"]):
            incomplete.append(bank)
        for row in value["operations"]:
            entry = {"bank_id": bank, **row}
            if row["status"] in {"failed", "cancelled"}:
                failed.append(entry)
            elif row["status"] != "completed":
                pending.append(entry)
    return {"pending": pending, "failed": failed, "incomplete_banks": incomplete}


def router_snapshot(reads):
    records, offset = [], 0
    while True:
        page = reads.get("router", f"/v1/router/observations?limit=100&offset={offset}")
        for row in page["items"]:
            identity = str(UUID(row["request_id"]))
            records.append(reads.get("router", "/v1/router/observations/" + identity))
        offset += len(page["items"])
        if offset >= page["total"]:
            return {
                "records": records,
                "missing_outcome_request_ids": [
                    row["request"]["request_id"]
                    for row in records
                    if row["outcome"] is None
                ],
            }
        if not page["items"]:
            raise ValueError("paired_router_pagination_incomplete")
