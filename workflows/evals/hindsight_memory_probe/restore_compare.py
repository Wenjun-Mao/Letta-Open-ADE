"""Strict stdlib comparison of canonical PostgreSQL snapshots and frozen scopes."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from . import restart_selection
from .candidate_database import sha256_file


def _table_rows(snapshot: dict, root: Path) -> dict[str, list[dict]]:
    tables = snapshot.get("tables")
    if not isinstance(tables, dict) or not tables:
        raise RuntimeError("restore_snapshot_tables_missing")
    rows = {}
    for name, entry in sorted(tables.items()):
        if (not isinstance(name, str) or not name.replace("_", "").isalnum()
                or not isinstance(entry, dict) or not isinstance(entry.get("file"), str)
                or Path(entry["file"]).name != entry["file"]
                or not restart_selection.valid_sha256(entry.get("sha256"))):
            raise RuntimeError("restore_snapshot_entry_invalid")
        path = root / entry["file"]
        if not path.is_file() or sha256_file(path) != entry["sha256"]:
            raise RuntimeError("restore_snapshot_file_hash_mismatch")
        content = path.read_bytes()
        if len(content) != entry.get("bytes"):
            raise RuntimeError("restore_snapshot_file_size_mismatch")
        if name == "scope_eligibility":
            try:
                evidence = json.loads(content)
            except (UnicodeDecodeError, ValueError) as exc:
                raise RuntimeError("restore_scope_evidence_invalid") from exc
            if not isinstance(evidence, dict) or evidence.get("status") not in {
                    "absent", "public_readback_bound", "frozen_selection_without_restart_proof"}:
                raise RuntimeError("restore_scope_evidence_invalid")
            required_hashes = {
                "public_readback_bound": ("selection_sha256", "selection_file_sha256",
                    "restart_readback_sha256", "before_file_sha256", "before_snapshot_sha256",
                    "after_file_sha256", "after_snapshot_sha256"),
                "frozen_selection_without_restart_proof": ("selection_file_sha256",),
                "absent": (),
            }[evidence["status"]]
            if any(not restart_selection.valid_sha256(evidence.get(key)) for key in required_hashes):
                raise RuntimeError("restore_scope_evidence_invalid")
            continue
        if name == "schema_extensions":
            try:
                rows[name] = [json.loads(content)]
            except (UnicodeDecodeError, ValueError) as exc:
                raise RuntimeError("restore_schema_snapshot_invalid") from exc
            continue
        try:
            decoded = content.decode("utf-8")
            values = [json.loads(line) for line in decoded.splitlines()]
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError("restore_table_snapshot_invalid") from exc
        if any(not isinstance(row, dict) for row in values):
            raise RuntimeError("restore_table_row_invalid")
        rows[name] = values
    return rows


def _scope_rows(rows: dict[str, list[dict]], selection: dict) -> list[dict]:
    valid_rows = rows.get("memory_units")
    invalid_rows = rows.get("invalidated_memory_units")
    if valid_rows is None or invalid_rows is None:
        raise RuntimeError("restore_scope_tables_missing")
    states = {"valid": {}, "invalidated": {}}
    for state, table_rows in (("valid", valid_rows), ("invalidated", invalid_rows)):
        for row in table_rows:
            identifier = row.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in states[state]:
                raise RuntimeError("restore_scope_memory_identity_invalid")
            states[state][identifier] = row
    if set(states["valid"]) & set(states["invalidated"]):
        raise RuntimeError("restore_scope_memory_in_both_states")

    projections = []
    for bank in selection["banks"]:
        scopes = []
        for scope in bank["scopes"]:
            if scope["tags_match"] != "any_strict":
                raise RuntimeError("restore_scope_match_rule_unsupported")
            positive = set()
            for identifier in scope["cohort_ids"]:
                valid = states["valid"].get(identifier)
                invalidated = states["invalidated"].get(identifier)
                if (valid is None) == (invalidated is None):
                    raise RuntimeError("restore_scope_cohort_membership_invalid")
                row = valid or invalidated
                tags = row.get("tags")
                fact_type = row.get("fact_type")
                if (not isinstance(tags, list)
                        or any(not isinstance(tag, str) or not tag for tag in tags)
                        or not isinstance(fact_type, str)):
                    raise RuntimeError("restore_scope_tags_invalid")
                tag_overlap = bool(set(scope["tags"]) & set(tags))
                char_tag = f"character:{scope['character_root_id']}"
                observation_local = (
                    fact_type != "observation"
                    or {tag for tag in tags if tag.startswith("character:")} == {char_tag}
                )
                if valid is not None and tag_overlap and observation_local:
                    positive.add(identifier)
            expected_positive = set(scope["positive_ids"])
            expected_excluded = set(scope["exclusion_ids"])
            excluded = set(scope["cohort_ids"]) - positive
            scopes.append({
                "character_root_id": scope["character_root_id"],
                "tags": list(scope["tags"]), "tags_match": scope["tags_match"],
                "cohort_ids": sorted(scope["cohort_ids"]),
                "positive_ids": sorted(positive), "exclusion_ids": sorted(excluded),
                "expected_positive_ids": sorted(expected_positive),
                "expected_exclusion_ids": sorted(expected_excluded),
                "eligibility_matches": positive == expected_positive and excluded == expected_excluded,
            })
        projections.append({"bank_id": bank["bank_id"], "workspace_id": bank["workspace_id"],
                            "subject_id": bank["subject_id"], "scopes": scopes})
    return projections


def _selected_state(rows: dict[str, list[dict]], selection: dict) -> dict:
    required = {"banks", "documents", "chunks", "memory_units", "invalidated_memory_units",
                "observation_history", "entities", "unit_entities",
                "entity_cooccurrences", "memory_links", "schema_extensions"}
    if not required.issubset(rows):
        raise RuntimeError("restore_snapshot_required_table_missing")
    documents = {(row.get("bank_id"), row.get("id")): row for row in rows["documents"]}
    bank_ids = {row.get("bank_id") for row in rows["banks"]}
    valid = {row.get("id"): row for row in rows["memory_units"]}
    invalid = {row.get("id"): row for row in rows["invalidated_memory_units"]}
    for bank in selection["banks"]:
        if bank["bank_id"] not in bank_ids:
            raise RuntimeError("restore_selected_bank_missing")
        for source in bank["sources"]:
            document = documents.get((bank["bank_id"], source["source_id"]))
            if document is None:
                raise RuntimeError("restore_selected_document_missing")
            original_text = document.get("original_text")
            retain_params = document.get("retain_params")
            context = retain_params.get("context") if isinstance(retain_params, dict) else None
            if (document.get("bank_id") != bank["bank_id"]
                    or not isinstance(original_text, str)
                    or hashlib.sha256(original_text.encode("utf-8")).hexdigest() != source["original_text_sha256"]
                    or document.get("content_hash") != source["content_hash"]
                    or (None if context is None else hashlib.sha256(context.encode("utf-8")).hexdigest()) != source["context_sha256"]):
                raise RuntimeError("restore_selected_source_hash_mismatch")
            for state in ("valid", "invalidated"):
                index = valid if state == "valid" else invalid
                other = invalid if state == "valid" else valid
                for fact in source["facts"][state]:
                    item = index.get(fact["id"])
                    if item is None or fact["id"] in other:
                        raise RuntimeError("restore_selected_fact_state_missing")
                    if item.get("document_id") != source["source_id"]:
                        raise RuntimeError("restore_selected_fact_source_mismatch")
                    if item.get("bank_id") != bank["bank_id"]:
                        raise RuntimeError("restore_selected_fact_bank_mismatch")
                    text = item.get("text")
                    if not isinstance(text, str):
                        raise RuntimeError("restore_selected_fact_text_invalid")
                    # The public frozen contract stores SHA256(text), not a lossy projection.
                    if hashlib.sha256(text.encode("utf-8")).hexdigest() != fact["text_sha256"]:
                        raise RuntimeError("restore_selected_fact_text_hash_mismatch")
                for curation_id in source["curation_ids"]:
                    if curation_id not in invalid or curation_id in valid:
                        raise RuntimeError("restore_selected_curation_state_mismatch")
    return _scope_rows(rows, selection)


def compare(original: dict, original_root: Path, restored: dict, restored_root: Path,
            selection: dict) -> dict:
    restart_selection.validate_selection(selection)
    before = _table_rows(original, original_root)
    after = _table_rows(restored, restored_root)
    scope_entry = original.get("tables", {}).get("scope_eligibility")
    if not isinstance(scope_entry, dict):
        raise RuntimeError("restore_scope_evidence_missing")
    scope_evidence = json.loads((original_root / scope_entry["file"]).read_text(encoding="utf-8"))
    scope_evidence_hash = scope_entry["sha256"]
    before_scope = _selected_state(before, selection)
    after_scope = _selected_state(after, selection)
    mismatch = []
    for table in sorted(set(before) | set(after)):
        left, right = before.get(table), after.get(table)
        if left is None or right is None or left != right:
            mismatch.append({"table": table, "before_rows": None if left is None else len(left),
                             "after_rows": None if right is None else len(right)})
    scope_matches = before_scope == after_scope
    scope_valid = all(scope["eligibility_matches"] for bank in before_scope for scope in bank["scopes"])
    scope_valid = scope_valid and all(scope["eligibility_matches"] for bank in after_scope for scope in bank["scopes"])
    return {
        "schema": 1,
        "status": "completed" if not mismatch and scope_matches and scope_valid else "mismatch",
        "claim": "logical_persisted_state_restore_only",
        "tables_compared": sorted(set(before) | set(after)),
        "table_counts": {name: {"before": len(before[name]), "after": len(after[name])}
                         for name in sorted(set(before) & set(after))},
        "scope_evidence": scope_evidence,
        "scope_evidence_sha256": scope_evidence_hash,
        "table_mismatches": mismatch,
        "scope_before": before_scope,
        "scope_after": after_scope,
        "scope_matches": scope_matches and scope_valid,
        "compared_categories": ["schema_extensions_alembic", "banks", "documents", "chunks",
                                "valid_facts_observations", "invalidated_facts", "source_history",
                                "entities", "links", "vector_rows", "frozen_scope_membership"],
    }
