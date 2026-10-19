"""Exact wire-byte, privacy and outcome validation for collected requests."""

import hashlib
import json

from .checks import reject_sensitive_fields


def require(condition, code):
    if not condition:
        raise ValueError(code)


def validate_wire(value: dict) -> dict:
    reject_sensitive_fields(value)
    request, outcome = value["request"], value["outcome"]
    require(request.get("input_complete") is True, "wire_input_incomplete")
    raw = request["raw_body_utf8"].encode("utf-8")
    require(
        hashlib.sha256(raw).hexdigest() == request["request_sha256"],
        "wire_hash_mismatch",
    )
    require(json.loads(raw) == request["body"], "wire_json_mismatch")
    require(
        outcome is not None and outcome.get("request_id") == request["request_id"],
        "wire_outcome_missing_or_mismatched",
    )
    require(
        outcome.get("response_capture_complete") is True
        or (
            outcome.get("status") == "transport_failed"
            and isinstance(outcome.get("error_type"), str)
        ),
        "wire_response_incomplete",
    )
    return request
