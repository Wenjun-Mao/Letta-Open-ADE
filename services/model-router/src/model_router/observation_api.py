"""Authenticated private request exports and per-request correlation context."""

from fastapi import FastAPI, Header, HTTPException, Query, Request

from model_router.request_observations import (
    list_observations,
    observation_context,
    read_observation,
)


def install_observation_api(application: FastAPI, require_auth) -> None:
    @application.middleware("http")
    async def bind_context(request: Request, call_next):
        with observation_context(request.headers):
            return await call_next(request)

    @application.get("/v1/router/observations")
    def get_observations(
        run_id: str | None = Query(default=None, max_length=160),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=100),
        authorization: str | None = Header(default=None),
    ):
        require_auth(authorization)
        return list_observations(run_id=run_id, offset=offset, limit=limit)

    @application.get("/v1/router/observations/{request_id}")
    def get_observation(
        request_id: str, authorization: str | None = Header(default=None)
    ):
        require_auth(authorization)
        try:
            result = read_observation(request_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid observation identity")
        if result is None:
            raise HTTPException(status_code=404, detail="Observation unavailable")
        return result
