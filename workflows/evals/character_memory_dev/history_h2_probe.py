"""One-shot synthetic H2 ranking schedule; native history uses its own PG guard."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from ade_api.features.agent_runtime.history_native_rank import (
    HISTORY_EMBEDDING_ROUTE,
    HISTORY_VECTOR_RECIPE,
)
from ade_api.features.agent_runtime.history_ranking import (
    RECIPES,
    assess_rank,
    choose_ranker,
    cosine_score,
    document_text,
    literal_score,
    query_text,
    rank_windows,
    vector_recipe_identity,
)

from .history_fixture_contract import validate_history_cases
from .history_h2_router import ContainerEmbeddingClient

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "history_recall"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _provider_identity(catalog: dict[str, Any]) -> dict[str, Any]:
    items = catalog.get("items", [])
    if len(items) != 1 or items[0].get("model_key") != HISTORY_EMBEDDING_ROUTE:
        raise ValueError("frozen Qwen embedding route is unavailable")
    fingerprint = items[0].get("deployment", {}).get("fingerprint", {})
    if (
        fingerprint.get("artifact_reference")
        != HISTORY_VECTOR_RECIPE["artifact_reference"]
        or fingerprint.get("artifact_revision")
        != HISTORY_VECTOR_RECIPE["artifact_revision"]
        or fingerprint.get("sampling_settings", {}).get("dimensions")
        != HISTORY_VECTOR_RECIPE["dimensions"]
    ):
        raise ValueError("configured Qwen artifact identity differs from frozen recipe")
    return {
        "route": HISTORY_EMBEDDING_ROUTE,
        "artifact_reference": fingerprint["artifact_reference"],
        "artifact_revision": fingerprint["artifact_revision"],
        "dimensions": HISTORY_VECTOR_RECIPE["dimensions"],
        "deployment_fingerprint": fingerprint.get("sha256"),
    }


def _development_cases(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": case["id"],
            "exchanges": case["exchanges"],
            "current_user": case["query"],
            "local_suffix": [],
            "minimum_evidence": case["minimum_evidence"],
            "omitted_scope_ids": [],
        }
        for case in fixture["cases"]
    ]


def _heldout_cases(
    fixture: dict[str, Any], case_ids: list[str]
) -> list[dict[str, Any]]:
    by_id = {case["id"]: case for case in fixture["cases"]}
    cases = []
    for case_id in case_ids:
        case = by_id[case_id]
        eligible = [
            item
            for item in case["setup"]
            if all(
                item.get(key, "primary") == "primary"
                for key in ("workspace", "subject", "root")
            )
            and item.get("purpose", "evaluation") == "evaluation"
        ]
        local_suffix = [
            {"role": role, "content": item[field]}
            for item in eligible
            if item["chat"] == case["target"]["chat"]
            for role, field in (("user", "user"), ("assistant", "assistant"))
        ]
        cases.append(
            {
                "id": case_id,
                "exchanges": eligible,
                "current_user": case["target"]["user"],
                "local_suffix": local_suffix,
                "minimum_evidence": sorted(
                    {source.split(":", 1)[0] for source in case["required_evidence"]}
                ),
                "omitted_scope_ids": [
                    item["id"] for item in case["setup"] if item not in eligible
                ],
            }
        )
    return cases


async def _rank_case(
    case: dict[str, Any],
    recipe: str,
    embeddings: ContainerEmbeddingClient,
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    documents = {item["id"]: document_text(item) for item in case["exchanges"]}
    if len(documents) != len(case["exchanges"]):
        raise ValueError("duplicate frozen fixture exchange ID")
    query = query_text(case["current_user"], case["local_suffix"])
    receipts: list[dict[str, Any]] = []
    started = time.monotonic()
    if recipe == "literal_token_match":
        scores = {key: literal_score(query, text) for key, text in documents.items()}
        recipe_identity = vector_recipe_identity(
            {
                "literal_recipe": "casefolded alphanumeric character bigram query overlap fraction"
            },
            documents,
        )
    else:
        recipe_identity = vector_recipe_identity(HISTORY_VECTOR_RECIPE, documents)
        vectors = []
        for kind, inputs in (
            ("documents", list(documents.values())),
            ("query", [query]),
        ):
            before = time.monotonic()
            receipt = {
                "kind": kind,
                "model": HISTORY_EMBEDDING_ROUTE,
                "input_hashes": [_hash(value) for value in inputs],
                "input_count": len(inputs),
            }
            try:
                result = await embeddings.embed(
                    inputs=inputs, timeout_seconds=timeout_seconds
                )
                receipt.update(
                    status="succeeded",
                    elapsed_seconds=time.monotonic() - before,
                    vector_count=len(result),
                )
                vectors.append(result)
            except Exception as exc:
                receipt.update(
                    status="failed",
                    elapsed_seconds=time.monotonic() - before,
                    error_type=type(exc).__name__,
                )
                receipts.append(receipt)
                raise RankingDispatchFailure(receipts) from exc
            receipts.append(receipt)
        scores = {
            exchange_id: cosine_score(
                vectors[1][0], vector, dimensions=HISTORY_VECTOR_RECIPE["dimensions"]
            )
            for exchange_id, vector in zip(documents, vectors[0], strict=True)
        }
    ranked = rank_windows(case["exchanges"], scores)
    return {
        "status": "succeeded",
        "case_id": case["id"],
        "recipe": recipe,
        "source_contract": "frozen_synthetic_fixture_no_native_guard",
        "corpus_ids": list(documents),
        "omitted_scope_ids": case["omitted_scope_ids"],
        "document_hashes": {key: _hash(value) for key, value in documents.items()},
        "query_hash": _hash(query),
        "recipe_identity": recipe_identity,
        "scores": scores,
        "ranked": ranked,
        "assessment": assess_rank(list(documents), ranked, case["minimum_evidence"]),
        "embedding_receipts": receipts,
        "elapsed_seconds": time.monotonic() - started,
    }


class RankingDispatchFailure(Exception):
    def __init__(self, receipts: list[dict[str, Any]]) -> None:
        self.receipts = receipts


def _save(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


async def run_phase(
    *,
    phase: str,
    output: Path,
    embeddings: ContainerEmbeddingClient,
    development_result: Path | None = None,
) -> dict[str, Any]:
    contract_path = FIXTURES / "contract.json"
    development_path = FIXTURES / "ranking_development.json"
    heldout_path = FIXTURES / "cases.json"
    contract = json.loads(contract_path.read_text())
    development = json.loads(development_path.read_text())
    heldout = json.loads(heldout_path.read_text())
    validate_history_cases(contract, heldout)
    case_ids = (
        contract["ranking"]["development_cases"]
        if phase == "development"
        else contract["ranking"]["held_out_cases"]
    )
    cases = (
        _development_cases(development)
        if phase == "development"
        else _heldout_cases(heldout, case_ids)
    )
    if [case["id"] for case in cases] != case_ids:
        raise ValueError("ranking cases differ from frozen schedule")
    if any(
        len(case["exchanges"]) > contract["corpus"]["max_complete_exchanges"]
        for case in cases
    ):
        raise ValueError("synthetic ranking corpus exceeds frozen read cap")
    result: dict[str, Any] = {
        "phase": phase,
        "source_contract": "frozen_synthetic_fixture_no_native_guard",
        "contract_sha256": _file_hash(contract_path),
        "development_fixture_sha256": _file_hash(development_path),
        "heldout_fixture_sha256": _file_hash(heldout_path),
        "vector_recipe": HISTORY_VECTOR_RECIPE,
        "cells": [],
        "embedding_dispatches": 0,
    }
    selected = None
    if phase == "heldout":
        if development_result is None:
            raise ValueError("held-out phase requires the completed development result")
        prior = json.loads(development_result.read_text())
        if (
            prior.get("contract_sha256") != result["contract_sha256"]
            or prior.get("development_fixture_sha256")
            != result["development_fixture_sha256"]
            or prior.get("selection", {}).get("selected") not in RECIPES
            or prior.get("provider_identity") is None
        ):
            raise ValueError(
                "held-out gate does not match frozen adequate development result"
            )
        expected_cells = {
            (case_id, recipe)
            for case_id in contract["ranking"]["development_cases"]
            for recipe in RECIPES
        }
        observed_cells = {
            (cell["case_id"], cell["recipe"])
            for cell in prior.get("cells", [])
            if cell.get("status") == "succeeded"
        }
        if observed_cells != expected_cells or len(prior["cells"]) != len(
            expected_cells
        ):
            raise ValueError("held-out gate has incomplete development observations")
        assessments = {
            recipe: {
                cell["case_id"]: cell["assessment"]
                for cell in prior["cells"]
                if cell["recipe"] == recipe
            }
            for recipe in RECIPES
        }
        decision = choose_ranker(
            assessments,
            contract["ranking"]["development_cases"][:2],
            contract["ranking"]["development_cases"][2],
        )
        if decision["selected"] != prior["selection"]["selected"]:
            raise ValueError("held-out gate selection differs from frozen rule")
        selected = decision["selected"]
    try:
        result["provider_identity"] = _provider_identity(await embeddings.catalog())
        if (
            phase == "heldout"
            and result["provider_identity"] != prior["provider_identity"]
        ):
            raise ValueError("held-out provider identity differs from development")
    except Exception as exc:
        result["provider_identity_error"] = type(exc).__name__
        result["cells"] = [
            {
                "case_id": case["id"],
                "recipe": recipe,
                "status": "unrun",
                "reason": "provider identity unavailable",
            }
            for case in cases
            for recipe in (RECIPES if phase == "development" else (selected,))
        ]
        _save(output, result)
        return result
    for case in cases:
        for recipe in RECIPES if phase == "development" else (selected,):
            try:
                cell = await _rank_case(
                    case,
                    recipe,
                    embeddings,
                    timeout_seconds=contract["binding"]["turn_timeout_seconds"],
                )
            except RankingDispatchFailure as exc:
                cell = {
                    "case_id": case["id"],
                    "recipe": recipe,
                    "status": "failed",
                    "reason": "embedding dispatch failed",
                    "embedding_receipts": exc.receipts,
                }
            except Exception as exc:
                cell = {
                    "case_id": case["id"],
                    "recipe": recipe,
                    "status": "failed",
                    "reason": type(exc).__name__,
                    "embedding_receipts": [],
                }
            result["cells"].append(cell)
            result["embedding_dispatches"] += len(cell["embedding_receipts"])
            _save(output, result)
    if phase == "development":
        if all(cell["status"] == "succeeded" for cell in result["cells"]):
            assessments = {
                recipe: {
                    cell["case_id"]: cell["assessment"]
                    for cell in result["cells"]
                    if cell["recipe"] == recipe
                }
                for recipe in RECIPES
            }
            result["selection"] = choose_ranker(assessments, case_ids[:2], case_ids[2])
        else:
            result["selection"] = {
                "selected": None,
                "reason": "incomplete development cells",
            }
    _save(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("development", "heldout"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--development-result", type=Path)
    parser.add_argument("--router-container", default="letta-open-ade-ade-api-1")
    args = parser.parse_args()
    result = asyncio.run(
        run_phase(
            phase=args.phase,
            output=args.output,
            embeddings=ContainerEmbeddingClient(args.router_container),
            development_result=args.development_result,
        )
    )
    print(
        json.dumps(
            {
                "phase": args.phase,
                "output": str(args.output),
                "selection": result.get("selection", {}).get("selected"),
                "embedding_dispatches": result["embedding_dispatches"],
                "succeeded": sum(
                    cell["status"] == "succeeded" for cell in result["cells"]
                ),
                "failed": sum(cell["status"] == "failed" for cell in result["cells"]),
                "unrun": sum(cell["status"] == "unrun" for cell in result["cells"]),
            }
        )
    )


if __name__ == "__main__":
    main()
