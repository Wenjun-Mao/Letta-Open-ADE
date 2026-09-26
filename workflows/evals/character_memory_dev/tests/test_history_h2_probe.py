"""Finite synthetic schedule and held-out gate before any live Qwen call."""

from __future__ import annotations

import asyncio
import json

import pytest

from workflows.evals.character_memory_dev.history_h2_probe import run_phase
from ade_api.features.agent_runtime.history_native_rank import (
    HISTORY_EMBEDDING_ROUTE,
    HISTORY_VECTOR_RECIPE,
)


class FakeEmbeddingClient:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.calls: list[list[str]] = []

    async def catalog(self):
        return {
            "items": [
                {
                    "model_key": HISTORY_EMBEDDING_ROUTE,
                    "deployment": {
                        "fingerprint": {
                            "sha256": "1" * 64,
                            "artifact_reference": HISTORY_VECTOR_RECIPE[
                                "artifact_reference"
                            ],
                            "artifact_revision": HISTORY_VECTOR_RECIPE[
                                "artifact_revision"
                            ],
                            "sampling_settings": {"dimensions": 1024},
                        }
                    },
                }
            ]
            if self.available
            else []
        }

    async def embed(self, *, inputs, timeout_seconds):
        self.calls.append(inputs)
        assert timeout_seconds == 180
        return [[1.0] * 1024 for _ in inputs]


def test_development_cells_are_finite_and_records_are_source_scoped(tmp_path) -> None:
    provider = FakeEmbeddingClient()
    output = tmp_path / "development.json"
    result = asyncio.run(
        run_phase(phase="development", output=output, embeddings=provider)
    )
    assert [cell["case_id"] for cell in result["cells"]] == [
        "mandarin_paraphrase_coffee",
        "mandarin_paraphrase_coffee",
        "mandarin_paraphrase_concern",
        "mandarin_paraphrase_concern",
        "unrelated_probe",
        "unrelated_probe",
    ]
    assert len(provider.calls) == result["embedding_dispatches"] == 6
    assert all(cell["status"] == "succeeded" for cell in result["cells"])
    assert all(
        cell["source_contract"] == "frozen_synthetic_fixture_no_native_guard"
        for cell in result["cells"]
    )
    assert all(
        "minimum_evidence" not in json.dumps(call, ensure_ascii=False)
        for call in provider.calls
    )
    assert output.exists()
    assert result["selection"]["selected"] is None
    with pytest.raises(ValueError, match="adequate development"):
        asyncio.run(
            run_phase(
                phase="heldout",
                output=tmp_path / "heldout.json",
                development_result=output,
                embeddings=provider,
            )
        )


def test_missing_provider_identity_marks_all_cells_unrun_without_dispatch(
    tmp_path,
) -> None:
    provider = FakeEmbeddingClient(available=False)
    result = asyncio.run(
        run_phase(
            phase="development",
            output=tmp_path / "unavailable.json",
            embeddings=provider,
        )
    )
    assert len(result["cells"]) == 6
    assert {cell["status"] for cell in result["cells"]} == {"unrun"}
    assert result["embedding_dispatches"] == 0
    assert provider.calls == []
