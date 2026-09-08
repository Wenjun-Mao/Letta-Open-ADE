from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.features.model_catalog import runtime_options
from ade_api.features.prompt_center import persona_option_entries, prompt_option_entries
from ade_api.platform.auth import require_admin
from ade_api.platform.dependencies import (
    ModelRouterClientDependency,
    PromptPersonaRegistryDependency,
    TestOrchestratorDependency,
)
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.platform.openapi_metadata import TAG_TEST_CENTER

from .contracts import (
    TestCenterOptionsResponse,
    TestRunArtifactListResponse,
    TestRunArtifactReadResponse,
    TestRunListResponse,
    TestRunRecordResponse,
    TestRunRequest,
)
from .run_descriptors import (
    AGENT_RUNTIME_DIAGNOSTIC_CASE_KEYS,
    CHAT_MEMORY_EVALUATION_FIXTURES,
    DEFAULT_AGENT_RUNTIME_ACCEPTANCE_CONFIG,
    DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG,
)


router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/api/v2/test-center/options",
    response_model=TestCenterOptionsResponse,
    tags=[TAG_TEST_CENTER],
    summary="Get canonical Test Center launch options",
)
async def get_test_center_options(
    model_router_client: ModelRouterClientDependency,
    prompt_registry: PromptPersonaRegistryDependency,
):
    ensure_ade_api_enabled()
    models, embeddings = runtime_options(
        "chat",
        model_router_client=model_router_client,
        force_refresh=False,
    )
    return {
        "run_types": [
            {"key": "chat_memory_eval", "label": "Behavior evaluation"},
            {
                "key": "agent_runtime_acceptance",
                "label": "Native runtime qualification",
            },
            {"key": "ade_api_e2e_check", "label": "Current-stack smoke"},
        ],
        "catalog": {
            "models": _catalog_options(models),
            "embeddings": _catalog_options(embeddings),
            "prompts": _catalog_options(prompt_option_entries(prompt_registry, "chat")),
            "personas": _catalog_options(
                persona_option_entries(prompt_registry, "chat")
            ),
        },
        "chat_memory_eval": {
            "defaults": DEFAULT_CHAT_MEMORY_EVALUATION_CONFIG,
            "fixtures": [
                {"key": key, "label": label}
                for key, label in CHAT_MEMORY_EVALUATION_FIXTURES
            ],
        },
        "agent_runtime_acceptance": {
            "defaults": DEFAULT_AGENT_RUNTIME_ACCEPTANCE_CONFIG,
            "cases": [
                {"key": key, "label": key.replace("_", " ").title()}
                for key in AGENT_RUNTIME_DIAGNOSTIC_CASE_KEYS
            ],
        },
        "current_stack_smoke": {"run_type": "ade_api_e2e_check"},
    }


def _catalog_options(items: list[dict]) -> list[dict[str, object]]:
    return [
        {
            "key": str(item.get("key") or ""),
            "label": str(item.get("label") or item.get("key") or ""),
            "available": bool(item.get("available", True)),
        }
        for item in items
        if str(item.get("key") or "").strip()
    ]


@router.get(
    "/api/v2/test-center/runs",
    response_model=TestRunListResponse,
    tags=[TAG_TEST_CENTER],
    summary="List orchestrated test runs",
)
async def list_test_runs(test_orchestrator: TestOrchestratorDependency):
    ensure_ade_api_enabled()
    return {"items": test_orchestrator.list_runs()}


@router.post(
    "/api/v2/test-center/runs",
    response_model=TestRunRecordResponse,
    tags=[TAG_TEST_CENTER],
    summary="Create orchestrated test run",
)
async def create_test_run(
    request: TestRunRequest,
    test_orchestrator: TestOrchestratorDependency,
):
    ensure_ade_api_enabled()
    try:
        return test_orchestrator.create_run(**request.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/api/v2/test-center/runs/{run_id}",
    response_model=TestRunRecordResponse,
    tags=[TAG_TEST_CENTER],
    summary="Get orchestrated test run",
)
async def get_test_run(run_id: str, test_orchestrator: TestOrchestratorDependency):
    ensure_ade_api_enabled()
    run = test_orchestrator.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id not found")
    return run


@router.post(
    "/api/v2/test-center/runs/{run_id}/cancel",
    response_model=TestRunRecordResponse,
    tags=[TAG_TEST_CENTER],
    summary="Cancel orchestrated test run",
)
async def cancel_test_run(
    run_id: str,
    test_orchestrator: TestOrchestratorDependency,
):
    ensure_ade_api_enabled()
    run = test_orchestrator.cancel_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_id not found")
    return run


@router.get(
    "/api/v2/test-center/runs/{run_id}/artifacts",
    response_model=TestRunArtifactListResponse,
    tags=[TAG_TEST_CENTER],
    summary="List test run artifacts",
)
async def list_test_run_artifacts(
    run_id: str,
    test_orchestrator: TestOrchestratorDependency,
):
    ensure_ade_api_enabled()
    artifacts = test_orchestrator.list_artifacts(run_id)
    if artifacts is None:
        raise HTTPException(status_code=404, detail="run_id not found")
    return {"run_id": run_id, "items": artifacts}


@router.get(
    "/api/v2/test-center/runs/{run_id}/artifacts/{artifact_id}",
    response_model=TestRunArtifactReadResponse,
    tags=[TAG_TEST_CENTER],
    summary="Read test run artifact content",
)
async def read_test_run_artifact(
    run_id: str,
    artifact_id: str,
    test_orchestrator: TestOrchestratorDependency,
    max_lines: int = 400,
):
    ensure_ade_api_enabled()
    payload = test_orchestrator.read_artifact(
        run_id,
        artifact_id,
        max_lines=max_lines,
    )
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="run_id or artifact_id not found",
        )
    return payload
