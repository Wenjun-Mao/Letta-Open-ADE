"""A real generated candidate must roll back after its finalization lease expires."""

from .host_scenarios import reconcile_delivery
from .wire_capture import require


async def stale_worker(context):
    session = await context.session("expired finalizer")
    fault = await context.rule(session, target="router_chat", mode="hold_before_send")
    receipt = await context.accept(
        session, "今天在公园散步时看见一只很安静的小猫。", retries=1
    )
    await context.matched(fault)
    locked = await context.host(
        "lock-subject",
        {
            "subject_id": session["conversation"]["memory_subject_id"],
            "conversation_id": session["conversation"]["id"],
        },
    )
    await context.release(fault)
    expired = await context.host("expire-finalizer", {"run_id": receipt["run_id"]})
    run = await context.terminal(receipt["run_id"], expected="succeeded", seconds=180)
    require(
        run["attempt_count"] == 2, "expired_finalizer_not_recovered_as_second_attempt"
    )
    state = await context.messages(session, users=1, assistants=1)
    retained = await reconcile_delivery(context, session)
    capture = await context.capture()
    exported = capture["payload"]["runs"][0]["private_export"]
    attempts = exported["saved_attempts"]
    require(
        [(row["attempt_number"], row["status"]) for row in attempts]
        == [(1, "failed"), (2, "succeeded")],
        "stale_attempt_not_abandoned_before_recovered_commit",
    )
    first = next(
        row
        for row in exported["observations"]
        if row["attempt_id"] == attempts[0]["id"]
    )
    require(
        any(
            row["type"] == "attempt_execution.finished"
            and row["value"]["status"] == "candidate_produced"
            for row in first["records"]
        ),
        "stale_attempt_did_not_really_produce_candidate",
    )
    verified = await context.host("verify-finalizer", {"run_id": receipt["run_id"]})
    return {
        "subject_lock": locked,
        "expired_finalizer": expired,
        "recovered_run": run,
        "saved_state": state,
        "deliveries": retained,
        "attempt_readback": capture,
        "verified_recovery": verified,
    }
