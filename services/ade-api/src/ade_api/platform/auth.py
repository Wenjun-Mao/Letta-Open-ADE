from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import IntEnum
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ade_api.platform.settings import get_settings


class AdeRole(IntEnum):
    READER = 10
    OPERATOR = 20
    ADMIN = 30


@dataclass(frozen=True)
class AdePrincipal:
    role: AdeRole
    key_name: str


_BEARER = HTTPBearer(auto_error=False)


def _configured_keys() -> tuple[tuple[str, str, AdeRole], ...]:
    settings = get_settings()
    return tuple(
        (name, key, role)
        for name, key, role in (
            ("admin", settings.admin_key, AdeRole.ADMIN),
            ("operator", settings.operator_key, AdeRole.OPERATOR),
            ("reader", settings.reader_key, AdeRole.READER),
        )
        if key
    )


def authenticate_ade_request(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_BEARER)],
) -> AdePrincipal:
    settings = get_settings()
    if not settings.auth_enabled:
        return AdePrincipal(role=AdeRole.ADMIN, key_name="auth-disabled")

    configured = _configured_keys()
    if not configured:
        raise HTTPException(
            status_code=503,
            detail="ADE API authentication is enabled but no API key is configured.",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supplied = credentials.credentials.strip()
    for key_name, expected, role in configured:
        if secrets.compare_digest(supplied, expected):
            return AdePrincipal(role=role, key_name=key_name)
    raise HTTPException(
        status_code=401,
        detail="Invalid ADE API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(minimum_role: AdeRole):
    def dependency(
        principal: Annotated[AdePrincipal, Depends(authenticate_ade_request)],
    ) -> AdePrincipal:
        if principal.role < minimum_role:
            raise HTTPException(
                status_code=403,
                detail=f"This operation requires the {minimum_role.name.lower()} role.",
            )
        return principal

    return dependency


require_reader = require_role(AdeRole.READER)
require_operator = require_role(AdeRole.OPERATOR)
require_admin = require_role(AdeRole.ADMIN)
