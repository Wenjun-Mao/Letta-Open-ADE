from __future__ import annotations

import os

from fastapi import HTTPException


def is_truthy(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def ade_api_enabled() -> bool:
    return is_truthy(os.getenv("ADE_API_ENABLED", "1"))


def ensure_ade_api_enabled() -> None:
    if ade_api_enabled():
        return
    raise HTTPException(
        status_code=503,
        detail="ADE API is disabled by ADE_API_ENABLED.",
    )
