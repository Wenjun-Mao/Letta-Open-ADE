"""Allow-listed operational snapshots, never native error bodies or task payloads."""

from datetime import datetime
from uuid import UUID

from ade_api.integrations.hindsight import OPERATION_STATUSES


def native_progress(value: dict) -> dict:
    result = {}
    if value.get("status") in OPERATION_STATUSES:
        result["status"] = value["status"]
    progress = value.get("progress")
    if isinstance(progress, dict):
        snapshot = {
            key: item
            for key in ("processed", "total")
            if type(item := progress.get(key)) is int and 0 <= item <= 1_000_000_000
        }
        if progress.get("stage") in {
            "processing_batch",
            "consolidating",
            "extracting",
            "embedding",
            "storing",
        }:
            snapshot["stage"] = progress["stage"]
        try:
            at = progress.get("at")
            if (
                isinstance(at, str)
                and datetime.fromisoformat(at).utcoffset() is not None
            ):
                snapshot["at"] = at
        except ValueError:
            pass
        result["progress"] = snapshot
    children = value.get("child_operations")
    if isinstance(children, list):
        safe = []
        for child in children[:1000]:
            if (
                not isinstance(child, dict)
                or child.get("status") not in OPERATION_STATUSES
            ):
                continue
            try:
                operation = str(UUID(child.get("operation_id", "")))
            except (ValueError, TypeError, AttributeError):
                continue
            safe.append(
                {
                    "operation_id": operation,
                    "status": child["status"],
                    **{
                        key: item
                        for key in ("sub_batch_index", "items_count")
                        if type(item := child.get(key)) is int
                        and 0 <= item <= 1_000_000_000
                    },
                }
            )
        result["child_operations"] = safe
    return result
