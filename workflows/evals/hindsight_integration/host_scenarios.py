"""Owned-runtime recovery cases using explicit bounded host-control receipts."""

from uuid import uuid4

import httpx

from .product_views import memory_path, page, saved_state
from .public_http import get_json, post_json
from .wire_capture import require


async def worker_ready(context):
    async def read():
        try:
            return await get_json(context.api, "/api/v3/worker-health")
        except httpx.HTTPError:
            # Only explicit restart observation polls transient HTTP failures.
            return {"worker_ready": False}

    return await context.until(
        read,
        lambda row: row["worker_ready"] is True,
        seconds=180,
        code="owned_runtime_did_not_recover",
    )


async def reconcile_delivery(context, session):
    route = memory_path(session)
    before = await page(context.api, route + "/deliveries")
    retries = []
    for row in before["items"]:
        if row["status"] in {"failed", "uncertain"}:
            retries.append(
                await post_json(
                    context.api,
                    route + f"/deliveries/{row['operation_id']}/retry",
                    {"expected_check_count": row["check_count"]},
                )
            )
    retained = await context.retained(session)
    require(
        {row["operation_id"] for row in before["items"]}
        == {row["operation_id"] for row in retained["deliveries"]["items"]},
        "recovery_changed_delivery_operation_identity",
    )
    return {"before": before, "explicit_retry_receipts": retries, "retained": retained}


async def recall_outage(context):
    session = await context.session("recall outage")
    stopped = await context.host("stop-native")
    receipt = await context.accept(
        session, "我每周五傍晚去公园散步。今天想找你聊聊天。"
    )
    paused = await context.terminal(receipt["run_id"], expected="paused", seconds=90)
    state = await context.messages(session, users=1, assistants=0)
    response = await context.api.get(memory_path(session) + "/memories")
    require(response.status_code == 503, "native_outage_became_empty_memory_success")
    capture = await context.capture()
    require(
        not capture["payload"]["runs"][0]["wires"], "lookup_outage_reached_character"
    )
    started = await context.host("start-native")
    health = await worker_ready(context)
    request = {
        "idempotency_key": "stage1-safety-retry-" + uuid4().hex,
        "expected_attempt_count": paused["attempt_count"],
    }
    retried = await post_json(
        context.api, f"/api/v3/runs/{receipt['run_id']}/retry", request
    )
    replayed = await post_json(
        context.api, f"/api/v3/runs/{receipt['run_id']}/retry", request
    )
    require(
        retried["run_id"] == replayed["run_id"] == receipt["run_id"]
        and replayed["idempotent_replay"] is True,
        "saved_reply_retry_identity_changed",
    )
    run = await context.terminal(receipt["run_id"], expected="succeeded")
    after = await context.messages(session, users=1, assistants=1)
    require(
        state["conversation"]["messages"][0] == after["conversation"]["messages"][0],
        "retry_replaced_original_accepted_input",
    )
    deliveries = await reconcile_delivery(context, session)
    return {
        "stop": stopped,
        "start": started,
        "paused": paused,
        "paused_state": state,
        "paused_capture": capture,
        "restored_health": health,
        "retry": retried,
        "idempotent_retry_replay": replayed,
        "succeeded": run,
        "deliveries": deliveries,
    }


async def runtime_restart(context):
    session = await context.session("runtime restart with accepted retain")
    fault = await context.rule(
        session, target="memory_retain", mode="hold_after_response"
    )
    receipt = await context.accept(session, "我每周四下午去游泳。今天游完以后很放松。")
    received = await context.until(
        lambda: get_json(context.fault, f"/control/rules/{fault}"),
        lambda row: row["outcome"].get("upstream_status") in {200, 202},
        seconds=90,
        code="restart_retain_not_really_accepted",
    )
    await context.terminal(receipt["run_id"], expected="succeeded")
    before = await saved_state(context.api, session["conversation"]["id"])
    restarted = await context.host("restart-runtime")
    await context.release(fault)
    health = await worker_ready(context)
    after = await context.messages(session, users=1, assistants=1)
    require(
        before["conversation"] == after["conversation"],
        "restart_changed_saved_conversation",
    )
    reconciled = await reconcile_delivery(context, session)
    operation = received["outcome"]["operation_id"]
    source = next(
        row
        for row in reconciled["retained"]["deliveries"]["items"]
        if row["operation_id"] == operation
    )
    require(source["attempt_count"] == 1, "restart_resubmitted_accepted_retain")
    return {
        "held_after_native_acceptance": received,
        "restart": restarted,
        "restored_health": health,
        "before": before,
        "after": after,
        "reconciliation": reconciled,
    }


HOST_SCENARIOS = {"recall-outage": recall_outage, "runtime-restart": runtime_restart}
