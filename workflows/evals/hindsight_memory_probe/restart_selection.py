"""Stdlib-only structural contract for frozen restart-readback selections."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def read_selection(path: Path) -> dict:
    try:
        selection = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, ValueError) as exc:
        raise RuntimeError("restart_selection_invalid") from exc
    validate_selection(selection)
    return selection


def validate_selection(selection: dict) -> None:
    if (not isinstance(selection, dict) or selection.get("schema") != 1
            or not isinstance(selection.get("banks"), list) or not selection["banks"]):
        raise RuntimeError("restart_selection_invalid")
    if (not valid_sha1(selection.get("release_sha"))
            or not valid_sha256(selection.get("registry_sha256"))
            or not valid_sha256(selection.get("before_epoch_sha256"))):
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
        scopes, sources, bank_id = bank.get("scopes"), bank.get("sources"), bank["bank_id"]
        if (not nonempty_string(workspace_id) or not nonempty_string(subject_id)
                or not isinstance(sources, list) or not sources
                or not isinstance(scopes, list) or not scopes):
            raise RuntimeError("restart_selection_invalid")
        subject = (workspace_id, subject_id)
        if ((subject in subject_banks and subject_banks[subject] != bank_id)
                or (bank_id in bank_subjects and bank_subjects[bank_id] != subject)):
            raise RuntimeError("restart_selection_subject_bank_isolation_invalid")
        subject_banks[subject], bank_subjects[bank_id] = bank_id, subject

        scope_roots = set()
        for scope in scopes:
            if not isinstance(scope, dict):
                raise RuntimeError("restart_selection_scope_eligibility_invalid")
            root = scope.get("character_root_id")
            tags, cohort = scope.get("tags"), scope.get("cohort_ids")
            positive, excluded = scope.get("positive_ids"), scope.get("exclusion_ids")
            if (not nonempty_string(root) or root in scope_roots
                    or not string_list(tags, nonempty=True)
                    or not nonempty_string(scope.get("tags_match"))
                    or not string_list(cohort, nonempty=True)
                    or not string_list(positive, nonempty=True)
                    or not string_list(excluded, nonempty=True)
                    or len(set(cohort)) != len(cohort)
                    or len(set(positive)) != len(positive)
                    or len(set(excluded)) != len(excluded)
                    or set(cohort) != set(positive) | set(excluded)
                    or set(positive) & set(excluded)):
                raise RuntimeError("restart_selection_scope_eligibility_invalid")
            scope_roots.add(root)

        seen_sources, bank_fact_ids = set(), set()
        for source in sources:
            if not isinstance(source, dict):
                raise RuntimeError("restart_selection_source_invalid")
            source_id = source.get("source_id")
            if not nonempty_string(source_id) or source_id in seen_sources:
                raise RuntimeError("restart_selection_source_invalid")
            seen_sources.add(source_id)
            if (not valid_sha256(source.get("original_text_sha256"))
                    or (source.get("context_sha256") is not None
                        and not valid_sha256(source.get("context_sha256")))):
                raise RuntimeError("restart_selection_source_hash_invalid")
            if not nonempty_string(source.get("content_hash")):
                raise RuntimeError("restart_selection_content_hash_invalid")
            facts = source.get("facts")
            if (not isinstance(facts, dict) or set(facts) != {"valid", "invalidated"}
                    or any(not isinstance(facts[state], list) for state in ("valid", "invalidated"))):
                raise RuntimeError("restart_selection_fact_state_invalid")
            ids = []
            for state in ("valid", "invalidated"):
                for fact in facts[state]:
                    if (not isinstance(fact, dict) or not nonempty_string(fact.get("id"))
                            or not valid_sha256(fact.get("text_sha256"))):
                        raise RuntimeError("restart_selection_fact_hash_invalid")
                    ids.append(fact["id"])
            if not ids or len(ids) != len(set(ids)):
                raise RuntimeError("restart_selection_fact_ids_invalid")
            bank_fact_ids.update(ids)
            invalidated_ids = {fact["id"] for fact in facts["invalidated"]}
            curation_ids = source.get("curation_ids")
            if (not string_list(curation_ids, nonempty=False)
                    or len(curation_ids) != len(set(curation_ids))
                    or not set(curation_ids).issubset(invalidated_ids)):
                raise RuntimeError("restart_selection_curation_ids_invalid")
        if any(not set(scope["cohort_ids"]).issubset(bank_fact_ids) for scope in scopes):
            raise RuntimeError("restart_selection_scope_fact_missing")


def hash_json(value: dict) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_json_key")
        value[key] = item
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_sha256(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def valid_sha1(value) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def nonempty_string(value) -> bool:
    return isinstance(value, str) and bool(value)


def string_list(value, *, nonempty: bool) -> bool:
    return (isinstance(value, list) and (bool(value) or not nonempty)
            and all(nonempty_string(item) for item in value))
