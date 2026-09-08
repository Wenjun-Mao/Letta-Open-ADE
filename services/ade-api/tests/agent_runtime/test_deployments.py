from __future__ import annotations

import pytest

from ade_api.features.agent_runtime.contracts import QualificationState
from ade_api.features.agent_runtime.deployments import (
    resolve_deployment,
    validate_definition_execution,
)
from ade_api.features.agent_runtime.definition_service import normalize_route_alias
from ade_api.features.agent_runtime.errors import (
    RuntimeValidationError,
    UnqualifiedDeployment,
)


POLICY_HASHES = {
    "prompt": "1" * 64,
    "tool": "2" * 64,
    "schema": "3" * 64,
    "retrieval": "4" * 64,
}
AGENT_BUNDLE = {
    "prompt_key": None,
    "persona_key": None,
    "tool_names": ["search_memory"],
}


def _fingerprint(sha256: str) -> dict[str, object]:
    return {
        "sha256": sha256,
        "context_settings": {},
        "prompt_policy_sha256": POLICY_HASHES["prompt"],
        "tool_policy_sha256": POLICY_HASHES["tool"],
        "schema_policy_sha256": POLICY_HASHES["schema"],
        "retrieval_policy_sha256": POLICY_HASHES["retrieval"],
    }


CATALOG = {
    "items": [
        {
            "model_key": "source::model",
            "deployment": {
                "deployment_id": "deployment-1",
                "roles": ["conversation", "reviewer"],
                "lifecycle": "candidate",
                "fingerprint": _fingerprint("a" * 64),
                "qualification": {
                    "qualified": False,
                    "stale_round_count": 0,
                    "role_results": [
                        {
                            "role": "conversation",
                            "observed_rounds": 0,
                            "consecutive_passing_rounds": 0,
                            "qualified": False,
                        },
                        {
                            "role": "reviewer",
                            "observed_rounds": 3,
                            "consecutive_passing_rounds": 3,
                            "qualified": True,
                        },
                    ],
                },
            },
        }
    ]
}


def test_route_alias_requires_canonical_router_identity() -> None:
    assert normalize_route_alias("source::model") == "source::model"

    with pytest.raises(RuntimeValidationError, match="source::model"):
        normalize_route_alias("openai-proxy/source::model")


def test_development_mode_records_unqualified_deployment() -> None:
    result = resolve_deployment(
        CATALOG,
        route_alias="source::model",
        role="conversation",
        mode="development",
    )
    assert result.qualification_state is QualificationState.UNQUALIFIED
    assert result.fingerprint == "a" * 64


def test_development_mode_resolves_stable_alias_from_discovered_route() -> None:
    catalog = {
        "items": [
            {
                **CATALOG["items"][0],
                "model_key": "source::provider-advertised-name",
                "route_aliases": [
                    "source::stable",
                    "source::provider-advertised-name",
                ],
            }
        ]
    }

    result = resolve_deployment(
        catalog,
        route_alias="source::stable",
        role="conversation",
        mode="development",
    )

    assert result.route_alias == "source::stable"
    assert result.deployment_id == "deployment-1"


def test_release_mode_blocks_unqualified_deployment() -> None:
    with pytest.raises(UnqualifiedDeployment):
        resolve_deployment(
            CATALOG,
            route_alias="source::model",
            role="conversation",
            mode="release",
        )


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
                "fingerprint_payload": _fingerprint("c" * 64),
            },
            {
                "role": "reviewer",
                "route_alias": "source::chat",
                "deployment_id": "chat-deployment",
                "fingerprint": "c" * 64,
                "fingerprint_payload": _fingerprint("c" * 64),
            },
            {
                "role": "retriever",
                "route_alias": "source::embedding",
                "deployment_id": "embedding-deployment",
                "fingerprint": "e" * 64,
                "fingerprint_payload": _fingerprint("e" * 64),
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
                "fingerprint": _fingerprint("c" * 64),
                "qualification": {
                    "qualified": True,
                    "stale_round_count": 0,
                    "role_results": [
                        {
                            "role": "conversation",
                            "observed_rounds": 3,
                            "consecutive_passing_rounds": 3,
                            "qualified": True,
                        },
                        {
                            "role": "reviewer",
                            "observed_rounds": 3,
                            "consecutive_passing_rounds": 3,
                            "qualified": True,
                        },
                    ],
                },
            },
        },
        {
            "model_key": "source::embedding",
            "deployment": {
                "deployment_id": "embedding-deployment",
                "roles": ["retriever"],
                "lifecycle": "qualified",
                "fingerprint": _fingerprint("e" * 64),
                "qualification": {
                    "qualified": True,
                    "stale_round_count": 0,
                    "role_results": [
                        {
                            "role": "retriever",
                            "observed_rounds": 3,
                            "consecutive_passing_rounds": 3,
                            "qualified": True,
                        }
                    ],
                },
            },
        },
    ]
}


