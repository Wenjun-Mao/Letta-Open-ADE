import hashlib
import json

def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _selection():
    return {
        "schema": 1,
        "release_sha": "a" * 40,
        "registry_sha256": "b" * 64,
        "before_epoch_sha256": "c" * 64,
        "banks": [{
            "bank_id": "public-bank-id", "workspace_id": "workspace-a", "subject_id": "subject-a",
            "scopes": [{
                "character_root_id": "root-a", "tags": ["character:root-a", "kind:profile"],
                "tags_match": "any_strict", "cohort_ids": ["fact-a", "fact-b", "fact-c", "fact-d"],
                "positive_ids": ["fact-a", "fact-b"], "exclusion_ids": ["fact-c", "fact-d"],
            }],
            "sources": [{
                "source_id": "source-a", "original_text_sha256": _hash("source text"),
                "context_sha256": _hash("retained context"), "content_hash": "sha-content-a",
                "curation_ids": ["fact-d"],
                "facts": {"valid": [
                    {"id": "fact-a", "text_sha256": _hash("profile with char tag")},
                    {"id": "fact-b", "text_sha256": _hash("profile tag only")},
                    {"id": "fact-c", "text_sha256": _hash("cross root observation")},
                ], "invalidated": [{"id": "fact-d", "text_sha256": _hash("invalidated profile")} ]},
            }],
        }],
    }


def _rows(selection, *, vector="[0.25,0.75]"):
    bank = selection["banks"][0]
    return {
        "banks": [{"bank_id": bank["bank_id"]}],
        "documents": [{"id": "source-a", "bank_id": bank["bank_id"],
                       "original_text": "source text", "content_hash": "sha-content-a",
                       "retain_params": {"context": "retained context"}}],
        "chunks": [{"id": "chunk-a", "embedding": vector}],
        "memory_units": [
            {"id": "fact-a", "document_id": "source-a", "text": "profile with char tag",
             "bank_id": bank["bank_id"], "tags": ["character:root-a", "kind:profile"], "fact_type": "world",
             "source_memory_ids": ["source-memory-a"], "embedding": vector},
            {"id": "fact-b", "document_id": "source-a", "text": "profile tag only",
             "bank_id": bank["bank_id"], "tags": ["kind:profile"], "fact_type": "world", "embedding": vector},
            {"id": "fact-c", "document_id": "source-a", "text": "cross root observation",
             "bank_id": bank["bank_id"], "fact_type": "observation", "tags": ["character:root-a", "character:root-b"],
             "embedding": vector},
        ],
        "invalidated_memory_units": [{"id": "fact-d", "document_id": "source-a",
             "text": "invalidated profile", "bank_id": bank["bank_id"], "fact_type": "world",
             "tags": ["kind:profile"], "source_memory_ids": ["fact-a"], "embedding": vector}],
        "observation_history": [{"id": "observation-history-a", "source_memory_ids": ["source-memory-a"],
                                 "memory_unit_id": "fact-c"}], "entities": [],
        "unit_entities": [], "entity_cooccurrences": [], "memory_links": [],
        "schema_extensions": [{"schemas": [{"name": "public", "owner": "postgres"}],
                               "extensions": [{"name": "vector", "version": "0.8.6"}],
                               "alembic": [{"version_num": "frozen"}] }],
    }


def _snapshot(root, values):
    root.mkdir()
    entries = {}
    for name, rows in values.items():
        content = (json.dumps(rows[0], sort_keys=True, separators=(",", ":"))
                   if name == "schema_extensions" else
                   "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows))
        filename = "schema-extensions.json" if name == "schema_extensions" else name + ".jsonl"
        (root / filename).write_text(content, encoding="utf-8")
        payload = (root / filename).read_bytes()
        entries[name] = {"file": filename, "sha256": hashlib.sha256(payload).hexdigest(),
                         "bytes": len(payload)}
    scope_file = root / "scope-eligibility.json"
    scope_content = json.dumps({"status": "absent"}, sort_keys=True, separators=(",", ":"))
    scope_file.write_text(scope_content, encoding="utf-8")
    scope_bytes = scope_file.read_bytes()
    entries["scope_eligibility"] = {"file": scope_file.name,
                                    "sha256": hashlib.sha256(scope_bytes).hexdigest(),
                                    "bytes": len(scope_bytes)}
    return {"schema": 1, "database": "hindsight_probe", "tables": entries}
