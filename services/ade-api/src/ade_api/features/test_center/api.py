from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ade_api.platform.auth import require_admin
from ade_api.platform.dependencies import TestOrchestratorDependency
from ade_api.platform.feature_flags import ensure_ade_api_enabled
from ade_api.platform.openapi_metadata import TAG_TEST_CENTER

from .chat_memory_evaluations import ChatMemoryEvaluationArtifactUnavailable
from .agent_runtime_parity_evaluations import AgentRuntimeParityArtifactUnavailable
from .chat_memory_evaluation_comparisons import (
    ChatMemoryEvaluationComparisonUnavailable,
)
from .chat_memory_evaluation_decisions import (
    ChatMemoryEvaluationDecisionConflict,
)
from .contracts import (
    ChatMemoryEvaluationComparisonResponse,
    ChatMemoryEvaluationDecisionRequest,
    ChatMemoryEvaluationDecisionResponse,
    ChatMemoryEvaluationDetailResponse,
    ChatMemoryEvaluationListResponse,
    AgentRuntimeParityDetailResponse,
    AgentRuntimeParityListResponse,
    TestRunArtifactListResponse,
    TestRunArtifactReadResponse,
    TestRunListResponse,
    TestRunRecordResponse,
    TestRunRequest,
)


router = APIRouter(dependencies=[Depends(require_admin)])


@router.get(
    "/api/v2/test-center/agent-runtime-parity-evaluations",
    response_model=AgentRuntimeParityListResponse,
    tags=[TAG_TEST_CENTER],
    summary="List Agent Runtime paired baseline comparisons",
)
async def list_agent_runtime_parity_evaluations(
    test_orchestrator: TestOrchestratorDependency,
):
    ensure_ade_api_enabled()
    return {"items": test_orchestrator.list_agent_runtime_parity_evaluations()}


@router.get(
    "/api/v2/test-center/agent-runtime-parity-evaluations/{run_id}",
    response_model=AgentRuntimeParityDetailResponse,
    response_model_exclude_none=True,
    tags=[TAG_TEST_CENTER],
    summary="Get Agent Runtime paired baseline evidence",
)
async def get_agent_runtime_parity_evaluation(
    run_id: str,
    test_orchestrator: TestOrchestratorDependency,
):
    ensure_ade_api_enabled()
    try:
        evaluation = test_orchestrator.get_agent_runtime_parity_evaluation(run_id)
    except AgentRuntimeParityArtifactUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if evaluation is None:
        raise HTTPException(
            status_code=404,
            detail="agent-runtime paired baseline run_id not found",
        )
    return evaluation


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
    "/api/v2/test-center/chat-memory-evaluations/comparison",
    response_model=ChatMemoryEvaluationComparisonResponse,
    tags=[TAG_TEST_CENTER],
    summary="Compare two chat-memory evaluations",
)
async def compare_chat_memory_evaluations(
    baseline_run_id: str,
    candidate_run_id: str,
    test_orchestrator: TestOrchestratorDependency,
):
    ensure_ade_api_enabled()
    if baseline_run_id == candidate_run_id:
        raise HTTPException(
            status_code=400, detail="Baseline and candidate must be different runs"
        )
    try:
        comparison = test_orchestrator.compare_chat_memory_evaluations(
            baseline_run_id, candidate_run_id
        )
    except (
        ChatMemoryEvaluationArtifactUnavailable,
        ChatMemoryEvaluationComparisonUnavailable,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if comparison is None:
        raise HTTPException(status_code=404, detail="Evaluation run_id not found")
    return comparison


@router.post(
    "/api/v2/test-center/chat-memory-evaluations/{run_id}/decisions",
    response_model=ChatMemoryEvaluationDecisionResponse,
    tags=[TAG_TEST_CENTER],
    summary="Record a chat-memory evaluation decision",
)
async def record_chat_memory_evaluation_decision(
    run_id: str,
    request: ChatMemoryEvaluationDecisionRequest,
    test_orchestrator: TestOrchestratorDependency,
):
    ensure_ade_api_enabled()
    try:
        decision = test_orchestrator.record_chat_memory_evaluation_decision(
            run_id, **request.model_dump()
        )
    except (
        ChatMemoryEvaluationArtifactUnavailable,
        ChatMemoryEvaluationDecisionConflict,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if decision is None:
        raise HTTPException(status_code=404, detail="Evaluation run_id not found")
    return decision


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