def test_turn_execution_revalidates_the_immutable_deployment_snapshot() -> None:
    validate_definition_execution(
        _definition(),
        EXECUTION_CATALOG,
        mode="release",
        expected_policy_hashes=POLICY_HASHES,
        expected_route_aliases={
            "conversation": "source::chat",
            "reviewer": "source::chat",
            "retriever": "source::embedding",
        },
        expected_agent_bundle=AGENT_BUNDLE,
        source_clean=True,
    )
    stale = _definition()
    stale["deployment_snapshot"][0]["fingerprint"] = "x" * 64

    with pytest.raises(UnqualifiedDeployment, match="fingerprint is stale"):
        validate_definition_execution(stale, EXECUTION_CATALOG, mode="development")


def test_release_execution_rejects_development_definitions_and_tools() -> None:
    with pytest.raises(UnqualifiedDeployment, match="unqualified agent definition"):
        validate_definition_execution(
            _definition(qualified=False),
            EXECUTION_CATALOG,
            mode="release",
            expected_policy_hashes=POLICY_HASHES,
            expected_route_aliases={
                "conversation": "source::chat",
                "reviewer": "source::chat",
                "retriever": "source::embedding",
            },
            expected_agent_bundle=AGENT_BUNDLE,
            source_clean=True,
        )
    with pytest.raises(UnqualifiedDeployment, match="bundle is outside"):
        validate_definition_execution(
            _definition(tool_names=["search_memory", "get_weather"]),
            EXECUTION_CATALOG,
            mode="release",
            expected_policy_hashes=POLICY_HASHES,
            expected_route_aliases={
                "conversation": "source::chat",
                "reviewer": "source::chat",
                "retriever": "source::embedding",
            },
            expected_agent_bundle=AGENT_BUNDLE,
            source_clean=True,
        )


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"source_clean": False}, "clean source tree"),
        (
            {"expected_policy_hashes": {**POLICY_HASHES, "schema": "9" * 64}},
            "stale runtime policy",
        ),
        (
            {
                "expected_route_aliases": {
                    "conversation": "other::chat",
                    "reviewer": "source::chat",
                    "retriever": "source::embedding",
                }
            },
            "outside the qualified Agent Studio contract",
        ),
    ],
)
def test_release_execution_fails_closed_on_release_contract_drift(
    override: dict[str, object], message: str
) -> None:
    kwargs = {
        "expected_policy_hashes": POLICY_HASHES,
        "expected_route_aliases": {
            "conversation": "source::chat",
            "reviewer": "source::chat",
            "retriever": "source::embedding",
        },
        "expected_agent_bundle": AGENT_BUNDLE,
        "source_clean": True,
        **override,
    }

    with pytest.raises(UnqualifiedDeployment, match=message):
        validate_definition_execution(
            _definition(), EXECUTION_CATALOG, mode="release", **kwargs
        )


def test_release_execution_rejects_an_evidence_bundle_mismatch() -> None:
    with pytest.raises(UnqualifiedDeployment, match="bundle is outside"):
        validate_definition_execution(
            _definition(),
            EXECUTION_CATALOG,
            mode="release",
            expected_policy_hashes=POLICY_HASHES,
            expected_route_aliases={
                "conversation": "source::chat",
                "reviewer": "source::chat",
                "retriever": "source::embedding",
            },
            expected_agent_bundle={
                "prompt_key": "reviewed_prompt",
                "persona_key": "reviewed_persona",
                "tool_names": ["search_memory"],
            },
            source_clean=True,
        )
