"""Revalidate product phase collections and their source-linked sidecars."""

import hashlib
from pathlib import Path

from .casebook import actor_material
from .capture_validation import qualify_run_capture
from .live_capture_contracts import (
    FileReference,
    ProductCollection,
    ProductReadbacks,
    ProductSlotManifest,
)
from .live_artifacts import referenced_file, journal_bodies
from .live_readbacks import validate_readbacks
from .models import ProductCaptureProvenance
from .records import digest, load_sealed, seal, write_new
from .wire_capture import require
from .native_checks import require_full_chinese_reranking


def validate_product_provenance(path: Path, run, case, attempt, observation) -> None:
    provenance = observation.product_capture
    if provenance is None:
        return
    require(run.mode == "live_capture", "scripted_capture_has_product_sidecar")
    manifest_path = referenced_file(
        path,
        FileReference(
            path=provenance.manifest_file, file_sha256=provenance.file_sha256
        ),
    )
    manifest, _ = load_sealed(manifest_path, "product-slot", ProductSlotManifest)
    require(
        manifest.case_id == case.case_id
        and manifest.repeat == attempt.repeat
        and manifest.actor_sha256 == digest(actor_material(case)),
        "slot_actor_or_attempt_mismatch",
    )
    require(
        manifest.source["source_revision"]
        == run.runtime.product_revision
        == run.evaluator_revision,
        "slot_source_mismatch",
    )
    require(
        manifest.source_conversation_id == observation.source_conversation_id
        and manifest.probe_conversation_id == observation.probe_conversation_id,
        "slot_conversation_mismatch",
    )
    actual_scope = {
        "workspace": manifest.scope["workspace_id"],
        "subject": manifest.scope["subject_id"],
        "character_root": manifest.scope["character_root_id"],
    }
    require(
        observation.source_scope.model_dump()
        == observation.target_scope.model_dump()
        == actual_scope,
        "slot_relationship_mismatch",
    )
    setup = [item for item in manifest.collections if item.phase == "setup"]
    probes = [item for item in manifest.collections if item.phase == "probe"]
    require(
        len(setup) == len(case.history)
        and len(probes) == 1
        and len(setup) + 1 == len(manifest.collections),
        "slot_phase_coverage_incomplete",
    )
    expected = [seed.content for seed in case.history] + [case.prompt]
    probe_bundle = None
    for ref, content in zip([*setup, *probes], expected, strict=True):
        bundle, _ = load_sealed(
            referenced_file(path, ref), "product-run-collection", ProductCollection
        )
        require(
            bundle.scope == manifest.scope
            and bundle.source == manifest.source
            and bundle.phase_run_id == ref.run_id == bundle.run["id"]
            and bundle.phase_group == ref.phase
            and bundle.expected_input == content
            and bundle.fresh_probe == (ref.phase == "probe"),
            "phase_binding_mismatch",
        )
        qualify_run_capture(
            run=bundle.run,
            export=bundle.export,
            state=bundle.state["conversation"],
            wires=bundle.wires,
            events=bundle.events,
            scope=bundle.scope,
            source=bundle.source,
            expected_input=content,
            fresh_probe=bundle.fresh_probe,
        )
        for observed in bundle.export["observations"]:
            for record in observed["records"]:
                if record["type"] == "context.sources":
                    require(
                        record["value"]["bank_configuration_sha256"]
                        == run.runtime.memory_config_sha256,
                        "memory_mission_binding_mismatch",
                    )
        if ref.phase == "probe":
            probe_bundle = bundle
    bodies = set()
    for journal in manifest.journals:
        bodies.update(journal_bodies(path, journal))
    readback_path = referenced_file(path, manifest.readbacks)
    readbacks, _ = load_sealed(readback_path, "product-readbacks", ProductReadbacks)
    for name, value in readbacks.model_dump(mode="json").items():
        for body in value if name == "source_documents" else [value]:
            require(digest(body) in bodies, "readback_missing_from_actual_http_journal")
    validate_readbacks(readbacks, observation, manifest, case, run)
    requests = {
        wire["request"]["request_id"]: wire
        for wire in probe_bundle.wires
        if wire["request"]["metadata"]["role"] == "conversation"
    }
    require(
        {request.request_id for request in observation.requests} == set(requests),
        "probe_request_set_mismatch",
    )
    for request in observation.requests:
        wire = requests[request.request_id]
        require(
            request.body == wire["request"]["body"]
            and request.served_identity_sha256 == run.runtime.character_identity_sha256,
            "probe_request_or_model_mismatch",
        )
    committed = [
        row
        for row in probe_bundle.state["conversation"]["messages"]
        if row["role"] == "assistant" and row["run_id"] == probe_bundle.run["id"]
    ]
    require(
        len(committed) == 1
        and observation.reply == committed[0]["content"]
        and observation.reply_message_id == committed[0]["id"]
        and observation.reply_committed is True,
        "observation_reply_not_committed",
    )
    lookups = [
        record["value"]
        for observed in probe_bundle.export["observations"]
        for record in observed["records"]
        if record["type"] == "memory_lookup.completed"
    ]
    require(
        observation.recall_payload == {"lookups": lookups},
        "observation_recall_not_actual_attempt_snapshot",
    )
    for lookup in lookups:
        if lookup["response"].get("results"):
            require_full_chinese_reranking(lookup["response"])


def write_product_manifest(
    path: Path, manifest: ProductSlotManifest
) -> ProductCaptureProvenance:
    destination = path / "product-slot.json"
    write_new(destination, seal("product-slot", manifest))
    return ProductCaptureProvenance(
        manifest_file=destination.name,
        file_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
    )
