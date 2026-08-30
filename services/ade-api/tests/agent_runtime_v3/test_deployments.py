from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.contracts import QualificationState
from ade_api.features.agent_runtime_v3.deployments import (
    resolve_deployment,
    validate_definition_execution,
)
from ade_api.features.agent_runtime_v3.errors import (
    RuntimeValidationError,
    UnqualifiedDeployment,
)


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


def _definition(*, qualified: bool = True, tool_names: list[str] | None = None):
    return {
        "qualification_state": "qualified" if qualified else "unqualified",
        "tool_names": tool_names or ["search_memory"],
        "deployment_snapshot": [
            {
                "role": "conversation",
                "route_alias": "source::chat",
                "deployment_id": "chat-deployment",
                "fingerprint": "c" * 64,
                "fingerprint_payload": {"sha256": "c" * 64},
            },
            {
                "role": "reviewer",
                "route_alias": "source::chat",
                "deployment_id": "chat-deployment",
                "fingerprint": "c" * 64,
                "fingerprint_payload": {"sha256": "c" * 64},
            },
            {
                "role": "retriever",
                "route_alias": "source::embedding",
                "deployment_id": "embedding-deployment",
                "fingerprint": "e" * 64,
                "fingerprint_payload": {"sha256": "e" * 64},
            },
        ],
    }


EXECUTION_CATALOG = {
    "items": [
        {
            "model_key": "source::chat",
            "deployment": {
                "deployment_id": "chat-deployment",
                "roles": ["conversation", "reviewer"],
                "lifecycle": "qualified",
                "fingerprint": {"sha256": "c" * 64},
                "qualification": {
                    "role_results": [
                        {"role": "conversation", "qualified": True},
                        {"role": "reviewer", "qualified": True},
                    ]
                },
            },
        },
        {
            "model_key": "source::embedding",
            "deployment": {
                "deployment_id": "embedding-deployment",
                "roles": ["retriever"],
                "lifecycle": "qualified",
                "fingerprint": {"sha256": "e" * 64},
                "qualification": {
                    "role_results": [{"role": "retriever", "qualified": True}]
                },
            },
        },
    ]
}


def test_turn_execution_revalidates_the_immutable_deployment_snapshot() -> None:
    validate_definition_execution(_definition(), EXECUTION_CATALOG, mode="release")
    stale = _definition()
    stale["deployment_snapshot"][0]["fingerprint"] = "x" * 64

    with pytest.raises(UnqualifiedDeployment, match="fingerprint is stale"):
        validate_definition_execution(stale, EXECUTION_CATALOG, mode="development")


def test_release_execution_rejects_development_definitions_and_tools() -> None:
    with pytest.raises(UnqualifiedDeployment, match="unqualified agent definition"):
        validate_definition_execution(
            _definition(qualified=False), EXECUTION_CATALOG, mode="release"
        )
    with pytest.raises(RuntimeValidationError, match="get_weather"):
        validate_definition_execution(
            _definition(tool_names=["search_memory", "get_weather"]),
            EXECUTION_CATALOG,
            mode="release",
        )
