"""Source-backed isolated configuration; no catalog discovery or provider calls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from model_catalog_contracts.deployment_manifest import (
    DeploymentFingerprint,
    DeploymentManifest,
)

DIRECTORY = Path(__file__).parent
MANIFEST = DIRECTORY / "deployment-manifest.json"
SOURCES = DIRECTORY / "sources.json"
MANIFEST_SHA256 = "918e5a4d075980af852d0fd1967f7bf4c9e126fd04754a8a22548a237c80da55"
SOURCES_SHA256 = "c5c78910c7f502748390b4ebb9b7ed3dad60c30cd3ba89bd3c4873a5292fc3ec"
ROLE_ROUTES = {
    "conversation": "deepseek::deepseek-flash",
    "reviewer": "deepseek::deepseek-flash",
    "retriever": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
}


def _frozen_json(path: Path, expected: str):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"Isolated baseline configuration changed: {path.name}")
    return json.loads(raw)


def manifest() -> DeploymentManifest:
    # The shared parser computes the fingerprint from its full payload. A
    # copied sha256 field can never make a different deployment match this pin.
    return DeploymentManifest.from_payload(_frozen_json(MANIFEST, MANIFEST_SHA256))


def expected_catalog() -> dict:
    """Expected metadata for offline comparison/fakes, NOT a discovery receipt."""
    sources = {item["id"]: item for item in _frozen_json(SOURCES, SOURCES_SHA256)}
    items = []
    for entry in manifest().deployments:
        source = sources[entry.fingerprint.provider]
        items.append(
            {
                "route_aliases": list(entry.route_aliases),
                "source_adapter": source["adapter"],
                "source_base_url": source["base_url"],
                "deployment": entry.as_catalog_dict(),
            }
        )
    return {"items": items}


def validate_catalog(catalog: dict) -> dict:
    """Check supplied metadata before approval; never fetch or qualify it."""
    expected = expected_catalog()
    items = catalog.get("items")
    if not isinstance(items, list):
        raise ValueError("Catalog items missing")
    bindings = {}
    for role, route in ROLE_ROUTES.items():
        matches = [item for item in items if route in item.get("route_aliases", [])]
        if len(matches) != 1:
            raise ValueError(f"Missing or ambiguous isolated route: {route}")
        actual = matches[0]
        wanted = next(
            item for item in expected["items"] if route in item["route_aliases"]
        )
        if any(
            actual.get(key) != wanted[key]
            for key in ("source_adapter", "source_base_url", "deployment")
        ):
            raise ValueError(f"Isolated catalog binding differs: {route}")
        fingerprint = actual["deployment"]["fingerprint"]
        computed = DeploymentFingerprint.from_payload(
            {key: value for key, value in fingerprint.items() if key != "sha256"}
        ).sha256
        if computed != fingerprint["sha256"]:
            raise ValueError("Catalog fingerprint does not match its payload")
        bindings[role] = {
            "route": route,
            "deployment_fingerprint": computed,
            "source_base_url": actual["source_base_url"],
        }
    return bindings


def preparation_binding() -> dict:
    return {
        "manifest_sha256": MANIFEST_SHA256,
        "sources_sha256": SOURCES_SHA256,
        "roles": validate_catalog(expected_catalog()),
        "catalog_status": "expected_configuration_not_live_observation",
        "qualification": "none; isolated candidate only",
        "fingerprint_provenance": {
            "retriever": "264c57e:config/model-router/deployment-manifest.json",
            "conversation_and_reviewer": "90b72b435f2d54af00c3c44d413518a628ee94aa:config/model-router/deployment-manifest.json",
        },
    }
