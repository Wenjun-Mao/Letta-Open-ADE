"""Validate and seal the synthetic campaign before any upstream request."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

from .receipts import ReceiptStore

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = Path(__file__).resolve().parent
FIXTURE = WORKFLOW / "fixtures/campaign.json"
PERSONAS = ROOT / "content/personas/personas.jsonl"
NAMESPACE = uuid.UUID("3d30bf87-76ed-5a53-9a5b-5628d86ff8ca")
CONFIG_PATHS = [
    WORKFLOW / "config/pins.json", WORKFLOW / "config/sources.json",
    WORKFLOW / "config/model-profiles.json", WORKFLOW / "config/hindsight.env",
    WORKFLOW / "compose.yaml", WORKFLOW / "docker/python.Dockerfile",
    ROOT / "services/model-router/pyproject.toml",
    ROOT / "services/ade-api/pyproject.toml",
    ROOT / "workflows/pyproject.toml", ROOT / "pyproject.toml", ROOT / "uv.lock",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate_json_key")
        value[key] = item
    return value


def strict_json(data):
    return json.loads(data, object_pairs_hook=_unique_object)


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _feature_scope(workspace: str, subject: str, root: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m",
         "ade_api.features.agent_runtime.hindsight_evaluation", "scope",
         "--workspace-id", workspace, "--subject-id", subject,
         "--character-root-id", root],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    value = json.loads(result.stdout)
    if value.get("workspace_id") != workspace or value.get("subject_id") != subject:
        raise ValueError("feature_scope_mismatch")
    return value


def _persona() -> str:
    for line in PERSONAS.read_text(encoding="utf-8").splitlines():
        item = strict_json(line)
        if item.get("key") == "chat_linxiaotang":
            return item["content"]
    raise ValueError("authored_persona_missing")


def _source_content(source: dict) -> str:
    user = next(m["content"] for m in source["messages"] if m["role"] == "user")
    assistant = next(m["content"] for m in source["messages"] if m["role"] == "assistant")
    return f"用户：{user}\n林小棠（助手，已提交）：{assistant}"


def _bind_context(source: dict, by_id: dict[str, dict]) -> str | None:
    return _context_binding(source, by_id)[0]


def _context_binding(source: dict, by_id: dict[str, dict]) -> tuple[str | None, list[dict]]:
    refs = source.get("reference_context", [])
    if not refs:
        return None, []
    lines = [
        f"当前正文所属来源：{source['id']}。主体：{source['subject']}；角色根：{source['root']}；会话：{source['conversation']}。",
        "以下是同一会话中较早消息的原文片段，作为当前正文的指代背景；它们保留原来的时间和说话者，不是当前新陈述。",
    ]
    source_time = source["timestamp"]
    sealed_refs = []
    for ref in refs:
        prior = by_id.get(ref["source"])
        if not prior or ref["message"] not in {m["id"] for m in prior["messages"]}:
            raise ValueError("reference_source_missing")
        if any(prior[key] != source[key] for key in ("workspace", "subject", "root", "conversation")):
            raise ValueError("reference_scope_mismatch")
        if prior["timestamp"] >= source_time or prior["timestamp"] != ref["timestamp"]:
            raise ValueError("reference_not_historical")
        message = next(m for m in prior["messages"] if m["id"] == ref["message"])
        if message["role"] != ref["role"] or ref["role"] != "user" or ref["excerpt"] not in message["content"]:
            raise ValueError("reference_excerpt_mismatch")
        # This exact assertion prevents the unnecessary private game/code origin
        # from entering context on the profile fact.
        if ref["source"] == "s01" and ref["excerpt"] != "我喜欢茉莉奶茶，冰的、半糖。":
            raise ValueError("reference_context_too_broad")
        lines.append(
            f"来源 {ref['source']}；消息 {ref['message']}；时间 {ref['timestamp']}；说话者 {ref['role']}：\n{ref['excerpt']}"
        )
        sealed_refs.append({
            **ref,
            "source_sha256": sha(json.dumps(prior, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
            "message_sha256": sha(message["content"].encode()),
        })
    return "\n\n".join(lines), sealed_refs


def _validate_fixture(fixture: dict) -> None:
    if fixture.get("persona_key") != "chat_linxiaotang" or fixture.get("model_key") != "deepseek::deepseek-flash":
        raise ValueError("campaign_consumer_binding_invalid")
    expected = {
        **{f"s{i:02d}": ("subject_a", "root_xiaotang", "a_x_01", "xiaotang_v1") for i in range(1, 8)},
        "s08": ("subject_a", "root_other", "a_o_01", "other_v1"),
        "s09": ("subject_b", "root_xiaotang", "b_x_01", "xiaotang_v1"),
        "s10": ("subject_a", "root_xiaotang", "a_x_01", "xiaotang_v1"),
        "s11": ("subject_a", "root_xiaotang", "a_x_02", "xiaotang_v2"),
        "s12": ("subject_a", "root_xiaotang", "a_x_02", "xiaotang_v2"),
    }
    source_ids = [source.get("id") for source in fixture.get("sources", [])]
    if len(source_ids) != 12 or set(source_ids) != set(expected) or len(set(source_ids)) != len(source_ids):
        raise ValueError("campaign_source_ids_invalid")
    message_ids = []
    for source in fixture["sources"]:
        if tuple(source.get(key) for key in ("subject", "root", "conversation", "version")) != expected[source["id"]]:
            raise ValueError("campaign_source_scope_invalid")
        try:
            timestamp = datetime.fromisoformat(source["timestamp"].replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError("campaign_source_timestamp_invalid") from exc
        if timestamp.tzinfo is None or len(source.get("messages", [])) != 2:
            raise ValueError("campaign_source_attribution_invalid")
        roles = {message.get("role"): message.get("state") for message in source["messages"]}
        if roles != {"user": "accepted", "assistant": "committed"}:
            raise ValueError("campaign_source_attribution_invalid")
        for message in source["messages"]:
            if not message.get("id") or not message.get("content", "").strip():
                raise ValueError("campaign_message_invalid")
            message_ids.append(message["id"])
    if len(message_ids) != len(set(message_ids)):
        raise ValueError("campaign_message_ids_invalid")
    if len(fixture.get("cases", [])) != 8 or {case.get("id") for case in fixture["cases"]} != {f"q{i:02d}" for i in range(1, 9)}:
        raise ValueError("campaign_cases_invalid")
    q07 = next(case for case in fixture["cases"] if case["id"] == "q07")
    if q07.get("query_version") != "q07-v2" or not q07.get("original_query") or "之前说的去海边" not in q07.get("query", ""):
        raise ValueError("q07_query_version_invalid")
    readiness = fixture.get("readiness", {})
    try:
        ready_time = datetime.fromisoformat(readiness["timestamp"].replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("readiness_timestamp_invalid") from exc
    if ready_time.tzinfo is None or readiness.get("source_id") != "ready01":
        raise ValueError("readiness_source_invalid")


def build_manifest(workspace_id: str) -> dict:
    fixture_bytes = FIXTURE.read_bytes()
    fixture = strict_json(fixture_bytes)
    _validate_fixture(fixture)
    sources = fixture["sources"]
    by_id = {item["id"]: item for item in sources}
    persona = _persona()
    profile_path = WORKFLOW / "config/model-profiles.json"
    profile = strict_json(profile_path.read_text(encoding="utf-8"))[fixture["model_key"]]
    scopes = {}
    for source in sources:
        key = (source["subject"], source["root"])
        scopes.setdefault(key, _feature_scope(workspace_id, key[0], key[1]))
    frozen_sources = []
    for source in sources:
        context, sealed_references = _context_binding(source, by_id)
        document_content = _source_content(source)
        payload = {
            "async": True,
            "operation_id": str(uuid.uuid5(NAMESPACE, f"{workspace_id}:{source['subject']}:{source['id']}")),
            "items": [{
                "content": document_content,
                "timestamp": source["timestamp"],
                "context": context,
                "document_id": source["id"],
                "tags": [f"character:{source['root']}"],
                "observation_scopes": [[f"character:{source['root']}"]],
                "metadata": {
                    "source_id": source["id"], "speaker": "user+assistant",
                    "subject_id": source["subject"], "character_root_id": source["root"],
                    "conversation_id": source["conversation"], "definition_version": source["version"],
                },
            }],
        }
        payload_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        frozen_sources.append({
            **source,
            "workspace": workspace_id,
            "document_content": document_content,
            "source_sha256": sha(json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
            "document_content_sha256": sha(document_content.encode()),
            "reference_context": sealed_references,
            "message_sha256": {message["id"]: sha(message["content"].encode()) for message in source["messages"]},
            "rendered_context": context,
            "rendered_context_sha256": sha(context.encode()) if context is not None else None,
            "retain_payload": payload,
            "retain_payload_sha256": sha(payload_bytes),
            "retain_payload_utf8": payload_bytes.decode(),
        })
    readiness = fixture["readiness"]
    readiness_content = f"用户：{readiness['user']}\n林小棠（助手，已提交）：{readiness['assistant']}"
    readiness_payload = {
        "async": True,
        "operation_id": str(uuid.uuid5(NAMESPACE, f"{workspace_id}:subject_a:{readiness['source_id']}")),
        "items": [{
            "content": readiness_content, "timestamp": readiness["timestamp"],
            "document_id": readiness["source_id"],
            "tags": ["character:root_xiaotang"],
            "observation_scopes": [["character:root_xiaotang"]],
        }],
    }
    readiness_payload_bytes = json.dumps(readiness_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    try:
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
        if status.strip():
            raise ValueError("clean_commit_required_for_freeze")
        source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError("git_identity_unavailable") from exc
    config_hashes = {
        str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in CONFIG_PATHS
    }
    return {
        "contract": "ade-hindsight-campaign-manifest-v1",
        "source_sha": source_sha,
        "workspace_id": workspace_id,
        "fixture_sha256": sha(fixture_bytes),
        "source_suite_sha256": sha(json.dumps(sources, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
        "query_suite_sha256": sha(json.dumps(fixture["cases"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
        "persona_key": fixture["persona_key"],
        "persona": persona,
        "persona_sha256": sha(persona.encode()),
        "model_key": fixture["model_key"],
        "model_profile": profile,
        "model_profile_sha256": sha(json.dumps(profile, sort_keys=True, separators=(",", ":")).encode()),
        "pins": strict_json((WORKFLOW / "config/pins.json").read_text(encoding="utf-8")),
        "config_sha256": config_hashes,
        "scopes": {f"{subject}:{root}": value for (subject, root), value in scopes.items()},
        "sources": frozen_sources,
        "cases": fixture["cases"],
        "adequate_memories": fixture["adequate_memories"],
        "readiness": fixture["readiness"],
        "readiness_payload": readiness_payload,
        "readiness_payload_utf8": readiness_payload_bytes.decode(),
        "readiness_payload_sha256": sha(readiness_payload_bytes),
        "retry_policy": {"retain": "exact sealed body and original UUID only", "automatic_retries": 0},
        "timeouts_seconds": {"http": 120, "operation": 600},
    }


def validate_manifest(manifest: dict, *, expected_source_sha: str) -> None:
    """Rebind every frozen byte to current tracked inputs before any dispatch."""
    fixture_bytes = FIXTURE.read_bytes()
    fixture = strict_json(fixture_bytes)
    _validate_fixture(fixture)
    if manifest.get("contract") != "ade-hindsight-campaign-manifest-v1":
        raise ValueError("campaign_manifest_invalid")
    if manifest.get("source_sha") != expected_source_sha:
        raise ValueError("campaign_source_revision_mismatch")
    workspace = manifest.get("workspace_id")
    if not isinstance(workspace, str) or not workspace or len(workspace) > 128:
        raise ValueError("campaign_workspace_invalid")
    if manifest.get("fixture_sha256") != sha(fixture_bytes):
        raise ValueError("campaign_fixture_changed")
    if manifest.get("source_suite_sha256") != sha(canonical(fixture["sources"])):
        raise ValueError("campaign_sources_changed")
    if manifest.get("query_suite_sha256") != sha(canonical(fixture["cases"])) or manifest.get("cases") != fixture["cases"]:
        raise ValueError("campaign_queries_changed")
    persona = _persona()
    if manifest.get("persona_key") != fixture["persona_key"] or manifest.get("persona") != persona or manifest.get("persona_sha256") != sha(persona.encode()):
        raise ValueError("campaign_persona_changed")
    profile = strict_json((WORKFLOW / "config/model-profiles.json").read_text(encoding="utf-8"))[fixture["model_key"]]
    if manifest.get("model_key") != fixture["model_key"] or manifest.get("model_profile") != profile or manifest.get("model_profile_sha256") != sha(canonical(profile)):
        raise ValueError("campaign_model_profile_changed")
    pins = strict_json((WORKFLOW / "config/pins.json").read_text(encoding="utf-8"))
    if manifest.get("pins") != pins:
        raise ValueError("campaign_runtime_pins_changed")
    config_hashes = {str(path.relative_to(ROOT)): sha(path.read_bytes()) for path in CONFIG_PATHS}
    if manifest.get("config_sha256") != config_hashes:
        raise ValueError("campaign_configuration_changed")
    if manifest.get("adequate_memories") != fixture["adequate_memories"] or manifest.get("readiness") != fixture["readiness"]:
        raise ValueError("campaign_control_fixture_changed")
    by_id = {source["id"]: source for source in fixture["sources"]}
    sealed = manifest.get("sources")
    if not isinstance(sealed, list) or len(sealed) != len(by_id) or len({item.get("id") for item in sealed if isinstance(item, dict)}) != len(by_id):
        raise ValueError("campaign_source_manifest_invalid")
    expected_scopes = {}
    for source_id, source in by_id.items():
        key = (source["subject"], source["root"])
        bank = "ade-probe-" + hashlib.sha256(json.dumps([workspace, key[0]], separators=(",", ":")).encode()).hexdigest()[:32]
        expected_scopes[f"{key[0]}:{key[1]}"] = {
            "workspace_id": workspace, "subject_id": key[0], "character_root_id": key[1],
            "bank_id": bank, "tags": [f"character:{key[1]}", "kind:profile"], "tags_match": "any_strict",
        }
        item = next(candidate for candidate in sealed if candidate["id"] == source_id)
        context, refs = _context_binding(source, by_id)
        content = _source_content(source)
        payload = {
            "async": True,
            "operation_id": str(uuid.uuid5(NAMESPACE, f"{workspace}:{source['subject']}:{source_id}")),
            "items": [{
                "content": content, "timestamp": source["timestamp"], "context": context,
                "document_id": source_id, "tags": [f"character:{source['root']}"],
                "observation_scopes": [[f"character:{source['root']}"]],
                "metadata": {"source_id": source_id, "speaker": "user+assistant", "subject_id": source["subject"],
                             "character_root_id": source["root"], "conversation_id": source["conversation"],
                             "definition_version": source["version"]},
            }],
        }
        payload_bytes = canonical(payload)
        if (item.get("workspace") != workspace or item.get("messages") != source["messages"]
                or item.get("source_sha256") != sha(canonical(source))
                or item.get("document_content") != content or item.get("document_content_sha256") != sha(content.encode())
                or item.get("rendered_context") != context
                or item.get("rendered_context_sha256") != (sha(context.encode()) if context is not None else None)
                or item.get("reference_context") != refs
                or item.get("message_sha256") != {message["id"]: sha(message["content"].encode()) for message in source["messages"]}
                or item.get("retain_payload") != payload or item.get("retain_payload_utf8") != payload_bytes.decode()
                or item.get("retain_payload_sha256") != sha(payload_bytes)):
            raise ValueError("campaign_frozen_source_mismatch")
    if manifest.get("scopes") != expected_scopes:
        raise ValueError("campaign_scope_binding_changed")
    readiness = fixture["readiness"]
    ready_content = f"用户：{readiness['user']}\n林小棠（助手，已提交）：{readiness['assistant']}"
    ready_payload = {
        "async": True,
        "operation_id": str(uuid.uuid5(NAMESPACE, f"{workspace}:subject_a:{readiness['source_id']}")),
        "items": [{"content": ready_content, "timestamp": readiness["timestamp"], "document_id": readiness["source_id"],
                   "tags": ["character:root_xiaotang"], "observation_scopes": [["character:root_xiaotang"]]}],
    }
    ready_bytes = canonical(ready_payload)
    if (manifest.get("readiness_payload") != ready_payload
            or manifest.get("readiness_payload_utf8") != ready_bytes.decode()
            or manifest.get("readiness_payload_sha256") != sha(ready_bytes)):
        raise ValueError("campaign_readiness_payload_mismatch")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output_directory.exists():
        raise SystemExit("freeze_output_directory_must_be_new")
    manifest = build_manifest(args.workspace_id)
    store = ReceiptStore(args.output_directory)
    store.write("campaign-manifest.json", manifest)
    print(json.dumps({"status": "frozen", "workspace_id": args.workspace_id,
                      "manifest_sha256": sha(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()),
                      "sources": len(manifest["sources"]), "cases": len(manifest["cases"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
