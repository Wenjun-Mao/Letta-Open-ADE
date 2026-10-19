"""Private captures are not reader-visible product activity."""

from uuid import UUID

from fastapi import APIRouter, Depends

from ade_api.platform.auth import require_operator

from .api_boundary import call_runtime
from .dependencies import AgentRuntimeServiceDependency
from .private_observation_contracts import PrivateObservationResponse


router = APIRouter()


@router.get(
    "/private-observations/runs/{run_id}",
    response_model=PrivateObservationResponse,
    dependencies=[Depends(require_operator)],
    summary="Export opt-in development-workspace observations for one saved run",
)
async def read_run_observations(run_id: UUID, service: AgentRuntimeServiceDependency):
    return await call_runtime(service.private_observations.read(str(run_id)))
