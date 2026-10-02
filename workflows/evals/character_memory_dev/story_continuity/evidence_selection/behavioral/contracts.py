"""Fixed D04 request freeze; no runtime imports or provider discovery."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
ROOT = DIRECTORY.parents[5]
MODEL = "deepseek::deepseek-flash"
ARMS = (
    ("literal-four", ("E07", "E02", "E05", "E04")),
    ("repaired-four", ("E07", "E02", "E05", "E01")),
    ("whole-pool", tuple(f"E{i:02d}" for i in range(1, 9))),
)
PINNED = {"thinking": {"type": "enabled"}, "reasoning_effort": "high", "stream": False}
ROUTE = {
    "router_model_id": MODEL,
    "model_key": MODEL,
    "source_id": "deepseek",
    "source_adapter": "deepseek_openai",
    "provider_model_id": "deepseek-flash",
    "model_type": "llm",
    "source_base_url": "https://api.deepseek.com",
    "agent_studio_available": True,
    "supports_thinking": True,
    "supports_top_k": False,
    "thinking_default_enabled": True,
    "reasoning_effort_default": "high",
    "profile_applied": True,
    "profile_source": "docs/adr/0025-deepseek-development-lane.md",
    "sampling_defaults": {},
}


def wire(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(wire(value).encode()).hexdigest()


def estimate(request: dict) -> int:
    return (len(wire(request).encode()) + 3) // 4


def load_prepared() -> dict:
    prepared = json.loads((DIRECTORY / "preparation.json").read_bytes())
    from ..offline_inputs import load_offline_inputs

    if load_offline_inputs()[2] != prepared["historical_freeze"]:
        raise ValueError("Historical input/artifact freeze drift")
    for relative, expected in prepared["source_sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen source drift: {relative}")
    packets = json.loads((DIRECTORY / "requests.json").read_bytes())
    if digest(packets) != prepared["requests_sha256"]:
        raise ValueError("Frozen request drift")
    if [(p["arm"], tuple(p["included"])) for p in packets] != list(ARMS):
        raise ValueError("Frozen arm/order drift")
    return {**prepared, "packets": packets}


def review_request(packet: dict, reply: str) -> dict:
    request = copy.deepcopy(packet["reviewer"])
    body = json.loads(request["messages"][1]["content"])
    body["candidate_visible_reply"] = reply
    request["messages"][1]["content"] = json.dumps(body, ensure_ascii=False)
    if estimate(request) > 11469:
        raise ValueError(
            "Actual complete reviewer request exceeds 11469; never truncate"
        )
    return request


def route_receipt(catalog: dict) -> dict:
    items = [i for i in catalog["items"] if i.get("router_model_id") == MODEL]
    sources = [s for s in catalog["sources"] if s.get("id") == "deepseek"]
    if len(items) != 1 or len(sources) != 1:
        raise ValueError("Route missing or ambiguous")
    item, source = items[0], sources[0]
    if any(item.get(k) != v for k, v in ROUTE.items()):
        raise ValueError("Route/profile mismatch; no model substitution")
    if (
        source.get("status") != "healthy"
        or source.get("adapter") != "deepseek_openai"
        or source.get("base_url") != ROUTE["source_base_url"]
    ):
        raise ValueError("Source unavailable or adapter mismatch")
    if not any(
        m.get("provider_model_id") == "deepseek-flash" for m in source["models"]
    ):
        raise ValueError("Provider model absent from fresh source catalog")
    return {k: item[k] for k in ROUTE}
