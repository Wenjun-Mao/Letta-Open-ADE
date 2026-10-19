"""Exact actor inputs through the normal saved-turn API, with independent capture."""

import asyncio
from pathlib import Path
import time
from uuid import uuid4

from .live_artifacts import reference
from .live_capture_contracts import PhaseReference
from .product_capture import CaptureQualificationError, collect_saved_run
from .product_views import state_path
from .public_http import get_json, post_json
from .wire_capture import require


class ProductTurnFailure(RuntimeError):
    def __init__(self, status: str, code: str | None, bundle: dict):
        super().__init__(f"saved_turn_{status}:{code or 'no_error_code'}")
        self.stage = "recall" if status == "paused" else "generation"
        self.bundle = bundle


async def wait_turn(api, run_id, *, deadline):
    while time.monotonic() < deadline:
        run = await get_json(api, f"/api/v3/runs/{run_id}")
        if run["status"] in {"succeeded", "failed", "cancelled", "paused"}:
            return run
        await asyncio.sleep(1)
    raise TimeoutError("saved_turn_still_active_at_slot_deadline")


async def send_turn(
    api,
    router,
    *,
    session: dict,
    content: str,
    phase: str,
    source: dict,
    scope: dict,
    root: Path,
    out: Path,
    deadline: float,
):
    conversation_id = session["conversation"]["id"]
    remaining = deadline - time.monotonic()
    require(remaining >= 10, "insufficient_slot_time_for_saved_turn")
    receipt = await post_json(
        api,
        f"/api/v3/conversations/{conversation_id}/turns",
        {
            "content": content,
            "idempotency_key": "stage1-" + uuid4().hex,
            "timeout_seconds": min(180, remaining - 5),
            "retry_count": 0,
        },
    )
    run_id = receipt["run_id"]
    # Obtain actual workspace authority from its public saved-run export; do not
    # reconstruct a private database UUID algorithm in the evaluator.
    identity = await get_json(api, f"/api/v3/private-observations/runs/{run_id}")
    if "workspace_id" in scope:
        require(
            scope["workspace_id"] == identity["workspace_id"],
            "active_workspace_changed",
        )
    scope["workspace_id"] = identity["workspace_id"]
    run = await wait_turn(api, run_id, deadline=deadline)
    try:
        bundle, result = await collect_saved_run(
            api=api,
            router=router,
            run_id=run_id,
            phase=phase,
            state_path=state_path(conversation_id),
            scope=scope,
            source=source,
            expected_input=content,
            fresh_probe=phase == "probe",
            out=out,
        )
    except CaptureQualificationError as exc:
        if run["status"] != "succeeded":
            raise ProductTurnFailure(
                run["status"], run.get("error_code"), exc.bundle
            ) from None
        raise
    require(run["status"] == "succeeded", "saved_turn_not_succeeded")
    ref = PhaseReference(
        **reference(root, out / "collection.json").model_dump(),
        phase=phase,
        run_id=run_id,
    )
    return ref, bundle, result
