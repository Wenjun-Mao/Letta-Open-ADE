from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import IntEnum
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_platform_api.settings import get_settings


class PlatformRole(IntEnum):
    READER = 10
    OPERATOR = 20
    ADMIN = 30


@dataclass(frozen=True)
class PlatformPrincipal:
    role: PlatformRole
    key_name: str


_BEARER = HTTPBearer(auto_error=False)


def _configured_keys() -> tuple[tuple[str, str, PlatformRole], ...]:
    settings = get_settings()
    return tuple(
        (name, key, role)
        for name, key, role in (
            ("admin", settings.api_key, PlatformRole.ADMIN),
            ("operator", settings.operator_api_key, PlatformRole.OPERATOR),
            ("reader", settings.read_api_key, PlatformRole.READER),
        )
        if key
    )


def authenticate_platform_request(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_BEARER)],
) -> PlatformPrincipal:
    settings = get_settings()
    if not settings.auth_enabled:
        return PlatformPrincipal(role=PlatformRole.ADMIN, key_name="auth-disabled")

    configured = _configured_keys()
    if not configured:
        raise HTTPException(status_code=503, detail="Agent Platform API authentication is enabled but no API key is configured.")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer authentication is required.", headers={"WWW-Authenticate": "Bearer"})

    supplied = credentials.credentials.strip()
    for key_name, expected, role in configured:
        if secrets.compare_digest(supplied, expected):
            return PlatformPrincipal(role=role, key_name=key_name)
    raise HTTPException(status_code=401, detail="Invalid Agent Platform API key.", headers={"WWW-Authenticate": "Bearer"})


def require_role(minimum_role: PlatformRole):
    def dependency(
        principal: Annotated[PlatformPrincipal, Depends(authenticate_platform_request)],
    ) -> PlatformPrincipal:
        if principal.role < minimum_role:
            raise HTTPException(status_code=403, detail=f"This operation requires the {minimum_role.name.lower()} role.")
        return principal

    return dependency


require_reader = require_role(PlatformRole.READER)
require_operator = require_role(PlatformRole.OPERATOR)
require_admin = require_role(PlatformRole.ADMIN)
