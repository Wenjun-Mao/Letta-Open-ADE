from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.contracts import QualificationState
from ade_api.features.agent_runtime_v3.deployments import resolve_deployment
from ade_api.features.agent_runtime_v3.errors import UnqualifiedDeployment


CATALOG = {
    "items": [
        {
            "model_key": "source::model",
            "deployment": {
                "deployment_id": "deployment-1",
                "roles": ["conversation", "reviewer"],
                "lifecycle": "candidate",
                "fingerprint": {"sha256": "a" * 64, "context_settings": {}},
                "qualification": {
                    "role_results": [
                        {"role": "conversation", "qualified": False},
                        {"role": "reviewer", "qualified": True},
                    ]
                },
            },
        }
    ]
}


def test_development_mode_records_unqualified_deployment() -> None:
    result = resolve_deployment(
        CATALOG,
        route_alias="source::model",
        role="conversation",
        mode="development",
    )
    assert result.qualification_state is QualificationState.UNQUALIFIED
    assert result.fingerprint == "a" * 64


def test_release_mode_blocks_unqualified_deployment() -> None:
    with pytest.raises(UnqualifiedDeployment):
        resolve_deployment(
            CATALOG,
            route_alias="source::model",
            role="conversation",
            mode="release",
        )


def test_role_qualification_is_independent() -> None:
    result = resolve_deployment(
        CATALOG,
        route_alias="source::model",
        role="reviewer",
        mode="release",
    )
    assert result.qualification_state is QualificationState.QUALIFIED
