from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import require_operator
from ade_api.platform.dependencies import TestOrchestratorDependency
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.platform.openapi_metadata import TAG_TEST_CENTER

from .chat_memory_evaluations import ChatMemoryEvaluationArtifactUnavailable
from .contracts import (
    ChatMemoryEvaluationDetailResponse,
    ChatMemoryEvaluationListResponse,
    TestRunArtifactListResponse,
    TestRunArtifactReadResponse,
    TestRunListResponse,
    TestRunRecordResponse,
    TestRunRequest,
)


router = APIRouter(dependencies=[Depends(require_operator)])


@router.get(
    "/api/v2/test-center/chat-memory-evaluations",
    response_model=ChatMemoryEvaluationListResponse,
    tags=[TAG_TEST_CENTER],
    summary="List chat-memory evaluations",
)
async def list_chat_memory_evaluations(
    test_orchestrator: TestOrchestratorDependency,
):
    ensure_ade_api_enabled()
    return {"items": test_orchestrator.list_chat_memory_evaluations()}


@router.get(
    "/api/v2/test-center/chat-memory-evaluations/{run_id}",
    response_model=ChatMemoryEvaluationDetailResponse,
    response_model_exclude_none=True,
    tags=[TAG_TEST_CENTER],
    summary="Get chat-memory evaluation detail",
)
async def get_chat_memory_evaluation(
    run_id: str,
    test_orchestrator: TestOrchestratorDependency,
):
    ensure_ade_api_enabled()
    try:
        evaluation = test_orchestrator.get_chat_memory_evaluation(run_id)
    except ChatMemoryEvaluationArtifactUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if evaluation is None:
        raise HTTPException(
            status_code=404, detail="chat-memory evaluation run_id not found"
        )
    return evaluation


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
