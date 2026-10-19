"""Opt-in private observations of the actual upstream HTTP request."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import time
import tempfile
from uuid import UUID, uuid4

import httpx

from model_router.dispatch_lease import check_dispatch_lease
from model_router.settings import get_settings


_CONTEXT: ContextVar[dict | None] = ContextVar(
    "router_observation_context", default=None
)
_HEADERS = {
    "x-ade-observation-role": "role",
    "x-ade-observation-phase": "phase",
    "x-ade-run-id": "run_id",
    "x-ade-attempt-id": "attempt_id",
    "x-ade-conversation-id": "conversation_id",
    "x-ade-workspace-id": "workspace_id",
    "x-ade-subject-id": "subject_id",
    "x-ade-character-root-id": "character_root_id",
    "x-ade-operation-id": "operation_id",
}
_PRIVATE_FIELDS = {
    "authorization",
    "api_key",
    "access_token",
    "refresh_token",
    "password",
    "reasoning_content",
    "encrypted_content",
}


class ObservationUnavailable(RuntimeError):
    pass


@contextmanager
def observation_context(headers):
    metadata: dict = {}
    for header, field in _HEADERS.items():
        value = headers.get(header)
        if value is None:
            continue
        if re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
            metadata[field] = value
        else:
            metadata.setdefault("invalid_header_fields", []).append(field)
    token = _CONTEXT.set(metadata)
    try:
        yield
    finally:
        _CONTEXT.reset(token)


def bind_router_model(model: str) -> None:
    metadata = _CONTEXT.get()
    if metadata is not None:
        metadata["router_model"] = model


def _private_fields(value: object) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in _PRIVATE_FIELDS for key in value) or any(
            _private_fields(item) for item in value.values()
        )
    return isinstance(value, list) and any(_private_fields(item) for item in value)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".observation-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(
                json.dumps(value, ensure_ascii=False, allow_nan=False).encode() + b"\n"
            )
            target.flush()
            os.fsync(target.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def _visible_message(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    return {
        key: value[key]
        for key in ("role", "content", "tool_calls", "refusal")
        if key in value and not _private_fields(value[key])
    }


def visible_response(value: dict) -> dict:
    result = {
        key: value[key]
        for key in ("id", "model", "object", "usage", "created")
        if key in value
    }
    if isinstance(value.get("choices"), list):
        result["choices"] = [
            {
                "index": choice.get("index"),
                "finish_reason": choice.get("finish_reason"),
                **(
                    {"message": _visible_message(choice["message"])}
                    if "message" in choice
                    else {}
                ),
                **(
                    {"delta": _visible_message(choice["delta"])}
                    if "delta" in choice
                    else {}
                ),
            }
            for choice in value["choices"]
            if isinstance(choice, dict)
        ]
    if isinstance(value.get("data"), list):
        result["embedding_dimensions"] = [
            len(item["embedding"])
            for item in value["data"]
            if isinstance(item, dict) and isinstance(item.get("embedding"), list)
        ]
    return result


@dataclass
class RequestObservation:
    root: Path
    request_id: str

    def outcome(self, value: dict) -> bool:
        try:
            _write(
                self.root / f"{self.request_id}.outcome.json",
                {
                    "request_id": self.request_id,
                    "finished_at": time.time(),
                    **value,
                },
            )
        except (OSError, ValueError, TypeError):
            return False
        return True

    def completed(self, response: httpx.Response) -> bool:
        try:
            value = response.json()
            if not isinstance(value, dict):
                raise ValueError("non_object_response")
        except ValueError:
            return self.outcome(
                {
                    "http_status": response.status_code,
                    "status": "received",
                    "response_capture_complete": False,
                    "limitation": "non_json_response",
                }
            )
        return self.outcome(
            {
                "http_status": response.status_code,
                "status": "received",
                "response_capture_complete": True,
                "visible_response": visible_response(value),
            }
        )

    def failed(self, error: BaseException) -> bool:
        return self.outcome(
            {"status": "transport_failed", "error_type": type(error).__name__}
        )


def begin_observation(
    request: httpx.Request, *, source_id: str
) -> RequestObservation | None:
    settings = get_settings()
    activation_root = getattr(settings, "activation_root", "")
    lease = check_dispatch_lease(Path(activation_root) if activation_root else None)
    root = getattr(settings, "observation_root", "")
    if not root:
        return None
    request_id = str(uuid4())
    record: dict = {
        "schema_version": 1,
        "request_id": request_id,
        "started_at": time.time(),
        "source_id": source_id,
        "endpoint": str(request.url),
        "request_sha256": hashlib.sha256(request.content).hexdigest(),
        "metadata": dict(_CONTEXT.get() or {}),
        "activation_id": lease["activation_id"] if lease else None,
        "source_revision": lease["source_revision"] if lease else None,
    }
    try:
        body = json.loads(request.content)
        if _private_fields(body):
            record.update(
                {"input_complete": False, "limitation": "private_fields_excluded"}
            )
        else:
            record.update(
                {
                    "input_complete": True,
                    "body": body,
                    "raw_body_utf8": request.content.decode("utf-8"),
                }
            )
        _write(Path(root) / f"{request_id}.request.json", record)
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        raise ObservationUnavailable("request_capture_unavailable") from exc
    return RequestObservation(Path(root), request_id)


def read_observation(request_id: str) -> dict | None:
    root = getattr(get_settings(), "observation_root", "")
    if not root:
        return None
    identity = str(UUID(request_id))
    request_path = Path(root) / f"{identity}.request.json"
    if not request_path.is_file():
        return None
    request = json.loads(request_path.read_bytes())
    outcome_path = Path(root) / f"{identity}.outcome.json"
    outcome = json.loads(outcome_path.read_bytes()) if outcome_path.is_file() else None
    return {"request": request, "outcome": outcome}


def list_observations(*, run_id: str | None, offset: int, limit: int) -> dict:
    root = getattr(get_settings(), "observation_root", "")
    if not root:
        return {"items": [], "total": 0, "enabled": False}
    items = []
    for path in Path(root).glob("*.request.json"):
        value = json.loads(path.read_bytes())
        if run_id is not None and value.get("metadata", {}).get("run_id") != run_id:
            continue
        items.append(
            {
                key: value.get(key)
                for key in (
                    "request_id",
                    "started_at",
                    "metadata",
                    "request_sha256",
                    "input_complete",
                )
            }
        )
    items.sort(key=lambda value: (value["started_at"], value["request_id"]))
    return {
        "items": items[offset : offset + limit],
        "total": len(items),
        "enabled": True,
    }
