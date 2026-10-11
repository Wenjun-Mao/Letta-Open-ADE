"""Versioned adequate controls for the approved semantic diagnostic cases."""

from __future__ import annotations

import json
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent
PATH = WORKFLOW / "fixtures/semantic-diagnostic-controls-v1.json"


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_json_key")
        value[key] = item
    return value


def load(fixture: dict) -> dict:
    controls = json.loads(PATH.read_bytes(), object_pairs_hook=_unique_object)
    validate(controls, fixture)
    return controls


def validate(controls: dict, fixture: dict) -> None:
    """Bind each control's semantic source audit to the unchanged campaign fixture."""
    if (controls.get("contract") != "ade-hindsight-semantic-diagnostic-controls-v1"
            or controls.get("version") != "semantic-diagnostic-controls-v1"
            or set(controls.get("cases", {})) != {"q01", "q06", "q07"}):
        raise ValueError("semantic_diagnostic_controls_invalid")
    sources = {item["id"]: item for item in fixture["sources"]}
    expected_scopes = {
        "q01": ("subject_a", "root_other"),
        "q06": ("subject_b", "root_xiaotang"),
        "q07": ("subject_a", "root_xiaotang"),
    }
    expected_source_scopes = {
        "q01": {"s01": ("subject_a", "root_xiaotang"), "s03": ("subject_a", "root_xiaotang")},
        "q06": {"s09": ("subject_b", "root_xiaotang"), "s05": ("subject_a", "root_xiaotang")},
        "q07": {"s08": ("subject_a", "root_other"), "s06": ("subject_a", "root_xiaotang")},
    }
    expected_audit_roots = {
        "q01": {"source_character_root_id": "root_xiaotang"},
        "q06": {"source_character_root_id": "root_xiaotang"},
        "q07": {
            "portable_profile_source_character_root_id": "root_other",
            "hypothetical_source_character_root_id": "root_xiaotang",
        },
    }
    expected_source_metadata = {
        "q01": {
            "adequate_q01_profile_v1": {"speaker": "user", "subject_id": "subject_a"},
        },
        "q06": {
            "adequate_q06_profile_v1": {"speaker": "user", "subject_id": "subject_b"},
            "adequate_q06_naming_experience_v1": {
                "speaker": "user+assistant", "source_id": "s09",
                "source_timestamp": sources["s09"]["timestamp"],
                "subject_id": "subject_b", "character_root_id": "root_xiaotang",
                "definition_version": "xiaotang_v1",
            },
        },
        "q07": {
            "adequate_q07_commute_profile_v1": {"speaker": "user", "subject_id": "subject_a"},
            "adequate_q07_hypothetical_v1": {
                "speaker": "assistant", "source_id": "s06",
                "source_timestamp": sources["s06"]["timestamp"],
                "subject_id": "subject_a", "character_root_id": "root_xiaotang",
                "definition_version": "xiaotang_v1",
            },
        },
    }
    fixture_cases = {item["id"]: item for item in fixture["cases"]}
    for case_id, (subject, active_root) in expected_scopes.items():
        case = controls["cases"][case_id]
        audit = case.get("audit", {})
        campaign_case = fixture_cases[case_id]
        if ((audit.get("subject_id"), audit.get("active_character_root_id")) != (subject, active_root)
                or (campaign_case.get("subject"), campaign_case.get("root")) != (subject, active_root)
                or any(audit.get(key) != value for key, value in expected_audit_roots[case_id].items())):
            raise ValueError("semantic_diagnostic_scope_invalid")
        memories = case.get("memories")
        if not isinstance(memories, list) or not memories or not case.get("expected_distinctions"):
            raise ValueError("semantic_diagnostic_memory_invalid")
        ids = set()
        for memory in memories:
            if (not isinstance(memory, dict) or not isinstance(memory.get("text"), str)
                    or not memory["text"].strip() or memory.get("type") not in {"world", "experience", "observation"}
                    or not isinstance(memory.get("tags"), list) or not memory["tags"]
                    or not isinstance(memory.get("metadata", {}), dict)):
                raise ValueError("semantic_diagnostic_memory_invalid")
            if any(not isinstance(value, str) for value in memory.get("metadata", {}).values()):
                raise ValueError("semantic_diagnostic_memory_invalid")
            if memory.get("metadata", {}) != expected_source_metadata[case_id].get(memory["id"]):
                raise ValueError("semantic_diagnostic_memory_attribution_invalid")
            ids.add(memory["id"])
        if ids != set(expected_source_metadata[case_id]):
            raise ValueError("semantic_diagnostic_memory_attribution_invalid")
        if case_id in {"q01", "q07"}:
            portable_id = f"adequate_{case_id}_profile_v1" if case_id == "q01" else "adequate_q07_commute_profile_v1"
            portable = next(memory for memory in memories if memory["id"] == portable_id)
            if (portable.get("tags") != ["kind:profile"]
                    or any(key in portable for key in ("document_id", "mentioned_at", "context"))):
                raise ValueError("semantic_diagnostic_profile_attribution_invalid")
        if case_id == "q06":
            profile = next(memory for memory in memories if memory["id"] == "adequate_q06_profile_v1")
            experience = next(memory for memory in memories if memory["id"] == "adequate_q06_naming_experience_v1")
            if (profile.get("tags") != ["kind:profile"]
                    or experience.get("tags") != ["character:root_xiaotang"]
                    or "昨天" not in experience.get("text", "")
                    or sources["s09"]["timestamp"] not in experience.get("context", "")):
                raise ValueError("semantic_diagnostic_profile_attribution_invalid")
        source_ids = set()
        for key, value in audit.items():
            if key.endswith("source_ids") and isinstance(value, list):
                source_ids.update(value)
            elif key.endswith("source_id") and isinstance(value, str):
                source_ids.add(value)
        if source_ids != set(expected_source_scopes[case_id]):
            raise ValueError("semantic_diagnostic_source_scope_invalid")
        for source_id in source_ids:
            source = sources.get(source_id)
            if (source is None or (source["subject"], source["root"])
                    != expected_source_scopes[case_id].get(source_id)):
                raise ValueError("semantic_diagnostic_source_scope_invalid")
