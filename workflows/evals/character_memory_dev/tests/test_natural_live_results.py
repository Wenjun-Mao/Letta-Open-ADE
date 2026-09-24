from __future__ import annotations

import json

import pytest

from workflows.evals.character_memory_dev.natural_live_results import capture_scope
from workflows.evals.character_memory_dev.natural_live_transport import RequestScope


def test_capture_scope_requires_one_completed_file_per_reserved_request(
    tmp_path,
) -> None:
    scope = RequestScope("cell-a", generation_limit=2, embedding_limit=1)
    scope.reserve_local("generation")
    path = tmp_path / "cell-a-generation-001.json"
    path.write_text(
        json.dumps(
            {
                "scope": "cell-a",
                "kind": "generation",
                "number": 1,
                "outcome": "completed",
            }
        )
    )
    assert len(capture_scope(tmp_path, scope)) == 1

    scope.reserve_local("embedding")
    with pytest.raises(RuntimeError, match="missing embedding"):
        capture_scope(tmp_path, scope)
    (tmp_path / "cell-a-embedding-001.json").write_text(
        json.dumps(
            {"scope": "cell-a", "kind": "embedding", "number": 1, "outcome": "failed"}
        )
    )
    with pytest.raises(RuntimeError, match="failed or invalid embedding"):
        capture_scope(tmp_path, scope)
