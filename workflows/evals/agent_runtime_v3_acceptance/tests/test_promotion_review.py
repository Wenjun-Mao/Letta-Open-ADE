from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import pytest
from agent_runtime_eval_contracts import (
    EventObservation,
    FactObservation,
    ToolObservation,
    TurnObservation,
    load_cases,
    score_case,
    study_cases_path,
)
from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from workflows.evals.agent_runtime_v3_acceptance.artifacts import RoundArtifactWriter
from workflows.evals.agent_runtime_v3_acceptance.policy import production_policy_hashes
from workflows.evals.agent_runtime_v3_acceptance.promotion_review import (
    GitState,
    PromotionReviewError,
    review_promotion,
)
from workflows.evals.agent_runtime_v3_acceptance.proposal import (
    build_promotion_proposal,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def test_review_is_non_mutating_and_apply_promotes_the_bound_role_set(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "deployment-manifest.json"
    manifest_path.write_bytes(
        (PROJECT_ROOT / "config/model-router/deployment-manifest.json").read_bytes()
    )
    proposal_path = _evidence(tmp_path, manifest_path)
    original = manifest_path.read_bytes()
    state = GitState(revision="c" * 40, dirty=False)

    checked = review_promotion(
        proposal_path=proposal_path,
        manifest_path=manifest_path,
        project_root=PROJECT_ROOT,
        apply=False,
        git_state=state,
    )

    assert checked.applied is False
    assert manifest_path.read_bytes() == original

    applied = review_promotion(
        proposal_path=proposal_path,
        manifest_path=manifest_path,
        project_root=PROJECT_ROOT,
        apply=True,
        git_state=state,
    )
    manifest = load_deployment_manifest(manifest_path)
    by_id = {item.deployment_id: item for item in manifest.deployments}

    assert applied.applied is True
    assert by_id["dgx-qwen3_6-chat"].lifecycle == "qualified"
    assert by_id["dgx-qwen3-embedding-0_6b"].lifecycle == "qualified"
    assert by_id["llama-server-qwen3_5-27b"].lifecycle == "discovered"
    assert all(
        result.qualified
        for deployment_id in applied.deployment_ids
        for result in by_id[deployment_id].qualification.role_results
    )


def test_review_rejects_tampered_events_or_dirty_source(tmp_path: Path) -> None:
    manifest_path = tmp_path / "deployment-manifest.json"
    manifest_path.write_bytes(
        (PROJECT_ROOT / "config/model-router/deployment-manifest.json").read_bytes()
    )
    proposal_path = _evidence(tmp_path, manifest_path)

    with pytest.raises(PromotionReviewError, match="exact clean source"):
        review_promotion(
            proposal_path=proposal_path,
            manifest_path=manifest_path,
            project_root=PROJECT_ROOT,
            apply=False,
            git_state=GitState(revision="c" * 40, dirty=True),
        )

    events_path = proposal_path.parent / "round-002" / "events.jsonl"
    events_path.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(PromotionReviewError, match="events digest"):
        review_promotion(
            proposal_path=proposal_path,
            manifest_path=manifest_path,
            project_root=PROJECT_ROOT,
            apply=False,
            git_state=GitState(revision="c" * 40, dirty=False),
        )


def _evidence(tmp_path: Path, manifest_path: Path) -> Path:
    manifest = load_deployment_manifest(manifest_path)
    by_id = {item.deployment_id: item for item in manifest.deployments}
    chat = by_id["dgx-qwen3_6-chat"]
    embedding = by_id["dgx-qwen3-embedding-0_6b"]
    snapshots = (
        _snapshot(chat, "conversation"),
        _snapshot(chat, "reviewer"),
        _snapshot(embedding, "retriever"),
    )
    fingerprints = {
        "conversation": chat.fingerprint.sha256,
        "reviewer": chat.fingerprint.sha256,
        "retriever": embedding.fingerprint.sha256,
    }
    cases = (
        SimpleNamespace(
            resources=SimpleNamespace(deployment_snapshots=snapshots),
        ),
    )
    canonical_cases = tuple(load_cases(study_cases_path()))
    case_keys = tuple(case.key for case in canonical_cases)
    writer = RoundArtifactWriter(tmp_path, "run-a")
    rounds = []
    round_summaries = []
    for index in range(1, 4):
        case_payloads = []
        raw_events = []
        for case in canonical_cases:
            case_payload, case_events = _passing_case_evidence(case, index)
            case_payloads.append(case_payload)
            raw_events.extend(case_events)
        summary = {
            "index": index,
            "kind": "primary",
            "execution_mode": "live-api",
            "complete_matrix": True,
            "passed": True,
            "case_keys": list(case_keys),
            "deployment_fingerprints": fingerprints,
            "deployment_snapshots": list(snapshots),
            "artifact_sha256": "",
            "cases": case_payloads,
        }
        artifact = writer.write_round(index, summary, raw_events)
        rounds.append(
            SimpleNamespace(
                index=index,
                kind="primary",
                execution_mode="live-api",
                complete_matrix=True,
                passed=True,
                case_keys=case_keys,
                artifact_sha256=artifact.sha256,
                deployment_fingerprints=fingerprints,
                cases=cases,
            )
        )
        round_summaries.append({**summary, "artifact_sha256": artifact.sha256})
    policy_hashes = production_policy_hashes(PROJECT_ROOT)
    qualification_config = {
        "conversation_model_key": chat.route_aliases[0],
        "reviewer_model_key": chat.route_aliases[0],
        "embedding_model_key": embedding.route_aliases[0],
        "rounds": 3,
        "timeout_seconds": 180.0,
        "retry_count": 0,
        "case_keys": [],
    }
    _provenance_path, provenance_sha256 = writer.write_provenance(
        {
            "schema_version": 1,
            "kind": "agent-runtime-v3-acceptance-provenance",
            "captured_at": "2026-08-29T12:00:00+00:00",
            "run_id": "run-a",
            "source_revision": "c" * 40,
            "source_dirty": False,
            "policy_hashes": policy_hashes,
            "effective_config": qualification_config,
            "canonical_case_keys": list(case_keys),
            "canonical_case_keys_sha256": hashlib.sha256(
                "\n".join(case_keys).encode("utf-8")
            ).hexdigest(),
            "agent_runtime_eval_contracts_version": "0.3.0",
            "primary_rounds": round_summaries,
            "llama_compatibility": None,
        }
    )
    proposal = build_promotion_proposal(
        output_dir=tmp_path,
        run_id="run-a",
        rounds=tuple(rounds),
        canonical_case_keys=case_keys,
        required_rounds=3,
        provenance_sha256=provenance_sha256,
        source_revision="c" * 40,
        source_dirty=False,
        policy_hashes=policy_hashes,
        qualification_config=qualification_config,
    )
    assert proposal is not None
    return proposal.path


def _snapshot(deployment, role: str) -> dict[str, str]:
    return {
        "deployment_id": deployment.deployment_id,
        "route_alias": deployment.route_aliases[0],
        "fingerprint": deployment.fingerprint.sha256,
        "role": role,
    }


def _passing_case_evidence(case, round_index: int):
    fact_records = []
    facts_by_subject = {subject_key: [] for subject_key in case.subject_keys}
    for fact_index, assertion in enumerate(case.fact_assertions, start=1):
        if assertion.absent:
            continue
        observation = FactObservation(
            key=assertion.key or "profile.note",
            value=assertion.aliases[0],
        )
        facts_by_subject[assertion.subject_key].append(observation)
        fact_records.append(
            {
                "subject_key": assertion.subject_key,
                "fact_id": f"fact-{round_index}-{case.key}-{fact_index}",
                "observation": {"key": observation.key, "value": observation.value},
            }
        )

    assistant_fragments = defaultdict(list)
    for assertion in case.assistant_assertions:
        if assertion.contains_any:
            assistant_fragments[assertion.conversation_key].append(
                assertion.contains_any[0]
            )
    results_by_conversation = {
        conversation_key: [] for conversation_key in case.conversations
    }
    turn_records = []
    tool_records = []
    raw_events = []
    for turn_index, fixture_turn in enumerate(case.turns, start=1):
        run_id = f"run-{round_index}-{case.key}-{turn_index}"
        tool_observations = ()
        if turn_index == 1:
            tool_observations = tuple(
                ToolObservation(
                    name=name,
                    succeeded=not case.require_failed_tool_result,
                )
                for name in case.required_tools
            )
        event_observations = (
            EventObservation(type="model.request"),
            EventObservation(type="model.response"),
            EventObservation(type="memory.review.request"),
            *(
                (EventObservation(type="summary.committed"),)
                if case.prelude_messages
                else ()
            ),
        )
        assistant_text = " ".join(
            assistant_fragments.get(fixture_turn.conversation_key) or ["ok"]
        )
        observation = TurnObservation(
            status="succeeded",
            assistant_text=assistant_text,
            candidate_assistant_text=assistant_text,
            events=event_observations,
            tools=tool_observations,
            usage={"input_tokens": 10, "output_tokens": 5},
            elapsed_seconds=0.5,
        )
        results_by_conversation[fixture_turn.conversation_key].append(observation)
        turn_records.append(
            {
                "case_key": case.key,
                "conversation_key": fixture_turn.conversation_key,
                "run_id": run_id,
                "attempt_count": 1,
                "observation": {
                    "status": observation.status,
                    "assistant_text": observation.assistant_text,
                    "candidate_assistant_text": observation.candidate_assistant_text,
                    "events": [{"type": item.type} for item in observation.events],
                    "tools": [
                        {"name": item.name, "succeeded": item.succeeded}
                        for item in observation.tools
                    ],
                    "usage": dict(observation.usage),
                    "elapsed_seconds": observation.elapsed_seconds,
                },
            }
        )
        for tool in tool_observations:
            tool_records.append(
                {
                    "run_id": run_id,
                    "name": tool.name,
                    "succeeded": tool.succeeded,
                    "payload": {},
                }
            )
        raw_types = [
            ("run.started", {}),
            ("model.request.started", {"role": "conversation"}),
            ("model.response.completed", {"role": "conversation"}),
            ("model.request.started", {"role": "reviewer"}),
            ("model.response.completed", {"role": "reviewer"}),
        ]
        if case.prelude_messages:
            raw_types.append(
                (
                    "summary.committed",
                    {"version": 1, "through_sequence": 70},
                )
            )
        raw_types.extend(
            ("tool.call.completed", {"name": tool.name}) for tool in tool_observations
        )
        raw_types.extend((("message.committed", {}), ("run.completed", {"usage": {}})))
        raw_events.extend(
            {
                "run_id": run_id,
                "sequence": sequence,
                "event_type": event_type,
                "attempt": 1,
                "payload": payload,
            }
            for sequence, (event_type, payload) in enumerate(raw_types, start=1)
        )
    score = score_case(
        case=case,
        facts_by_subject=facts_by_subject,
        results_by_conversation=results_by_conversation,
    )
    assert score["pass"] is True
    return (
        {
            "case_key": case.key,
            "score": score,
            "infrastructure": {
                "failures": [],
                "terminal_statuses": ["succeeded"] * len(case.turns),
                "all_terminal": True,
            },
            "turns": turn_records,
            "tools": tool_records,
            "facts": fact_records,
            "resources": {
                "definition_keys": [f"definition-{case.key}"],
                "subject_external_keys": [f"subject-{case.key}"],
            },
        },
        raw_events,
    )
