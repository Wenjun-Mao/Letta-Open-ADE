"""Frozen inputs and source identity for the one-shot natural-memory campaign."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from .natural_live_results import sha256_file
from .natural_memory_contract import expanded_cells, load_cases, load_matrix


ROOT = Path(__file__).resolve().parents[3]
EMBEDDING_ROUTE = "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B"
EXPECTED_CASES_SHA256 = (
    "abd244c17c5f2e6fe90f9a32bc50e1bb262d233f0dad62db4f682d65b615dcc3"
)
EXPECTED_MATRIX_SHA256 = (
    "188148ea73facc1e2fbecd795d2172e5cb659e489ff792b42dcc0db704a356d8"
)


def _source_identity() -> tuple[str, str]:
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT):
        raise RuntimeError("checkpoint-6 live source must be a clean exact commit")
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    fingerprint = subprocess.check_output(
        [
            sys.executable,
            str(ROOT / "scripts/source_fingerprint.py"),
            "--root",
            str(ROOT),
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or not re.fullmatch(
        r"[0-9a-f]{64}", fingerprint
    ):
        raise RuntimeError("checkpoint-6 source identity is invalid")
    return revision, fingerprint


def _frozen_inputs() -> tuple[dict, dict, list]:
    fixtures = ROOT / "workflows/evals/character_memory_dev/fixtures/natural_memory"
    if sha256_file(fixtures / "cases.json") != EXPECTED_CASES_SHA256:
        raise RuntimeError("frozen natural cases changed")
    if sha256_file(fixtures / "matrix.json") != EXPECTED_MATRIX_SHA256:
        raise RuntimeError("frozen natural matrix changed")
    cases, matrix = load_cases(), load_matrix()
    schedule = matrix["live_request_schedule_proposed_not_authorized"]
    if (
        schedule["generation_limit"] != 96
        or schedule["embedding_limit"] != 160
        or schedule["maximum_reserved_generation"] != 92
        or schedule["timeout_seconds_per_turn"] != 180
        or schedule["application_retries"] != 0
        or schedule["reviewer_repairs"] != 0
    ):
        raise RuntimeError("checkpoint-6 request schedule changed")
    return cases, matrix, expanded_cells(matrix)


def selected_cells(
    frozen_cells: list[tuple[str, dict, str]],
    *,
    diagnostic_first_three: bool,
    iteration_id: str | None,
    diagnostic_reviewer_output_4096: bool,
) -> tuple[list[tuple[str, dict, str]], list[str]]:
    if not diagnostic_first_three:
        if iteration_id or diagnostic_reviewer_output_4096:
            raise RuntimeError("diagnostic options require first-three probe mode")
        return frozen_cells, []
    if iteration_id not in {"c6-iter1", "c6-iter2", "c6-iter3"}:
        raise RuntimeError(
            "diagnostic first-three probe requires a versioned iteration ID"
        )
    if diagnostic_reviewer_output_4096 and iteration_id not in {"c6-iter2", "c6-iter3"}:
        raise RuntimeError("reviewer output diagnostic requires iteration two or three")
    cells = frozen_cells[:3]
    if [cell["id"] for _, cell, _ in cells] != [
        "mutation-preference-add",
        "mutation-scoped-addition",
        "mutation-natural-correction",
    ]:
        raise RuntimeError("diagnostic first-three mutation schedule drifted")
    return cells, [name for name, _, _ in frozen_cells[3:]]


def _branch(cases: dict, cell: dict) -> dict:
    return next(
        branch
        for arc in cases["arcs"]
        if arc["id"] == cell["arc"]
        for branch in arc["branches"]
        if branch["id"] == cell["branch"]
    )


def _current_text(branch: dict, cell: dict) -> str:
    return next(
        text
        for label, role, text in branch["turns"]
        if label == cell["cutoff"] and role == "user"
    )


def _admitted_mutation_sources(branch: dict, cell: dict, evidence: dict) -> bool:
    cutoff = next(
        index for index, turn in enumerate(branch["turns"]) if turn[0] == cell["cutoff"]
    )
    required = [
        (role, content)
        for _, role, content in branch["turns"][: cutoff + 1]
        if role != "operator"
    ]
    source = [
        (item["role"], item["content"])
        for item in evidence["generation"]["source_messages"]
    ]
    review = json.loads(evidence["reviewer_request"]["messages"][1]["content"])
    reviewed = [(item["role"], item["content"]) for item in review["source_messages"]]
    return (
        all(item in source and item in reviewed for item in required)
        and source == reviewed
    )
