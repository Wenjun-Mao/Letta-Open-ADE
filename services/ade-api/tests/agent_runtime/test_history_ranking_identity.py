"""H2's selected Qwen deployment cannot drift between ranking and H4."""

from __future__ import annotations

from copy import deepcopy

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.history_admission import HistoryProbe
from ade_api.features.agent_runtime.history_native_rank import HISTORY_VECTOR_RECIPE
from ade_api.features.agent_runtime.turn_history_setup import (
    validate_history_ranking_deployment,
)


def _deployment() -> dict:
    return {
        "route_alias": HISTORY_VECTOR_RECIPE["route"],
        "fingerprint": "c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086",
        "fingerprint_payload": {
            "artifact_reference": HISTORY_VECTOR_RECIPE["artifact_reference"],
            "artifact_revision": HISTORY_VECTOR_RECIPE["artifact_revision"],
            "sampling_settings": {"dimensions": HISTORY_VECTOR_RECIPE["dimensions"]},
        },
    }


@pytest.mark.parametrize(
    "recipe", ["probe_local_qwen_cosine", "probe_local_qwen_cosine_v2"]
)
def test_qwen_probe_requires_pinned_identity(recipe: str) -> None:
    deployment = _deployment()
    probe = HistoryProbe(
        arm="automatic_history",
        ranking_recipe=recipe,
        expected_embedding_fingerprint=deployment["fingerprint"],
    )
    validate_history_ranking_deployment(probe, deployment)
    with pytest.raises(RuntimeValidationError):
        HistoryProbe(arm="automatic_history", ranking_recipe=recipe)
    for field, value in (
        ("route_alias", "other::route"),
        ("fingerprint", "0" * 64),
    ):
        altered = deepcopy(deployment)
        altered[field] = value
        with pytest.raises(RuntimeValidationError):
            validate_history_ranking_deployment(probe, altered)
    altered = deepcopy(deployment)
    altered["fingerprint_payload"]["sampling_settings"]["dimensions"] = 768
    with pytest.raises(RuntimeValidationError):
        validate_history_ranking_deployment(probe, altered)
