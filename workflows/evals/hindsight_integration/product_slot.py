"""One frozen synthetic relationship: actual setup dialogue, then a fresh-chat probe."""

from datetime import datetime, timezone
from pathlib import Path
import re
import time
from uuid import uuid4

import httpx

from .casebook import actor_material
from .live_artifacts import reference
from .live_capture_contracts import ProductReadbacks, ProductSlotManifest
from .live_provenance import write_product_manifest
from .models import Observation, RequestSnapshot, Scope
from .product_turns import send_turn
from .product_views import (
    ProcessingReadback,
    fresh_readbacks,
    memory_path,
    original_sources,
    page,
    saved_state,
    wait_processed,
)
from .public_http import PublicRecordingTransport, get_json, post_json
from .records import digest, seal, write_new
from .runs import record_capture


def safe_failure(exc):
    code = str(exc)
    return type(exc).__name__ + (
        ":" + code if re.fullmatch(r"[A-Za-z0-9_:.-]{1,240}", code) else ""
    )


def scoped(scope):
    return Scope(
        workspace=scope["workspace_id"],
        subject=scope["subject_id"],
        character_root=scope["character_root_id"],
    )


async def run_product_slot(
    *,
    path: Path,
    case,
    repeat: int,
    runtime,
    source: dict,
    api_url: str,
    api_key: str,
    router_url: str,
    router_key: str,
    timeout: int = 1200,
    transport_factory=PublicRecordingTransport,
):
    actor = actor_material(case)
    write_new(path / "actor.json", actor)
    observation = Observation(
        mode="live_capture",
        status="failed",
        stage="setup",
        error="slot_not_finished",
        history_provenance="product_dialogue",
        limitations=[
            "Incomplete product slot; inspect retained HTTP and capture receipts."
        ],
    )
    progress = ProcessingReadback()
    deadline = time.monotonic() + timeout
    collections, scope, readbacks = [], {}, None
    api_transport = transport_factory(path / "api-http")
    router_transport = transport_factory(path / "router-http")
    try:
        async with (
            httpx.AsyncClient(
                base_url=api_url,
                headers={"Authorization": "Bearer " + api_key},
                transport=api_transport,
                timeout=30,
            ) as api,
            httpx.AsyncClient(
                base_url=router_url,
                headers={"Authorization": "Bearer " + router_key},
                transport=router_transport,
                timeout=30,
            ) as router,
        ):
            source_session = await post_json(
                api,
                "/api/v3/evaluation-sessions",
                {
                    "idempotency_key": "stage1-source-" + uuid4().hex,
                    "title": f"Stage1 {case.case_id} r{repeat} source",
                    "model_key": runtime.character_route,
                    "compaction_model_key": runtime.character_route,
                    "prompt_key": "chat_v20261019",
                    "persona_key": "chat_linxiaotang",
                    "tool_names": ["search_memory"],
                },
            )
            probe_session = await post_json(
                api,
                "/api/v3/evaluation-sessions",
                {
                    "idempotency_key": "stage1-probe-" + uuid4().hex,
                    "title": f"Stage1 {case.case_id} r{repeat} probe",
                    "agent_definition_id": source_session["agent_definition"]["id"],
                    "memory_subject_id": source_session["memory_subject"]["id"],
                },
            )
            observation.source_conversation_id = source_session["conversation"]["id"]
            observation.probe_conversation_id = probe_session["conversation"]["id"]
            scope.update(
                subject_id=source_session["memory_subject"]["id"],
                character_root_id=source_session["agent_definition"][
                    "agent_definition_id"
                ],
            )
            initial = await fresh_readbacks(api, source_session, probe_session)
            observation.fresh_state_receipt = {
                "source_empty_before_setup": True,
                "target_empty_before_setup": True,
                "source_readback": {
                    "state": initial["source_initial_state"],
                    "memories": initial["source_initial_memories"],
                    "deliveries": initial["source_initial_deliveries"],
                },
                "target_readback": {
                    "state": initial["probe_initial_state"],
                    "memories": initial["probe_initial_memories"],
                },
            }
            for index, seed in enumerate(actor["history"], 1):
                ref, _, _ = await send_turn(
                    api,
                    router,
                    session=source_session,
                    content=seed["content"],
                    phase="setup",
                    source=source,
                    scope=scope,
                    root=path,
                    out=path / "product" / f"setup-{index:02d}",
                    deadline=deadline,
                )
                collections.append(ref)
            source_state = await saved_state(api, observation.source_conversation_id)
            observation.source_messages = original_sources(source_state, case, scope)
            observation.source_scope = observation.target_scope = scoped(scope)
            observation.source_complete = True
            observation.stage = "retention"
            deliveries, operations = await wait_processed(
                api,
                source_session,
                expected_message_ids={
                    row.message_id for row in observation.source_messages
                },
                deadline=deadline,
                progress=progress,
            )
            route = memory_path(source_session)
            memory_snapshot = await page(api, route + "/memories")
            documents = [
                await get_json(api, route + f"/sources/{row['document_id']}")
                for row in deliveries["items"]
            ]
            readbacks = ProductReadbacks(
                source_session=source_session,
                probe_session=probe_session,
                **initial,
                deliveries=deliveries,
                operations=operations,
                memories=memory_snapshot,
                source_state=source_state,
                source_documents=documents,
            )
            observation.delivery_receipts = deliveries["items"]
            observation.memory_snapshot = readbacks.model_dump(mode="json")
            observation.stage = "capture"
            ref, bundle, result = await send_turn(
                api,
                router,
                session=probe_session,
                content=actor["prompt"],
                phase="probe",
                source=source,
                scope=scope,
                root=path,
                out=path / "product" / "probe",
                deadline=deadline,
            )
            collections.append(ref)
            lookups = [
                record["value"]
                for attempt in bundle["export"]["observations"]
                for record in attempt["records"]
                if record["type"] == "memory_lookup.completed"
            ]
            observation.recall_payload = {"lookups": lookups}
            observation.recalled_scopes = (
                [scoped(scope)] if any(row["selected_ids"] for row in lookups) else []
            )
            observation.requests = [
                RequestSnapshot(
                    request_id=wire["request"]["request_id"],
                    sent_at=datetime.fromtimestamp(
                        wire["request"]["started_at"], timezone.utc
                    ),
                    served_identity_sha256=runtime.character_identity_sha256,
                    body=wire["request"]["body"],
                )
                for wire in bundle["wires"]
                if wire["request"]["metadata"]["role"] == "conversation"
            ]
            observation.reply, observation.reply_message_id = (
                result["reply"],
                result["reply_message_id"],
            )
            observation.reply_committed = True
        write_new(path / "readbacks.json", seal("product-readbacks", readbacks))
        manifest = ProductSlotManifest(
            case_id=case.case_id,
            repeat=repeat,
            actor_sha256=digest(actor),
            source=source,
            scope=scope,
            source_conversation_id=observation.source_conversation_id,
            probe_conversation_id=observation.probe_conversation_id,
            collections=collections,
            readbacks=reference(path, path / "readbacks.json"),
            journals=[
                reference(path, path / folder / "index.json")
                for folder in ("api-http", "router-http")
            ],
        )
        observation.product_capture = write_product_manifest(path, manifest)
        observation.observed_runtime = runtime
        observation.input_complete = True
        observation.status, observation.stage, observation.error = (
            "completed",
            "finished",
            None,
        )
        observation.retention, observation.consolidation = (
            progress.retention,
            progress.consolidation,
        )
        observation.limitations = [
            "Small real product demonstration, not general Memory reliability or Character acceptance.",
            "Provider identities are configured/reported service identities, not remote weight attestations.",
        ]
        try:
            issues = record_capture(
                path, Observation.model_validate(observation.model_dump())
            )
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            observation.product_capture = None
            observation.observed_runtime = None
            observation.status, observation.stage, observation.error = (
                "failed",
                "capture",
                safe_failure(exc),
            )
            observation.input_complete = False
            observation.limitations.append(
                "Product sidecar validation failed; all original files remain retained."
            )
            issues = record_capture(path, observation)
        return observation, issues
    except Exception as exc:
        observation.product_capture = None
        observation.observed_runtime = None
        observation.status, observation.error = "failed", safe_failure(exc)
        observation.stage = getattr(exc, "stage", observation.stage)
        observation.input_complete = False
        observation.retention, observation.consolidation = (
            progress.retention,
            progress.consolidation,
        )
        if progress.retention == "complete" and observation.stage == "retention":
            observation.stage = "consolidation"
        if "workspace_id" in scope:
            observation.source_scope = observation.target_scope = scoped(scope)
        bundle = getattr(exc, "bundle", None)
        if bundle:
            if bundle["phase_group"] == "setup":
                observation.source_messages = original_sources(
                    bundle["state"], case, scope, require_complete=False
                )
                observation.source_complete = (
                    len(observation.source_messages) == len(case.history) * 2
                )
            else:
                replies = [
                    row
                    for row in bundle["state"]["conversation"]["messages"]
                    if row["role"] == "assistant"
                    and row["run_id"] == bundle["run"]["id"]
                ]
                if len(replies) == 1:
                    observation.reply = replies[0]["content"]
                    observation.reply_message_id = replies[0]["id"]
                    observation.reply_committed = True
        write_new(
            path / "failure.json",
            {"stage": observation.stage, "error": observation.error},
        )
        return observation, record_capture(path, observation)
