"""Independent, public-HTTP readback for the frozen P4 restart checkpoint."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import quote

from .driver_support import HindsightHTTP, feature_scope
from . import restart_selection


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_selection(path: Path) -> dict:
    selection = restart_selection.read_selection(path)
    validate_feature_scopes(selection)
    return selection


def validate_feature_scopes(selection: dict) -> None:
    """Bind runner-side selection scopes to the existing public feature contract."""
    for bank in selection["banks"]:
        for scope in bank["scopes"]:
            public_scope = feature_scope(
                bank["workspace_id"], bank["subject_id"], scope["character_root_id"]
            )
            if (public_scope.get("bank_id") != bank["bank_id"]
                    or scope["tags"] != public_scope.get("tags")
                    or scope["tags_match"] != public_scope.get("tags_match")):
                raise RuntimeError("restart_selection_scope_contract_mismatch")


def re_hash(value) -> bool:
    return restart_selection.valid_sha256(value)


def re_sha(value) -> bool:
    return restart_selection.valid_sha1(value)


def canonical_entities_sha256(entities: list[str]) -> str:
    """Hash entity names as an order-independent structured collection."""
    canonical = json.dumps(sorted(entities), ensure_ascii=False, separators=(",", ":"))
    return sha_text(canonical)


def fact_projection(item: dict, text_hash: str, state: str, entities_sha256: str) -> dict:
    tags = item.get("tags")
    sources = item.get("source_memory_ids", [])
    context = item.get("context")
    metadata = item.get("metadata", {})
    text_fields = ("date", "mentioned_at", "occurred_start", "occurred_end", "chunk_id",
                   "invalidation_reason", "invalidated_at", "edited_at", "updated_at",
                   "consolidated_at", "consolidation_failed_at")
    if (not isinstance(tags, list) or any(not isinstance(tag, str) or not tag for tag in tags)
            or not isinstance(sources, list) or any(not isinstance(value, str) for value in sources)
            or not isinstance(context, str)
            or not isinstance(metadata, dict)
            or any(item.get(key) is not None and not isinstance(item.get(key), str) for key in text_fields)
            or not isinstance(item.get("date", ""), str)
            or type(item.get("proof_count", 1)) is not int or item.get("proof_count", 1) < 0
            or item.get("fact_type") not in {"world", "experience", "observation"}):
        raise RuntimeError("restart_fact_projection_invalid")
    invalidation_reason = item.get("invalidation_reason")
    metadata_bytes = json.dumps(metadata, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":"), allow_nan=False).encode("utf-8")
    return {
        "id": item["id"], "document_id": item.get("document_id"),
        "text_sha256": text_hash,
        "context_sha256": None if context is None else sha_text(context),
        "state": state, "fact_type": item.get("fact_type"), "date": item.get("date", ""),
        "mentioned_at": item.get("mentioned_at"),
        "occurred_start": item.get("occurred_start"), "occurred_end": item.get("occurred_end"),
        "chunk_id": item.get("chunk_id"), "proof_count": item.get("proof_count", 1),
        "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        "entities_sha256": entities_sha256, "tags": sorted(tags),
        "source_memory_ids": sorted(sources),
        "consolidated_at": item.get("consolidated_at"),
        "consolidation_failed_at": item.get("consolidation_failed_at"),
        "invalidation_reason_sha256": None if invalidation_reason is None else sha_text(invalidation_reason),
        "invalidated_at": item.get("invalidated_at"),
        "edited_at": item.get("edited_at"), "updated_at": item.get("updated_at"),
    }


async def pages(client: HindsightHTTP, bank_id: str, state: str) -> list[dict]:
    result = []
    offset = 0
    total = None
    path = f"/v1/default/banks/{quote(bank_id, safe='')}/memories/list"
    while total is None or offset < total:
        page = await client.request("GET", path, params={"state": state, "limit": 100, "offset": offset})
        items = page.get("items")
        page_total = page.get("total")
        if (not isinstance(items, list) or type(page_total) is not int or page_total < 0
                or type(page.get("limit")) is not int or page.get("limit") != 100
                or type(page.get("offset")) is not int or page.get("offset") != offset):
            raise RuntimeError("restart_readback_pagination_invalid")
        if total is None:
            total = page_total
        elif page_total != total:
            raise RuntimeError("restart_readback_pagination_changed")
        page_ids = []
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                raise RuntimeError("restart_readback_memory_identity_invalid")
            page_ids.append(item["id"])
        if len(page_ids) != len(set(page_ids)) or set(page_ids) & {row["id"] for row in result}:
            raise RuntimeError("restart_readback_duplicate_memory_id")
        if len(items) != min(100, max(0, total - offset)):
            raise RuntimeError("restart_readback_page_incomplete")
        result.extend(items)
        offset += 100
    return result


def index_memory_states(valid: list[dict], invalidated: list[dict]) -> dict[str, dict[str, dict]]:
    states = {
        "valid": {item["id"]: item for item in valid},
        "invalidated": {item["id"]: item for item in invalidated},
    }
    if len(states["valid"]) != len(valid) or len(states["invalidated"]) != len(invalidated):
        raise RuntimeError("restart_readback_duplicate_memory_id")
    if set(states["valid"]) & set(states["invalidated"]):
        raise RuntimeError("restart_readback_memory_in_both_states")
    return states


async def fact_entities(client: HindsightHTTP, bank_id: str, source_id: str,
                        memory_id: str, state: str, list_text_hash: str) -> str:
    """Read the public detail projection and bind its structured entity names."""
    path = (f"/v1/default/banks/{quote(bank_id, safe='')}/memories/"
            f"{quote(memory_id, safe='')}")
    detail = await client.request("GET", path)
    if (not isinstance(detail, dict)
            or detail.get("id") != memory_id
            or detail.get("document_id") != source_id
            or detail.get("state") != state
            or not isinstance(detail.get("text"), str)
            or sha_text(detail["text"]) != list_text_hash):
        raise RuntimeError("restart_fact_detail_identity_source_state_mismatch")
    entities = detail.get("entities")
    if (not isinstance(entities, list)
            or any(not isinstance(name, str) or not name for name in entities)):
        raise RuntimeError("restart_fact_detail_entities_invalid")
    return canonical_entities_sha256(entities)


async def capture(selection: dict, client: HindsightHTTP, run_identity: dict) -> dict:
    if (run_identity.get("release_sha") != selection["release_sha"]
            or run_identity.get("registry_sha256") != selection["registry_sha256"]
            or not re_hash(run_identity.get("epoch_sha256"))):
        raise RuntimeError("restart_readback_campaign_identity_mismatch")
    banks = []
    for bank in selection["banks"]:
        bank_id = bank["bank_id"]
        valid, invalidated = await asyncio.gather(pages(client, bank_id, "valid"), pages(client, bank_id, "invalidated"))
        indexed = index_memory_states(valid, invalidated)
        scope_projections = []
        for scope in bank["scopes"]:
            actual_positive = set()
            character_tag = f"character:{scope['character_root_id']}"
            for identifier in scope["cohort_ids"]:
                item = indexed["valid"].get(identifier)
                archived = indexed["invalidated"].get(identifier)
                selected = item or archived
                if not isinstance(selected, dict):
                    raise RuntimeError("restart_scope_fact_missing")
                tags = selected.get("tags")
                fact_type = selected.get("fact_type")
                if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag for tag in tags):
                    raise RuntimeError("restart_scope_tags_invalid")
                tag_overlap = bool(set(scope["tags"]) & set(tags))
                # any_strict is nonempty OR overlap; observations additionally stay
                # inside exactly the selected character root, matching RecallScope.
                observation_is_local = (
                    fact_type != "observation"
                    or {tag for tag in tags if tag.startswith("character:")} == {character_tag}
                )
                if item is not None and tag_overlap and observation_is_local:
                    actual_positive.add(identifier)
            actual_exclusion = set(scope["cohort_ids"]) - actual_positive
            if (actual_positive != set(scope["positive_ids"])
                    or actual_exclusion != set(scope["exclusion_ids"])):
                raise RuntimeError("restart_scope_eligibility_mismatch")
            scope_projections.append({
                "character_root_id": scope["character_root_id"], "tags": scope["tags"],
                "tags_match": scope["tags_match"], "cohort_ids": sorted(scope["cohort_ids"]),
                "positive_ids": sorted(actual_positive), "exclusion_ids": sorted(actual_exclusion),
            })
        sources = []
        for source in bank["sources"]:
            source_id = source["source_id"]
            document = await client.request("GET", f"/v1/default/banks/{quote(bank_id, safe='')}/documents/{quote(source_id, safe='')}")
            document_value = document.get("document", document)
            original_text = document_value.get("original_text") if isinstance(document_value, dict) else None
            if not isinstance(original_text, str):
                raise RuntimeError("restart_source_text_missing")
            retain_params = document_value.get("retain_params") or {}
            context = retain_params.get("context") if isinstance(retain_params, dict) else None
            if (document_value.get("content_hash") != source["content_hash"]
                    or (None if context is None else sha_text(context)) != source["context_sha256"]):
                raise RuntimeError("restart_source_context_or_content_hash_mismatch")
            facts = {}
            for state in ("valid", "invalidated"):
                rows = []
                for frozen in source["facts"][state]:
                    other_state = "invalidated" if state == "valid" else "valid"
                    if frozen["id"] in indexed[other_state]:
                        raise RuntimeError("restart_fact_present_in_both_states")
                    item = indexed[state].get(frozen["id"])
                    if not isinstance(item, dict) or item.get("document_id") != source_id:
                        raise RuntimeError("restart_fact_state_or_source_mismatch")
                    content = item.get("text")
                    if not isinstance(content, str):
                        raise RuntimeError("restart_fact_text_missing")
                    digest = sha_text(content)
                    if digest != frozen["text_sha256"]:
                        raise RuntimeError("restart_fact_text_hash_mismatch")
                    if item.get("state") != state or not isinstance(item.get("tags"), list):
                        raise RuntimeError("restart_fact_state_or_tags_invalid")
                    entities_sha256 = await fact_entities(
                        client, bank_id, source_id, frozen["id"], state, digest
                    )
                    rows.append(fact_projection(item, digest, state, entities_sha256))
                facts[state] = sorted(rows, key=lambda row: row["id"])
            if sha_text(original_text) != source["original_text_sha256"]:
                raise RuntimeError("restart_original_source_hash_mismatch")
            curation_facts = {row["id"]: row for row in facts["invalidated"]}
            selected_curation = []
            for identifier in source.get("curation_ids", []):
                row = curation_facts.get(identifier)
                if row is None:
                    raise RuntimeError("restart_curation_fact_missing")
                selected_curation.append(row)
            sources.append({
                "source_id": source_id,
                "original_text_sha256": sha_text(original_text),
                "context_sha256": None if context is None else sha_text(context),
                "content_hash": document_value["content_hash"],
                "retain_params_context_present": isinstance(retain_params, dict) and "context" in retain_params,
                "curation": sorted(selected_curation, key=lambda row: row["id"]),
                "facts": facts,
            })
        banks.append({"bank_id": bank_id, "workspace_id": bank["workspace_id"],
                      "subject_id": bank["subject_id"],
                      "scope_eligibility": sorted(scope_projections, key=lambda row: row["character_root_id"]),
                      "sources": sorted(sources, key=lambda row: row["source_id"])})
    return {"schema": 1, "selection_sha256": restart_selection.hash_json(selection),
            "selection_release_sha": selection["release_sha"],
            "selection_registry_sha256": selection["registry_sha256"],
            "selection_before_epoch_sha256": selection["before_epoch_sha256"],
            "run_identity": run_identity, "captured_at": time.time(),
            "banks": sorted(banks, key=lambda row: row["bank_id"])}


def validate_snapshot(snapshot: dict, selection: dict) -> None:
    selection_hash = hash_json(selection)
    if (snapshot.get("selection_sha256") != selection_hash
            or snapshot.get("selection_release_sha") != selection["release_sha"]
            or snapshot.get("selection_registry_sha256") != selection["registry_sha256"]
            or snapshot.get("selection_before_epoch_sha256") != selection["before_epoch_sha256"]):
        raise RuntimeError("restart_snapshot_selection_identity_mismatch")
    identity = snapshot.get("run_identity", {})
    if (identity.get("release_sha") != selection["release_sha"]
            or identity.get("registry_sha256") != selection["registry_sha256"]):
        raise RuntimeError("restart_snapshot_campaign_identity_mismatch")
    observed_banks = {bank["bank_id"]: bank for bank in snapshot.get("banks", [])}
    if set(observed_banks) != {bank["bank_id"] for bank in selection["banks"]}:
        raise RuntimeError("restart_snapshot_bank_set_mismatch")
    for frozen_bank in selection["banks"]:
        observed_bank = observed_banks[frozen_bank["bank_id"]]
        expected_scope = sorted(frozen_bank["scopes"], key=lambda row: row["character_root_id"])
        actual_scope = observed_bank.get("scope_eligibility", [])
        normalized_expected = [{key: scope[key] if key in {"character_root_id", "tags_match"}
                                else sorted(scope[key]) for key in (
                                    "character_root_id", "tags", "tags_match", "cohort_ids",
                                    "positive_ids", "exclusion_ids")}
                              for scope in expected_scope]
        if (observed_bank.get("workspace_id") != frozen_bank["workspace_id"]
                or observed_bank.get("subject_id") != frozen_bank["subject_id"]
                or actual_scope != normalized_expected):
            raise RuntimeError("restart_snapshot_scope_set_mismatch")
        observed_sources = {source["source_id"]: source for source in observed_bank.get("sources", [])}
        if set(observed_sources) != {source["source_id"] for source in frozen_bank["sources"]}:
            raise RuntimeError("restart_snapshot_source_set_mismatch")
        for frozen_source in frozen_bank["sources"]:
            observed = observed_sources[frozen_source["source_id"]]
            if (observed["original_text_sha256"] != frozen_source["original_text_sha256"]
                    or observed["context_sha256"] != frozen_source["context_sha256"]
                    or observed["content_hash"] != frozen_source["content_hash"]):
                raise RuntimeError("restart_snapshot_source_hash_mismatch")
            for state in ("valid", "invalidated"):
                facts = observed["facts"][state]
                expected = {item["id"]: item["text_sha256"] for item in frozen_source["facts"][state]}
                actual = {item["id"]: item["text_sha256"] for item in facts}
                if actual != expected or any(item["state"] != state for item in facts):
                    raise RuntimeError("restart_snapshot_fact_set_or_state_mismatch")
            actual_curation = {item["id"] for item in observed["curation"]}
            if actual_curation != set(frozen_source["curation_ids"]):
                raise RuntimeError("restart_snapshot_curation_set_mismatch")
            invalidated_by_id = {item["id"]: item for item in observed["facts"]["invalidated"]}
            expected_curation = sorted(
                (invalidated_by_id[identifier] for identifier in frozen_source["curation_ids"]),
                key=lambda row: row["id"],
            )
            if observed["curation"] != expected_curation:
                raise RuntimeError("restart_snapshot_curation_projection_mismatch")


def compare(before: dict, after: dict, selection: dict) -> dict:
    validate_snapshot(before, selection)
    validate_snapshot(after, selection)
    before_identity = before.get("run_identity", {})
    after_identity = after.get("run_identity", {})
    if (before.get("selection_sha256") != after.get("selection_sha256")
            or before.get("banks") != after.get("banks")
            or before_identity.get("release_sha") != after_identity.get("release_sha")
            or before_identity.get("release_sha") != before.get("selection_release_sha")
            or before_identity.get("registry_sha256") != after_identity.get("registry_sha256")
            or before_identity.get("registry_sha256") != before.get("selection_registry_sha256")
            or after.get("selection_registry_sha256") != before.get("selection_registry_sha256")
            or before_identity.get("epoch_sha256") != before.get("selection_before_epoch_sha256")
            or after.get("selection_before_epoch_sha256") != before.get("selection_before_epoch_sha256")
            or after_identity.get("epoch_sha256") == before_identity.get("epoch_sha256")):
        raise RuntimeError("restart_persistence_readback_mismatch")
    return {"schema": 1, "status": "completed", "selection_sha256": before["selection_sha256"],
            "before_sha256": hash_json(before),
            "after_sha256": hash_json(after), "bank_count": len(after["banks"]),
            "release_sha": after_identity["release_sha"],
            "registry_sha256": after_identity["registry_sha256"],
            "before_epoch_sha256": before_identity["epoch_sha256"],
            "after_epoch_sha256": after_identity["epoch_sha256"],
            "source_count": sum(len(bank["sources"]) for bank in after["banks"]),
            "fact_state_counts": {
                state: sum(len(source["facts"][state]) for bank in after["banks"] for source in bank["sources"])
                for state in ("valid", "invalidated")
            }, "completed_at": time.time(), "claim": "bounded_restart_persistence_readback"}


def hash_json(value: dict) -> str:
    return restart_selection.hash_json(value)


if __name__ == "__main__":
    from .restart_readback_cli import main

    raise SystemExit(main())
