"""Freeze declared identities and verify the available public runtime observations."""

import asyncio
import hashlib
import json
from pathlib import Path
import time

import httpx
from model_catalog_contracts.deployment_manifest import DeploymentManifest
from ade_api.integrations.hindsight_bank import bank_configuration_sha256
from content.prompts.system.chat.chat_v20261019 import PROMPT

from .casebook import load_suite
from .models import RuntimeBinding
from .model_cache import WEIGHT_SHA256, REVISION as RERANKER_REVISION
from .public_http import get_json
from .records import digest
from .wire_capture import require, validate_wire


CONFIG = Path(__file__).with_name("config")
CHARACTER_ROUTE = "deepseek::deepseek-flash"
EMBEDDING_ROUTE = "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B"


def declared_runtime(revision: str):
    suite = load_suite()
    payload = json.loads((CONFIG / "deployments.json").read_bytes())
    manifest = DeploymentManifest.from_payload(payload)
    deployment = manifest.for_route_alias(CHARACTER_ROUTE)
    require(
        deployment.roles == ("conversation", "compaction")
        and not deployment.qualification.qualified,
        "candidate_role_or_qualification_changed",
    )
    sources = json.loads((CONFIG / "sources.json").read_bytes())
    embedding_source = next(
        item for item in sources if item["id"] == "dgx_embedding_sidecar"
    )
    embedding = {
        "router_model": EMBEDDING_ROUTE,
        "provider_model": "Qwen/Qwen3-Embedding-0.6B",
        "endpoint": embedding_source["base_url"],
        "dimensions": 1024,
        "passage_prefix": "",
        "query_prefix": "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: ",
    }
    runtime = RuntimeBinding(
        product_revision=revision,
        persona_version=suite["persona"]["content_sha256"],
        persona_text=suite["persona"]["content"],
        prompt_version="chat_v20261019",
        system_prompt=PROMPT,
        character_route=CHARACTER_ROUTE,
        character_identity_sha256=deployment.fingerprint.sha256,
        character_settings=dict(deployment.fingerprint.sampling_settings),
        context_compaction_identity_sha256=deployment.fingerprint.sha256,
        memory_implementation="hindsight",
        memory_config_sha256=bank_configuration_sha256(),
        embedding_identity_sha256=digest(embedding),
    )
    environment = {
        "character": payload,
        "memory": {
            "bank_configuration_sha256": runtime.memory_config_sha256,
            "global_configuration_sha256": hashlib.sha256(
                (CONFIG / "hindsight.env").read_bytes()
            ).hexdigest(),
            "native_version": "0.10.3",
            "reranker_revision": RERANKER_REVISION,
            "reranker_weight_sha256": WEIGHT_SHA256,
        },
        "embedding": embedding,
        "limitations": [
            "Configured and reported provider identities are not remote weight attestations."
        ],
    }
    return runtime, environment


async def wire_records(router, *, run_id=None):
    records, offset = [], 0
    while True:
        parameters = {"offset": offset, "limit": 100}
        if run_id is not None:
            parameters["run_id"] = run_id
        page = await get_json(router, "/v1/router/observations", params=parameters)
        require(page["enabled"] is True, "router_observations_disabled")
        for item in page["items"]:
            records.append(
                await get_json(router, f"/v1/router/observations/{item['request_id']}")
            )
        offset += len(page["items"])
        if offset >= page["total"]:
            return records
        require(bool(page["items"]), "wire_pagination_incomplete")


async def preflight(api, router, native, *, source: dict, timeout=240):
    deadline = time.monotonic() + timeout
    while True:
        try:
            health = await get_json(api, "/api/v3/worker-health")
            native_health = await get_json(native, "/health")
            require(
                health["worker_ready"] is True and health["source_dirty"] is False,
                "worker_not_clean_and_ready",
            )
            require(
                health["source_revision"] == source["source_revision"]
                and health["source_fingerprint"] == source["source_fingerprint"],
                "worker_source_mismatch",
            )
            break
        except httpx.HTTPError:
            if time.monotonic() >= deadline:
                raise
            await asyncio.sleep(2)
    catalog = await get_json(router, "/v1/router/model-catalog")
    runtime, environment = declared_runtime(source["source_revision"])
    characters = [
        item for item in catalog["items"] if item["model_key"] == CHARACTER_ROUTE
    ]
    require(
        len(characters) == 1
        and characters[0]["deployment"]["fingerprint"]["sha256"]
        == runtime.character_identity_sha256,
        "catalog_candidate_identity_mismatch",
    )
    require(
        any(item["model_key"] == EMBEDDING_ROUTE for item in catalog["items"]),
        "embedding_route_missing",
    )
    observations = await wire_records(router)
    dimension_proof = []
    for record in observations:
        if record["request"]["metadata"].get("router_model") != EMBEDDING_ROUTE:
            continue
        request = validate_wire(record)
        outcome = record["outcome"]
        if outcome.get("http_status") == 200:
            require(
                request["body"]["model"] == environment["embedding"]["provider_model"]
                and outcome["visible_response"].get("embedding_dimensions") == [1024],
                "initialized_embedding_identity_mismatch",
            )
            dimension_proof.append(request["request_id"])
    require(bool(dimension_proof), "native_embedding_initialization_not_observed")
    return runtime, {
        **environment,
        "worker_health": health,
        "native_health": native_health,
        "catalog": catalog,
        "startup_observations": observations,
        "embedding_initialization_request_ids": dimension_proof,
    }
