"""Frozen prompts, annotation gates and network-free preparation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from .baseline import MANIFEST, SOURCES, preparation_binding

FIXTURE = Path(__file__).with_name("fixtures.json")
# Freeze bytes, not merely parsed meaning. Changes require another review.
FIXTURE_SHA256 = "56669a939e4883781d0f23215fda5beea22ab3ff1d6df2812847901a06d0ad5f"
ROOT = Path(__file__).resolve().parents[4]


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def frozen_schedule() -> dict:
    raw = FIXTURE.read_bytes()
    if digest(raw) != FIXTURE_SHA256:
        raise ValueError("PC-11 fixture changed after offline freeze")
    return json.loads(raw)


def prompt_for(turn: dict, *, replacement_suggestion: str | None = None) -> str:
    # Only the rewrite control may receive an annotated suggestion. Recall
    # prompts cannot interpolate the origin's diagnostic answers.
    if turn["id"] != 4:
        if replacement_suggestion is not None:
            raise ValueError("Annotation must not enter recall context")
        return turn["prompt"]
    if not replacement_suggestion or not replacement_suggestion.strip():
        raise ValueError("Rewrite requires a predeclared human replacement")
    return turn["prompt"].format(replacement_suggestion=replacement_suggestion)


def dependency_status(turn: dict, outcomes: dict[int, dict]) -> str:
    for dependency in turn["depends_on"]:
        outcome = outcomes.get(dependency)
        if not outcome or outcome.get("disposition") != "committed":
            return "unassessable_dependency"
        if dependency in {1, 3} and not outcome.get("usable_annotation"):
            return "unassessable_dependency"
    return "ready_for_separate_authorization"


def prepare() -> dict:
    schedule = frozen_schedule()
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    if branch != "main":
        raise ValueError("Preparation requires retained main checkout")
    # Bind source bytes, including uncommitted implementation; never pretend
    # HEAD alone describes this preparation or a future immutable definition.
    files = [
        *ROOT.joinpath("services/ade-api/src/ade_api/features/agent_runtime").rglob(
            "*.py"
        ),
        *ROOT.joinpath("content/prompts/system/chat").glob("*.py"),
        ROOT / "content/personas/personas.jsonl",
        ROOT / "docs/product-contract.md",
        *Path(__file__).parent.glob("*.py"),
        FIXTURE,
        MANIFEST,
        SOURCES,
        ROOT / "config/model-router/deployment-manifest.json",
        ROOT / "config/model-router/model-profiles.json",
    ]
    required = [
        "content/prompts/system/chat/chat_v20260926.py",
        "services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py",
        "services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py",
        "services/ade-api/src/ade_api/features/agent_runtime/natural_context.py",
        "services/ade-api/src/ade_api/features/agent_runtime/history_capacity.py",
    ]
    hashes = {
        str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in sorted(files)
    }
    if not all(path in hashes for path in required):
        raise ValueError("Effective prompt/reviewer/schema/capacity source missing")
    return {
        "format": "pc11-offline-preparation-v1",
        "status": "offline_ready_live_approval_required",
        "source_revision": revision,
        "branch": branch,
        "source_files": hashes,
        "source_fingerprint": digest(json.dumps(hashes, sort_keys=True).encode()),
        "governed_source_fingerprint_v2": subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "scripts/source_fingerprint.py"),
                "--root",
                str(ROOT),
            ],
            cwd=ROOT,
            text=True,
        ).strip(),
        "model_profiles_sha256": hashes["config/model-router/model-profiles.json"],
        "fixture_sha256": FIXTURE_SHA256,
        "schedule": schedule["turns"],
        "provider_dispatch": "unavailable",
        "isolated_baseline": preparation_binding(),
        "proposed_binding": {
            "prompt_key": "chat_v20260926",
            "persona_key": "chat_linxiaotang",
            "policy": "natural-user-assertions-v4-b-history-probe",
            "conversation_and_reviewer": "deepseek::deepseek-flash",
            "retriever": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
            "ranking": "probe_local_qwen_cosine_v2",
            "attempts_per_turn": 1,
            "retry_count": 0,
            "settings_authority": "Unchanged history-trial options and immutable deployment snapshots; verify before live approval",
        },
        "offline_readiness_items": {
            "immutable_versions": "implemented_ADR_0051",
            "isolated_deployment_binding": "implemented_ADR_0052",
            "private_observations": "required_ade-private-evaluation-observations-v1_ADR_0053",
        },
        "native_prerequisites": [
            "Separate live authorization, clean source binding, fresh owned database and exact router catalog/settings required",
            "Immutable definition IDs must be created and pinned in that new database, including same-root non-biographical version 2",
            "Every attempt requires complete isolated private observations v1; missing/truncated/mismatched evidence stops qualification",
            "Origin and turn-3 human annotations must be frozen before dependent outcomes; no invented native expected story",
        ],
    }
