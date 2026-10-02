"""Offline runtime-owned construction and post-run schema/source binding audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from ade_api.features.agent_runtime.natural_memory_binding import (
    build_natural_binding_map,
)
from ade_api.features.agent_runtime.natural_memory_policy import (
    prepare_natural_memory_review,
)
from ade_api.features.agent_runtime.natural_memory_review import (
    parse_natural_review_decision,
)
from workflows.evals.character_memory_dev.story_continuity.evidence_selection.behavioral.contracts import (
    ARMS,
    DIRECTORY,
    PINNED,
    ROOT,
    digest,
    estimate,
    load_prepared,
    wire,
)
from workflows.evals.character_memory_dev.story_continuity.evidence_selection.offline_inputs import (
    load_offline_inputs,
)

if __package__:
    from .story_correction_comparison import current_message, exchanges
    from .story_offline_capacity import build_complete_packet
else:
    from story_correction_comparison import current_message, exchanges
    from story_offline_capacity import build_complete_packet


def construct():
    context, cases, freeze = load_offline_inputs()
    case = next(c for c in cases if c["id"] == "D04")
    sources = exchanges(case, context)
    packets, sizes = [], []
    for arm, included in ARMS:
        receipt, requests = build_complete_packet(
            case=case, context=context, sources=sources, included=list(included)
        )
        old_generation = digest(requests["generation"])
        assert "thinking" not in requests["generation"]
        assert "reasoning_effort" not in requests["generation"]
        for request in requests.values():
            request.update(PINNED)
        assert estimate(requests["generation"]) <= 11213
        assert estimate(requests["reviewer_full_reserve"]) <= 11469
        packets.append({"arm": arm, "included": list(included), **requests})
        sizes.append(
            {
                "arm": arm,
                "history_sha256": receipt["history_sha256"],
                "source_order": receipt["source_order"],
                "generation_before_pinning_sha256": old_generation,
                "generation_input_estimate": estimate(requests["generation"]),
                "reviewer_full_reserve_estimate": estimate(
                    requests["reviewer_full_reserve"]
                ),
                "request_sha256": {k: digest(v) for k, v in requests.items()},
            }
        )
    paths = [
        Path(__file__),
        DIRECTORY / "PROTOCOL.md",
        DIRECTORY / "router-sources.json",
        Path(__file__).with_name("story_offline_capacity.py"),
        DIRECTORY.parent / "offline_capacity.json",
        DIRECTORY.parent / "offline_packets.jsonl",
    ]
    paths += list(DIRECTORY.glob("*.py"))
    # Bind all runtime serializer, binder, schema and router sources, not only
    # the immediate imports. No environment/local secret files are read.
    for directory in (
        ROOT / "services/ade-api/src/ade_api/features/agent_runtime",
        ROOT / "services/model-router/src/model_router",
        ROOT / "config/model-router",
    ):
        paths += [
            p
            for p in directory.rglob("*")
            if p.suffix in {".py", ".json"} and ".local." not in p.name
        ]
    return {
        "kind": "D04_behavioral_offline_preparation_no_provider_outcomes",
        "historical_freeze": freeze,
        "source_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths))
        },
        "requests_sha256": digest(packets),
        "sizes": sizes,
        "configuration_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "config/model-router/model-profiles.json",
                "config/model-router/deployment-manifest.json",
                str((DIRECTORY / "router-sources.json").relative_to(ROOT)),
            )
        },
        "settings": {
            **PINNED,
            "max_tokens": 4096,
            "deadline_seconds": 180,
            "generation_input_limit": 11213,
            "reviewer_input_limit": 11469,
            "candidate_reply_reserve": 4096,
            "tools": "absent",
            "retries": 0,
            "maximum_chat_requests": 6,
        },
    }, packets


def validate_observation(arm: str, reply: str, payload: object):
    """Existing schema/binding policy; no persistence or semantic scorer."""
    load_prepared()
    included = dict(ARMS)[arm]
    context, cases, _ = load_offline_inputs()
    case = next(c for c in cases if c["id"] == "D04")
    current = current_message(case)
    sources = exchanges(case, context)
    binding = build_natural_binding_map(
        current_user_message=current,
        source_messages=[current],
        facts=[],
        entities=[],
        history_exchanges=[sources[s] for s in included],
    )
    return prepare_natural_memory_review(
        decision=parse_natural_review_decision(payload),
        subject_id="diagnostic-subject",
        current_user_message=current,
        available_messages=[current],
        facts=[],
        entities=[{"id": "diagnostic-subject", "kind": "subject"}],
        candidate_reply=reply,
        binding_map=binding,
    )


if __name__ == "__main__":
    if len(sys.argv) == 1:
        preparation, packets = construct()
        for name, value in (
            ("preparation.json", preparation),
            ("requests.json", packets),
        ):
            (DIRECTORY / name).write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n"
            )
        print(wire(preparation["sizes"]))
    else:
        # Private operator audit after capture; never rewrite originals.
        from workflows.evals.character_memory_dev.story_continuity.evidence_selection.behavioral.runner import (
            audit,
        )

        print(wire(audit(Path(sys.argv[1]), validate_observation)))
