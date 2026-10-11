"""Frozen Hindsight ingestion, curation, readback and Character replay driver."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from . import bank_profile
from .driver_support import HindsightHTTP, NamedReceipt, feature_scope, set_phase, sha
from .freeze import strict_json, validate_manifest
from .receipts import ReceiptStore

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = Path(__file__).resolve().parent
FEATURE = "ade_api.features.agent_runtime.hindsight_evaluation"


class Campaign:
    def __init__(self, manifest: dict, output: Path, hindsight: HindsightHTTP):
        self.manifest, self.output, self.http = manifest, output, hindsight
        self.store = ReceiptStore(output)
        self.prefix_count = 0
        self.sources = {source["id"]: source for source in manifest["sources"]}
        self.workspace = manifest["workspace_id"]

    def receipt(self, label):
        self.prefix_count += 1
        return NamedReceipt(self.store, f"{self.prefix_count:04d}-{label}")

    def phase(self, phase, operation_id):
        marker = set_phase(self.output, phase, operation_id)
        self.store.write(f"phase-{self.prefix_count + 1:04d}-{phase}-{operation_id}.json", marker)
        return marker

    def bank(self, subject, root):
        return feature_scope(self.workspace, subject, root)["bank_id"]

    async def configure_bank(self, subject, root):
        scope = feature_scope(self.workspace, subject, root)
        bank_id = scope["bank_id"]
        # Keep extraction instructions in a versioned tracked contract so each
        # fresh candidate binds the precise memory-side change independently.
        config_contract = bank_profile.load_config()
        create = bank_profile.create_payload(config_contract)
        update = bank_profile.update_payload(config_contract)
        receipt = self.receipt(f"configure-{subject}-{root}")
        await self.http.request("PUT", f"/v1/default/banks/{quote(bank_id, safe='')}", body=create, receipt=receipt)
        await self.http.request("PATCH", f"/v1/default/banks/{quote(bank_id, safe='')}/config", body={"updates": update}, receipt=receipt)
        readback = await self.http.request("GET", f"/v1/default/banks/{quote(bank_id, safe='')}/config")
        config = readback.get("config")
        if not isinstance(config, dict):
            raise RuntimeError("bank_config_readback_mismatch")
        expected = {
            "enable_auto_consolidation": config_contract["enable_auto_consolidation"],
            **create,
            "entity_labels": config_contract["entity_labels"],
        }
        projection = bank_profile.verify_readback(config, expected)
        receipt.write("config-readback", {
            "bank_id": bank_id,
            "profile_config_version": config_contract["version"],
            "profile_config_sha256": sha(bank_profile.CONFIG_PATH.read_bytes()),
            **projection,
        })
        return bank_id

    async def retain(self, source_id: str, *, exact_retry=False):
        source = self.sources[source_id]
        bank_id = self.bank(source["subject"], source["root"])
        if not exact_retry:
            await self.configure_bank(source["subject"], source["root"])
        payload = source["retain_payload"]
        if sha(source["retain_payload_utf8"].encode()) != source["retain_payload_sha256"]:
            raise RuntimeError("frozen_retain_payload_corrupt")
        receipt = self.receipt(f"retain-{source_id}-{'retry' if exact_retry else 'initial'}")
        receipt.write("frozen-request", {
            "source_id": source_id, "operation_id": payload["operation_id"],
            "payload_sha256": source["retain_payload_sha256"], "payload": payload,
        })
        self.phase("retain", payload["operation_id"])
        raw_body = source["retain_payload_utf8"].encode("utf-8")
        if json.loads(raw_body) != payload:
            raise RuntimeError("frozen_retain_payload_mismatch")
        response = await self.http.request("POST", f"/v1/default/banks/{quote(bank_id, safe='')}/memories", body=payload, raw_body=raw_body, receipt=receipt)
        operation_ids = response.get("operation_ids") or ([response["operation_id"]] if response.get("operation_id") else [])
        if not isinstance(operation_ids, list) or len(operation_ids) != 1 or operation_ids[0] != payload["operation_id"]:
            raise RuntimeError("retain_operation_identity_mismatch")
        receipt.write("submit-response", {key: response.get(key) for key in ("success", "bank_id", "items_count", "async", "operation_id", "operation_ids")})
        await self.http.operation(bank_id, operation_ids[0], receipt)
        await self.read_document(bank_id, source, receipt)
        receipt.write("memory-readback", await self.memories(bank_id, source_id, "valid"))

    async def read_document(self, bank_id: str, source: dict, receipt: NamedReceipt):
        document = await self.http.request("GET", f"/v1/default/banks/{quote(bank_id, safe='')}/documents/{quote(source['id'], safe='')}")
        if document.get("original_text") != source["document_content"]:
            raise RuntimeError("document_original_text_mismatch")
        expected_scopes = [[f"character:{source['root']}"]]
        if document.get("tags") != [f"character:{source['root']}"]:
            raise RuntimeError("document_visibility_tags_mismatch")
        if document.get("observation_scopes") != expected_scopes:
            raise RuntimeError("document_observation_scope_mismatch")
        params = document.get("retain_params")
        expected_context = source["rendered_context"]
        if not isinstance(params, dict) or params.get("context") != expected_context:
            raise RuntimeError("document_retain_context_mismatch")
        receipt.write("document-readback", {
            "id": document.get("id"), "original_text": document.get("original_text"),
            "original_text_sha256": sha(str(document.get("original_text", "")).encode()),
            "content_hash": document.get("content_hash"),
            "retain_params": params, "document_tags": document.get("tags"),
            "memory_unit_count": document.get("memory_unit_count"),
        })

    async def pages(self, bank_id, path, key, *, params=None):
        rows, offset, total = [], 0, None
        while total is None or offset < total:
            query = {**(params or {}), "limit": 100, "offset": offset}
            page = await self.http.request("GET", path, params=query)
            items = page.get(key)
            if not isinstance(items, list) or not isinstance(page.get("total"), int) or page.get("limit") != 100 or page.get("offset") != offset:
                raise RuntimeError("pagination_shape_invalid")
            if total is None:
                total = page["total"]
            elif total != page["total"]:
                raise RuntimeError("pagination_total_changed")
            expected_count = min(page["limit"], max(0, total - offset))
            if len(items) != expected_count:
                raise RuntimeError("pagination_incomplete")
            rows.extend(items)
            if not items and offset < total:
                raise RuntimeError("pagination_empty_before_total")
            offset += page["limit"]
        return rows

    async def memories(self, bank_id, source_id=None, state="valid"):
        params = {"state": state}
        if source_id:
            params["document_id"] = source_id
        return await self.pages(bank_id, f"/v1/default/banks/{quote(bank_id, safe='')}/memories/list", "items", params=params)

    async def consolidate(self, subject, root):
        bank_id = self.bank(subject, root)
        operation_id = f"consolidate-{subject}-{root}-{self.prefix_count + 1}"
        receipt = self.receipt(f"consolidate-{subject}-{root}")
        body = {"observation_scopes": [[f"character:{root}"]]}
        self.phase("consolidation", operation_id)
        response = await self.http.request("POST", f"/v1/default/banks/{quote(bank_id, safe='')}/consolidate", body=body, receipt=receipt)
        if not isinstance(response.get("operation_id"), str):
            raise RuntimeError("consolidation_operation_missing")
        receipt.write("consolidation-response", {"operation_id": response["operation_id"], "deduplicated": response.get("deduplicated")})
        await self.http.operation(bank_id, response["operation_id"], receipt)
        receipt.write("memory-readback", await self.memories(bank_id, state="valid"))
        return bank_id

    async def invalidate_s10(self):
        bank_id = self.bank("subject_a", "root_xiaotang")
        receipt = self.receipt("invalidate-s10")
        valid = await self.memories(bank_id, "s10", "valid")
        raw = [item for item in valid if item.get("fact_type") in {"world", "experience"} and "character:root_xiaotang" in item.get("tags", [])]
        if not raw:
            raise RuntimeError("s10_selected_raw_fact_missing")
        raw_ids = {item["id"] for item in raw}
        valid_before = await self.memories(bank_id, state="valid")
        derived = [item for item in valid_before if item.get("fact_type") == "observation" and raw_ids.intersection(item.get("source_memory_ids", []))]
        receipt.write("before", {"raw_world_experience": raw, "derived_observations": derived})
        # The pinned operator curation operation is PATCH state=invalidated. Never
        # mutate observations directly; record their independent derived state.
        for item in raw:
            await self.http.request("PATCH", f"/v1/default/banks/{quote(bank_id, safe='')}/memories/{quote(item['id'], safe='')}", body={"state": "invalidated", "reason": "P0 synthetic curation checkpoint rooted in s10"}, receipt=receipt)
        active_after = await self.memories(bank_id, "s10", "valid")
        archive_after = await self.memories(bank_id, "s10", "invalidated")
        active_bank = await self.memories(bank_id, state="valid")
        invalidated_bank = await self.memories(bank_id, state="invalidated")
        derived_after = [item for item in active_bank if item.get("fact_type") == "observation" and raw_ids.intersection(item.get("source_memory_ids", []))]
        archived_ids = {item.get("id") for item in invalidated_bank}
        if not raw_ids.issubset(archived_ids):
            raise RuntimeError("s10_invalidation_archive_incomplete")
        receipt.write("after", {"selected_raw_ids": sorted(raw_ids), "valid_source_count": len(active_after), "invalidated_raw": [x for x in archive_after if x.get("id") in raw_ids], "derived_observations_after": derived_after, "all_valid_facts_and_observations": active_bank, "all_invalidated_facts": invalidated_bank})
        lineage = {"selected_raw_ids": sorted(raw_ids), "bank_id": bank_id, "source_id": "s10"}
        self.store.write("s10-curation-lineage.json", lineage)
        if raw_ids.intersection(x.get("id") for x in active_after):
            raise RuntimeError("s10_invalidation_not_effective")

    def original_s10_ids(self):
        lineage_path = self.output.parent / "invalidate-s10" / "s10-curation-lineage.json"
        try:
            lineage = strict_json(lineage_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError("s10_curation_lineage_missing") from exc
        ids = lineage.get("selected_raw_ids")
        if (lineage.get("source_id") != "s10" or not isinstance(ids, list)
                or not ids or any(not isinstance(item, str) for item in ids)
                or len(ids) != len(set(ids))):
            raise RuntimeError("s10_curation_lineage_invalid")
        return set(ids)

    async def record_curation_state(self, label):
        bank_id = self.bank("subject_a", "root_xiaotang")
        receipt = self.receipt(label)
        valid = await self.memories(bank_id, state="valid")
        invalidated = await self.memories(bank_id, state="invalidated")
        original_ids = self.original_s10_ids()
        active_ids = {item.get("id") for item in valid}
        present_invalidated = {item.get("id") for item in invalidated}
        missing_archived = original_ids - present_invalidated
        resurrected = original_ids & active_ids
        receipt.write("curation-state", {
            "original_s10_selected_ids": sorted(original_ids),
            "same_ids_still_valid": sorted(resurrected),
            "missing_from_invalidated": sorted(missing_archived),
            "all_valid_facts_and_observations": valid,
            "all_invalidated_facts": invalidated,
        })
        if missing_archived:
            raise RuntimeError("s10_curation_archive_incomplete")
        if resurrected:
            raise RuntimeError("s10_original_fact_reactivated")

    async def record_s12_provenance(self):
        bank_id = self.bank("subject_a", "root_xiaotang")
        receipt = self.receipt("s12-provenance")
        invalidated = await self.memories(bank_id, state="invalidated")
        valid_all = await self.memories(bank_id, state="valid")
        new_source = await self.memories(bank_id, "s12", "valid")
        original = [item for item in invalidated if item.get("fact_type") in {"world", "experience"}]
        new_raw = [item for item in new_source if item.get("fact_type") in {"world", "experience"}]
        by_text = {}
        for item in original:
            by_text.setdefault(item.get("text"), []).append(item.get("id"))
        reextract_matches = [
            {"new_s12_fact_id": item.get("id"), "matching_invalidated_s10_fact_ids": by_text[item.get("text")],
             "interpretation": "distinct_new_source_fact_or_duplicate_text; not original-fact reactivation"}
            for item in new_raw if item.get("text") in by_text
        ]
        invalidated_ids = self.original_s10_ids()
        original = [item for item in invalidated if item.get("id") in invalidated_ids]
        missing_archived = invalidated_ids - {item.get("id") for item in invalidated}
        active_ids = {item.get("id") for item in valid_all}
        receipt.write("source-provenance", {
            "invalidated_s10_fact_ids": sorted(invalidated_ids),
            "all_valid_facts_and_observations": valid_all,
            "all_invalidated_facts": invalidated,
            "valid_s12_raw_facts": new_raw,
            "s12_text_matches_of_invalidated_s10": reextract_matches,
            "original_fact_reactivation_ids": sorted(invalidated_ids & active_ids),
            "s12_observations": [item for item in new_source if item.get("fact_type") == "observation"],
            "missing_from_invalidated": sorted(missing_archived),
        })
        if missing_archived:
            raise RuntimeError("s10_curation_archive_incomplete")
        if invalidated_ids & active_ids:
            raise RuntimeError("historical_quote_reactivated_invalidated_fact")

    async def replay_case(self, case: dict, *, checkpoint: str, arms=None):
        arms = arms or ["hindsight", "empty"] + (["adequate"] if case.get("adequate") else [])
        workspace, subject, root = self.workspace, case["subject"], case["root"]
        scope = feature_scope(workspace, subject, root)
        input_value = {
            "contract": "ade-hindsight-character-evaluation-v1", "synthetic": True,
            "case_id": f"{case['id']}-{checkpoint}", "scope": {"workspace_id": workspace, "subject_id": subject, "character_root_id": root},
            "model_key": self.manifest["model_key"], "persona": self.manifest["persona"],
            "dialogue": [{"role": "user", "content": case["query"]}], "query": case["query"],
            "query_timestamp": "2026-10-03T12:00:00Z", "arms": arms,
        }
        if case["id"] == "q01" and "hindsight" in arms:
            input_value["excluded_memory_terms"] = ["雨巷接龙", "纸船靠岸"]
        if "adequate" in arms:
            memory = dict(self.manifest["adequate_memories"][case["adequate"]])
            memory.setdefault("id", case["adequate"])
            memory["tags"] = [f"character:{root}"] + (["kind:profile"] if "kind:profile" in memory.get("tags", []) else [])
            input_value["adequate_memories"] = [memory]
        label = f"{case['id']}-{checkpoint}-{int(time.time_ns())}"
        capture_dir = self.output / "character" / label
        capture_dir.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        input_path = self.output / f"{label}.input.json"
        self.store.write(input_path.name, input_value)
        self.phase("recall", label + "-recall")
        env = os.environ.copy()
        env.setdefault("ADE_EVAL_PHASE_FILE", str(self.output / "phase.json"))
        subprocess.run([sys.executable, "-m", FEATURE, "run", "--input", str(input_path), "--output-directory", str(capture_dir)], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        return {"case_id": case["id"], "checkpoint": checkpoint, "arms": arms, "input_sha256": sha(json.dumps(input_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()), "scope": scope}

    async def readiness(self):
        ready = self.manifest["readiness"]
        workspace = self.workspace + "_ready"
        scope = feature_scope(workspace, "subject_a", "root_xiaotang")
        bank_id = scope["bank_id"]
        # Readiness gets a separate disposable bank and one source only.
        receipt = self.receipt("readiness-bank")
        await self.http.request("PUT", f"/v1/default/banks/{quote(bank_id, safe='')}", body={"retain_mission": "Extract the explicit test-container name as an attributed profile fact.", "enable_observations": True}, receipt=receipt)
        await self.http.request("PATCH", f"/v1/default/banks/{quote(bank_id, safe='')}/config", body={"updates": {"enable_auto_consolidation": False}}, receipt=receipt)
        readiness_config = await self.http.request("GET", f"/v1/default/banks/{quote(bank_id, safe='')}/config")
        if readiness_config.get("config", {}).get("enable_auto_consolidation") is not False:
            raise RuntimeError("readiness_auto_consolidation_not_disabled")
        payload = self.manifest["readiness_payload"]
        op = payload["operation_id"]
        content = payload["items"][0]["content"]
        delivery = self.receipt("readiness-retain")
        self.phase("retain", op)
        frozen_ready = self.manifest["readiness_payload"]
        frozen_ready_bytes = self.manifest["readiness_payload_utf8"].encode("utf-8")
        if (sha(frozen_ready_bytes) != self.manifest["readiness_payload_sha256"]
                or json.loads(frozen_ready_bytes) != frozen_ready or frozen_ready != payload):
            raise RuntimeError("frozen_readiness_payload_mismatch")
        submitted = await self.http.request("POST", f"/v1/default/banks/{quote(bank_id, safe='')}/memories", body=payload, raw_body=frozen_ready_bytes, receipt=delivery)
        await self.http.operation(bank_id, submitted["operation_id"], delivery)
        await self.read_document(bank_id, {"id":ready["source_id"],"root":"root_xiaotang","document_content":content,"rendered_context":None}, delivery)
        case_input = {
            "contract": "ade-hindsight-character-evaluation-v1", "synthetic": True, "case_id": "readiness-ready01",
            "scope": {"workspace_id": workspace, "subject_id":"subject_a", "character_root_id":"root_xiaotang"},
            "model_key": self.manifest["model_key"], "persona": self.manifest["persona"],
            "dialogue": [{"role":"user","content":ready["query"]}], "query":ready["query"],
            "query_timestamp":"2026-10-01T09:00:00Z", "arms":["hindsight"],
        }
        input_path = self.output / "readiness.input.json"
        self.store.write(input_path.name, case_input)
        capture_dir = self.output / "readiness-feature"
        env = os.environ.copy()
        env.setdefault("ADE_EVAL_PHASE_FILE", str(self.output / "phase.json"))
        subprocess.run([sys.executable,"-m",FEATURE,"recall","--input",str(input_path),"--output-directory",str(capture_dir)], cwd=ROOT, env=env, check=True, capture_output=True, text=True)
        recall_receipt = json.loads((capture_dir / "hindsight.context.json").read_text(encoding="utf-8"))
        if not any("银杏七号" in item.get("text", "") and "character:root_xiaotang" in item.get("tags", []) for item in recall_receipt.get("memories", [])):
            raise RuntimeError("readiness_expected_fact_not_recalled")
        trace = json.loads((capture_dir / "hindsight.recall-trace.json").read_text(encoding="utf-8"))
        embedding = trace.get("query", {}).get("query_embedding") if isinstance(trace.get("query"), dict) else None
        if not isinstance(embedding, list) or len(embedding) != int(self.manifest["pins"]["embedding_dimensions"]):
            raise RuntimeError("readiness_embedding_dimensions_mismatch")
        return {"status":"readiness_recall_completed","scope":scope}


async def run(args):
    manifest = strict_json(args.manifest.read_text(encoding="utf-8"))
    source_sha = os.environ.get("ADE_EVAL_SOURCE_SHA")
    if source_sha is None:
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)
        if status.strip():
            raise RuntimeError("clean_source_checkout_required")
        source_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not isinstance(source_sha, str) or len(source_sha) != 40 or any(char not in "0123456789abcdef" for char in source_sha.lower()):
        raise RuntimeError("candidate_source_identity_invalid")
    validate_manifest(manifest, expected_source_sha=source_sha)
    async with httpx.AsyncClient(follow_redirects=False) as client:
        api = HindsightHTTP(client, os.environ.get("ADE_EVAL_HINDSIGHT_BASE_URL", ""), os.environ.get("ADE_EVAL_HINDSIGHT_API_KEY", ""))
        campaign = Campaign(manifest, args.output_directory, api)
        summaries = []
        if args.stage == "readiness":
            summaries.append(await campaign.readiness())
        elif args.stage == "initial-retain-a":
            for source in ("s01", "s02", "s03", "s04", "s05"):
                await campaign.retain(source)
        elif args.stage == "initial-retain-b":
            for source in ("s06", "s07", "s08", "s09", "s10"):
                await campaign.retain(source)
        elif args.stage in {"initial-compare-a", "initial-compare-b"}:
            case_ids = {"initial-compare-a": {"q01", "q02", "q03", "q04"},
                        "initial-compare-b": {"q05", "q06", "q07", "q08"}}[args.stage]
            for case in manifest["cases"]:
                if case["id"] in case_ids:
                    summaries.append(await campaign.replay_case(case, checkpoint="initial"))
        elif args.stage == "consolidate":
            seen = set()
            for source in manifest["sources"][:10]:
                key = (source["subject"], source["root"])
                if key not in seen:
                    await campaign.consolidate(*key)
                    seen.add(key)
            for case_id in ("q01", "q06", "q07"):
                case = next(c for c in manifest["cases"] if c["id"] == case_id)
                summaries.append(await campaign.replay_case(case, checkpoint="post-consolidation", arms=["hindsight", "empty"]))
        elif args.stage == "version-archive":
            campaign.store.write("lifecycle-archive-marker.json", {"conversation":"a_x_01","archived":True,"qualification":"fixture-only; Studio archive path not exercised"})
            case = next(c for c in manifest["cases"] if c["id"] == "q05")
            summaries.append(await campaign.replay_case(case, checkpoint="archive-version-marker", arms=["hindsight", "empty"]))
        elif args.stage == "invalidate-s10":
            await campaign.invalidate_s10()
            case = next(c for c in manifest["cases"] if c["id"] == "q08")
            summaries.append(await campaign.replay_case(case, checkpoint="after-invalidation", arms=["hindsight", "empty"]))
        elif args.stage == "s11":
            await campaign.retain("s11")
            await campaign.record_curation_state("s11-curation-state")
            case = next(c for c in manifest["cases"] if c["id"] == "q08")
            summaries.append(await campaign.replay_case(case, checkpoint="after-unrelated-s11", arms=["hindsight", "empty"]))
        elif args.stage == "retry-s10":
            await campaign.retain("s10", exact_retry=True)
            await campaign.record_curation_state("s10-after-retry-curation")
            case = next(c for c in manifest["cases"] if c["id"] == "q08")
            summaries.append(await campaign.replay_case(case, checkpoint="after-exact-retry-s10", arms=["hindsight", "empty"]))
        elif args.stage == "s12":
            await campaign.retain("s12")
            await campaign.record_s12_provenance()
            case = next(c for c in manifest["cases"] if c["id"] == "q08")
            summaries.append(await campaign.replay_case(case, checkpoint="after-historical-quote-s12", arms=["hindsight", "empty"]))
        campaign.store.write("stage-completion.json", {"status":"completed","stage":args.stage,"workspace_id":manifest["workspace_id"],"summaries":summaries})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--stage", choices=("readiness","initial-retain-a","initial-retain-b","initial-compare-a","initial-compare-b","consolidate","version-archive","invalidate-s10","s11","retry-s10","s12"), required=True)
    args = parser.parse_args(argv)
    if args.output_directory.exists():
        print(json.dumps({"status":"failed","code":"stage_output_directory_must_be_new"}), file=sys.stderr)
        return 1
    try:
        asyncio.run(run(args))
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        code = str(exc) if isinstance(exc, RuntimeError) else "campaign_stage_failed"
        print(json.dumps({"status":"failed","code":code}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
