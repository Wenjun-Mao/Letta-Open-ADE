"""Predeclared finite faults, with actual retained source and product outcomes."""

import time

from .product_views import memory_path, page
from .public_http import get_json, post_json
from .wire_capture import require


async def failed_generation(context):
    session = await context.session("failed generation")
    fault = await context.rule(session, target="router_chat", mode="fail_before_send")
    receipt = await context.accept(session, "我周六下午练习书法。")
    await context.matched(fault)
    run = await context.terminal(receipt["run_id"], expected="failed")
    state = await context.messages(session, users=1, assistants=0)
    sources = await context.retained(session)
    require(run["attempt_count"] == 1, "failed_generation_retried_implicitly")
    require(
        len(sources["deliveries"]["items"]) == 1, "failed_reply_became_memory_source"
    )
    return {"run": run, "state": state, **sources, "fault_id": fault}


async def cancellation(context):
    session = await context.session("cancellation")
    fault = await context.rule(session, target="router_chat", mode="hold_before_send")
    receipt = await context.accept(session, "我周三晚上练习钢琴。你喜欢什么音乐？")
    await context.matched(fault)
    await post_json(context.api, f"/api/v3/runs/{receipt['run_id']}/cancel", {})
    run = await context.terminal(receipt["run_id"], expected="cancelled", seconds=30)
    rule = await get_json(context.fault, f"/control/rules/{fault}")
    require(
        not rule["released"] and "upstream_status" not in rule["outcome"],
        "cancelled_request_was_forwarded",
    )
    state = await context.messages(session, users=1, assistants=0)
    await context.release(fault)
    sources = await context.retained(session)
    return {"run": run, "state": state, "held_rule": rule, **sources}


async def delayed_delivery(context):
    session = await context.session("delayed retain")
    fault = await context.rule(session, target="memory_retain", mode="hold_before_send")
    started = time.time()
    receipt = await context.accept(
        session, "我周二下午去图书馆。今天想聊一本轻松的小说。"
    )
    await context.matched(fault)
    run = await context.terminal(receipt["run_id"], expected="succeeded", seconds=90)
    held = await get_json(context.fault, f"/control/rules/{fault}")
    require(
        not held["released"] and "upstream_status" not in held["outcome"],
        "retain_not_still_delayed_at_reply_commit",
    )
    deliveries = await page(context.api, memory_path(session) + "/deliveries")
    require(
        not any(row["status"] == "retained" for row in deliveries["items"]),
        "delayed_source_already_retained",
    )
    await context.messages(session, users=1, assistants=1)
    other = await context.session("unrelated while retain held")
    other_receipt = await context.accept(other, "我每周日早上跑步。最近天气很舒服。")
    other_run = await context.terminal(
        other_receipt["run_id"], expected="succeeded", seconds=45
    )
    unrelated = await context.retained(other, seconds=60)
    still_held = await get_json(context.fault, f"/control/rules/{fault}")
    require(
        not still_held["released"] and "upstream_status" not in still_held["outcome"],
        "delayed_hold_ended_before_unrelated_delivery",
    )
    require(time.time() - started < 120, "delay_proof_exceeded_native_transport_window")
    await context.release(fault)
    retained = await context.retained(session)
    return {
        "started_at": started,
        "run": run,
        "reply_while_held": held,
        "deliveries_at_reply": deliveries,
        "unrelated_run": other_run,
        "unrelated_retained_while_held": unrelated,
        "held_after_unrelated_retained": still_held,
        "retained_after_release": retained,
    }


async def lost_acknowledgement(context):
    session = await context.session("lost retain acknowledgement")
    fault = await context.rule(session, target="memory_retain", mode="lose_ack")
    receipt = await context.accept(session, "我每个月的第二个周末参加读书会。")
    await context.matched(fault)
    await context.terminal(receipt["run_id"], expected="succeeded")
    retained = await context.retained(session)
    rule = await get_json(context.fault, f"/control/rules/{fault}")
    require(
        rule["outcome"].get("upstream_status") in {200, 202},
        "lost_ack_not_after_real_native_acceptance",
    )
    operation = rule["outcome"]["operation_id"]
    rows = [
        row
        for row in retained["deliveries"]["items"]
        if row["operation_id"] == operation
    ]
    require(
        len(rows) == 1 and rows[0]["attempt_count"] == 1,
        "lost_ack_duplicated_extraction_submission",
    )
    require(rows[0]["role"] == "user", "lost_ack_did_not_target_original_user_source")
    native = await get_json(
        context.api, memory_path(session) + f"/operations/{operation}"
    )
    await context.messages(session, users=1, assistants=1)
    return {"fault": rule, "same_operation": native, **retained}


PROXIED_SCENARIOS = {
    "failed-generation": failed_generation,
    "cancellation": cancellation,
    "delayed-delivery": delayed_delivery,
    "lost-acknowledgement": lost_acknowledgement,
}
