"""Public-client, operation, phase and scope helpers for the replay driver."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx

from .receipts import ReceiptStore

ROOT = Path(__file__).resolve().parents[3]
FEATURE = "ade_api.features.agent_runtime.hindsight_evaluation"
TERMINAL = {"completed", "failed", "cancelled", "not_found"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_operation(value: dict) -> dict:
    return {
        key: value.get(key)
        for key in ("operation_id", "operation_type", "status", "retry_count", "completed_at")
        if key in value
    } | {
        "child_operations": [
            {key: child.get(key) for key in ("operation_id", "status", "sub_batch_index", "items_count") if key in child}
            for child in value.get("child_operations", []) if isinstance(child, dict)
        ] if isinstance(value.get("child_operations"), list) else []
    }


class HindsightHTTP:
    def __init__(self, client: httpx.AsyncClient, base_url: str, api_key: str):
        parsed = urlsplit(base_url)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment or not api_key.strip()):
            raise RuntimeError("hindsight_credentials_missing")
        self.client, self.base_url, self.api_key = client, base_url.rstrip("/"), api_key

    async def request(self, method: str, path: str, *, body=None, raw_body: bytes | None = None, params=None, receipt=None):
        body_bytes = raw_body
        if body is not None:
            canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
            if body_bytes is None:
                body_bytes = canonical
            elif json.loads(body_bytes) != body:
                raise RuntimeError("frozen_request_body_mismatch")
        if receipt:
            receipt.write("request", {
                "method": method, "path": path, "query_params": params,
                "body_sha256": sha(body_bytes) if body_bytes is not None else None,
                "body_utf8": body_bytes.decode("utf-8") if body_bytes is not None else None,
            })
        try:
            response = await self.client.request(
                method, self.base_url + path,
                headers={"Authorization": f"Bearer {self.api_key}", **({"Content-Type": "application/json"} if body_bytes is not None else {})},
                content=body_bytes, params=params,
                timeout=120,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError("hindsight_transport_failed") from exc
        if receipt:
            receipt.write("response", {"http_status": response.status_code})
        if response.is_error:
            raise RuntimeError(f"hindsight_http_{response.status_code}")
        try:
            value = response.json()
        except ValueError as exc:
            raise RuntimeError("hindsight_response_invalid") from exc
        if not isinstance(value, dict):
            raise RuntimeError("hindsight_response_invalid")
        return value

    async def operation(self, bank_id: str, operation_id: str, receipt):
        try:
            timeout = int(os.getenv("ADE_EVAL_OPERATION_TIMEOUT_SECONDS", "600"))
        except ValueError as exc:
            raise RuntimeError("operation_timeout_invalid") from exc
        if not 1 <= timeout <= 3600:
            raise RuntimeError("operation_timeout_invalid")
        deadline = time.monotonic() + timeout
        base = f"/v1/default/banks/{quote(bank_id, safe='')}/operations/"
        ancestry: set[str] = set()

        async def wait_one(selected_id: str, parent: str | None = None):
            if selected_id in ancestry:
                raise RuntimeError("operation_child_cycle")
            ancestry.add(selected_id)
            try:
                while True:
                    data = await self.request("GET", base + quote(selected_id, safe=''))
                    returned_id = data.get("operation_id", data.get("id"))
                    if returned_id != selected_id:
                        raise RuntimeError("operation_identity_mismatch")
                    status = data.get("status")
                    if status not in {"pending", "processing", "completed", "failed", "cancelled", "not_found"}:
                        raise RuntimeError("operation_status_invalid")
                    projected = safe_operation(data)
                    projected["next_retry_at"] = data.get("next_retry_at")
                    projected["parent_operation_id"] = parent
                    receipt.write("operation", projected)
                    if status in {"failed", "cancelled", "not_found"}:
                        raise RuntimeError("operation_failed")
                    children = data.get("child_operations") if isinstance(data.get("child_operations"), list) else []
                    child_ids = []
                    for child in children:
                        if not isinstance(child, dict):
                            raise RuntimeError("operation_children_invalid")
                        child_id = child.get("operation_id")
                        child_status = child.get("status")
                        if not isinstance(child_id, str) or child_status not in {"pending", "processing", "completed", "failed", "cancelled", "not_found"}:
                            raise RuntimeError("operation_children_invalid")
                        child_ids.append(child_id)
                    if len(child_ids) != len(set(child_ids)):
                        raise RuntimeError("operation_child_duplicate")
                    for child_id in child_ids:
                        await wait_one(child_id, selected_id)
                    if status == "completed":
                        return projected
                    if time.monotonic() >= deadline:
                        raise RuntimeError("operation_timeout")
                    await asyncio.sleep(2)
            finally:
                ancestry.remove(selected_id)

        return await wait_one(operation_id)


class NamedReceipt:
    def __init__(self, store: ReceiptStore, prefix: str):
        self.store, self.prefix, self.count = store, prefix, 0

    def name(self, suffix):
        self.count += 1
        return f"{self.prefix}-{self.count:05d}-{suffix}.json"

    def write(self, suffix, value):
        self.store.write(self.name(suffix), value)


def feature_scope(workspace, subject, root):
    result = subprocess.run([
        sys.executable, "-m", FEATURE, "scope",
        "--workspace-id", workspace, "--subject-id", subject, "--character-root-id", root,
    ], cwd=ROOT, capture_output=True, text=True, check=True)
    value = json.loads(result.stdout)
    if value.get("tags_match") != "any_strict" or len(value.get("tags", [])) != 2:
        raise RuntimeError("feature_scope_invalid")
    return value


def set_phase(output: Path, phase: str, operation_id: str):
    target = Path(os.environ.get("ADE_EVAL_PHASE_FILE", str(output / "phase.json")))
    if target.name != "phase.json":
        raise RuntimeError("phase_target_invalid")
    subprocess.run([
        sys.executable, "-m", "workflows.evals.hindsight_memory_probe.phase",
        "--receipts", str(target.parent), "--phase", phase, "--operation-id", operation_id,
    ], cwd=ROOT, check=True, capture_output=True)
    value = json.loads(target.read_text(encoding="utf-8"))
    if value.get("phase") != phase or value.get("operation_id") != operation_id:
        raise RuntimeError("phase_marker_mismatch")
    return value
