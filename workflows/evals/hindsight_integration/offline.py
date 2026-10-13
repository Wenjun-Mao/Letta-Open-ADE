"""Scripted mechanics rehearsal. No network, provider, or product client."""

from datetime import timedelta
from pathlib import Path

from .casebook import actor_material, load_suite
from .models import LENSES, Observation, Review, RuntimeBinding, Scope, SourceMessage
from .records import digest, model_from_json, utc_now
from .report import write_report
from .reviews import record_review, review_template
from .runs import load_attempt, prepare_run, record_capture, start_attempt


def scripted_runtime() -> RuntimeBinding:
    suite = load_suite()
    return RuntimeBinding(
        product_revision="scripted-no-product-runtime",
        persona_version=suite["persona"]["content_sha256"],
        persona_text=suite["persona"]["content"],
        prompt_version="offline-mechanics-v1",
        system_prompt="Offline scripted rehearsal only.",
        character_route="offline://authored-example",
        character_identity_sha256=digest("scripted-character"),
        character_settings={"scripted": True},
        memory_implementation="scripted",
        memory_config_sha256=digest("scripted-memory"),
        embedding_identity_sha256=digest("no-embedding"),
    )


def scripted_observation(path: Path, reply: str) -> Observation:
    run, case, attempt, attempt_hash = load_attempt(path)
    if run.mode != "offline_scripted":
        raise ValueError("A scripted rehearsal cannot populate a live capture")
    actor = actor_material(case)
    namespace = f"{run.run_id}-{attempt_hash[:12]}"
    source = Scope(
        **{key: f"{namespace}-{value}" for key, value in actor["source_scope"].items()}
    )
    target = Scope(
        **{key: f"{namespace}-{value}" for key, value in actor["target_scope"].items()}
    )
    now = utc_now()
    return Observation(
        mode="offline_scripted",
        status="completed",
        stage="finished",
        observed_runtime=run.runtime,
        history_provenance={
            "user_dialogue": "product_dialogue",
            "controlled_history": "controlled_history",
            "creation": "no_history",
        }[case.history_kind],
        source_scope=source,
        target_scope=target,
        source_conversation_id=f"{namespace}-source",
        probe_conversation_id=f"{namespace}-probe",
        fresh_state_receipt={
            "scripted": True,
            "source_empty_before_setup": True,
            "target_empty_before_setup": True,
            "source_readback": {"scripted_empty": True},
            "target_readback": {"scripted_empty": True},
        },
        source_complete=True,
        input_complete=True,
        source_messages=[
            SourceMessage(
                message_id=f"{namespace}-{message.fixture_id}",
                fixture_id=message.fixture_id,
                conversation_id=f"{namespace}-source",
                scope=source,
                role=message.role,
                content=message.content,
                occurred_at=now - timedelta(seconds=len(case.history) - index),
                status="accepted" if message.role == "user" else "committed",
            )
            for index, message in enumerate(case.history)
        ],
        retention="complete" if case.history else "not_applicable",
        consolidation="complete" if case.history else "not_applicable",
        delivery_receipts=[{"scripted": True}] if case.history else [],
        memory_snapshot={"scripted": True, "sources": actor["history"]},
        recall_payload={
            "scripted": True,
            "sources": actor["history"] if source == target else [],
        },
        recalled_scopes=[target] if case.history and source == target else [],
        requests=[
            {
                "request_id": f"{namespace}-request",
                "sent_at": now,
                "served_identity_sha256": run.runtime.character_identity_sha256,
                "body": {
                    "model": "offline-scripted",
                    "messages": [
                        {
                            "role": "system",
                            "content": run.runtime.system_prompt
                            + "\n"
                            + run.runtime.persona_text,
                        },
                        {"role": "user", "content": actor["prompt"]},
                    ],
                },
            }
        ],
        reply=reply,
        reply_message_id=f"{namespace}-reply",
        reply_committed=True,
        limitations=[
            "All runtime, source, memory and request evidence is synthetic; no product or model ran."
        ],
    )


def dry_run(root: Path) -> dict:
    suite = load_suite()
    prepare_run(
        root,
        run_id="offline-rehearsal",
        mode="offline_scripted",
        runtime=scripted_runtime(),
        repeats=2,
    )
    examples = [
        ("q01-useful", 1, True),
        ("q01-repeat-question", 2, True),
        ("q02-invented-switch", 1, True),
        ("q02-invented-switch", 2, False),
    ]
    for example_id, repeat, reviewed in examples:
        example = suite["calibration"][example_id]
        path = start_attempt(root, example.case_id, repeat)
        issues = record_capture(path, scripted_observation(path, example.reply))
        if issues:
            raise ValueError(f"Scripted fixture failed its mechanical checks: {issues}")
        if reviewed:
            review = review_template(path)
            review.update(
                kind="scripted_example",
                reviewer="authored-calibration-example",
                judgments={
                    lens: judgment.model_dump()
                    for lens, judgment in example.judgments.items()
                },
            )
            record_review(path, model_from_json(Review, review))
    path = start_attempt(root, "q05-listen", 1)
    record_capture(
        path,
        Observation(
            mode="offline_scripted",
            status="failed",
            stage="recall",
            error="Deliberate scripted lookup failure",
            limitations=["No model request or reply exists."],
        ),
    )
    review = review_template(path)
    review.update(
        kind="scripted_example",
        reviewer="offline-failure-example",
        judgments={
            lens: {
                "result": "cannot_assess",
                "quote": "",
                "rationale": "Deliberate recall failure produced no reply.",
            }
            for lens in LENSES
        },
    )
    record_review(path, model_from_json(Review, review))
    start_attempt(root, "q05-listen", 2)
    return write_report(root, root / "report")
