"""Independent, public-HTTP readback for the frozen P4 restart checkpoint."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import quote

from .driver_support import HindsightHTTP


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_selection(path: Path) -> dict:
    selection = json.loads(path.read_text(encoding="utf-8"))
    if selection.get("schema") != 1 or not isinstance(selection.get("banks"), list) or not selection["banks"]:
        raise RuntimeError("restart_selection_invalid")
    if (not re_sha(selection.get("release_sha"))
            or not re_hash(selection.get("registry_sha256"))
            or not re_hash(selection.get("before_epoch_sha256"))):
        raise RuntimeError("restart_selection_campaign_identity_invalid")
    bank_ids = [bank.get("bank_id") for bank in selection["banks"] if isinstance(bank, dict)]
    if (len(bank_ids) != len(selection["banks"])
            or any(not isinstance(identifier, str) or not identifier for identifier in bank_ids)
            or len(bank_ids) != len(set(bank_ids))):
        raise RuntimeError("restart_selection_bank_identity_invalid")
    subject_banks = {}
    bank_subjects = {}
    for bank in selection["banks"]:
        workspace_id, subject_id = bank.get("workspace_id"), bank.get("subject_id")
        if (not isinstance(workspace_id, str) or not workspace_id
                or not isinstance(subject_id, str) or not subject_id
                or not isinstance(bank.get("sources"), list) or not bank["sources"]
                or not isinstance(bank.get("scopes"), list) or not bank["scopes"]):
            raise RuntimeError("restart_selection_invalid")
        bank_id = bank["bank_id"]
        if bank_id != subject_bank_id(workspace_id, subject_id):
            raise RuntimeError("restart_selection_subject_bank_identity_mismatch")
        if ((workspace_id, subject_id) in subject_banks and subject_banks[(workspace_id, subject_id)] != bank_id
                or bank_id in bank_subjects and bank_subjects[bank_id] != (workspace_id, subject_id)):
            raise RuntimeError("restart_selection_subject_bank_isolation_invalid")
        subject_banks[(workspace_id, subject_id)] = bank_id
        bank_subjects[bank_id] = (workspace_id, subject_id)
        roots = set()
        for scope in bank["scopes"]:
            root = scope.get("character_root_id")
            tags = scope.get("tags")
            cohort, positive, excluded = (scope.get("cohort_ids"), scope.get("positive_ids"),
                                          scope.get("exclusion_ids"))
            if (not isinstance(root, str) or not root or root in roots
                    or tags != [f"character:{root}", "kind:profile"]
                    or scope.get("tags_match") != "any_strict"
                    or not isinstance(cohort, list) or not cohort
                    or not isinstance(positive, list) or not positive
                    or not isinstance(excluded, list) or not excluded
                    or any(not isinstance(value, str) or not value for value in cohort + positive + excluded)
                    or len(set(cohort)) != len(cohort) or len(set(positive)) != len(positive)
                    or len(set(excluded)) != len(excluded)
                    or set(cohort) != set(positive) | set(excluded)
                    or set(positive) & set(excluded)):
                raise RuntimeError("restart_selection_scope_eligibility_invalid")
            roots.add(root)
        seen_sources = set()
        bank_fact_ids = set()
        for source in bank["sources"]:
            source_id = source.get("source_id")
            if not isinstance(source_id, str) or not source_id or source_id in seen_sources:
                raise RuntimeError("restart_selection_source_invalid")
            seen_sources.add(source_id)
            if not re_hash(source.get("original_text_sha256")) or (source.get("context_sha256") is not None and not re_hash(source.get("context_sha256"))):
                raise RuntimeError("restart_selection_source_hash_invalid")
            if not isinstance(source.get("content_hash"), str) or not source["content_hash"]:
                raise RuntimeError("restart_selection_content_hash_invalid")
            facts = source.get("facts")
            if not isinstance(facts, dict) or set(facts) != {"valid", "invalidated"}:
                raise RuntimeError("restart_selection_fact_state_invalid")
            ids = [item.get("id") for state in facts.values() for item in state]
            if not ids or any(not isinstance(item, str) for item in ids) or len(ids) != len(set(ids)):
                raise RuntimeError("restart_selection_fact_ids_invalid")
            bank_fact_ids.update(ids)
            if any(not re_hash(item.get("text_sha256")) for state in facts.values() for item in state):
                raise RuntimeError("restart_selection_fact_hash_invalid")
            invalidated_ids = {item["id"] for item in facts["invalidated"]}
            curation_ids = source.get("curation_ids")
            if (not isinstance(curation_ids, list) or len(curation_ids) != len(set(curation_ids))
                    or not set(curation_ids).issubset(invalidated_ids)):
                raise RuntimeError("restart_selection_curation_ids_invalid")
        if any(not set(scope["cohort_ids"]).issubset(bank_fact_ids) for scope in bank["scopes"]):
            raise RuntimeError("restart_selection_scope_fact_missing")
    return selection


def re_hash(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def re_sha(value) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def subject_bank_id(workspace_id: str, subject_id: str) -> str:
    identity = json.dumps([workspace_id, subject_id], separators=(",", ":")).encode()
    return "ade-probe-" + hashlib.sha256(identity).hexdigest()[:32]


def fact_projection(item: dict, text_hash: str, state: str) -> dict:
    tags = item.get("tags")
    sources = item.get("source_memory_ids", [])
    context = item.get("context")
    metadata = item.get("metadata", {})
    entities = item.get("entities", "")
    text_fields = ("date", "mentioned_at", "occurred_start", "occurred_end", "chunk_id",
                   "invalidation_reason", "invalidated_at", "edited_at", "updated_at",
                   "consolidated_at", "consolidation_failed_at")
    if (not isinstance(tags, list) or any(not isinstance(tag, str) or not tag for tag in tags)
            or not isinstance(sources, list) or any(not isinstance(value, str) for value in sources)
            or not isinstance(context, str)
            or not isinstance(metadata, dict)
            or not isinstance(entities, str)
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
        "entities_sha256": sha_text(entities), "tags": sorted(tags),
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
                    rows.append(fact_projection(item, digest, state))
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
    return {"schema": 1, "selection_sha256": hashlib.sha256(json.dumps(selection, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
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
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


if __name__ == "__main__":
    from .restart_readback_cli import main

    raise SystemExit(main())
