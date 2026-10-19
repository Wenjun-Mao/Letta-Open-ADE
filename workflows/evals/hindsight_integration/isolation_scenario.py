"""Negative structural/role controls, not an inference-based privacy guarantee."""

import os
from uuid import uuid4

import httpx

from .product_views import memory_path, page, saved_state
from .public_http import PublicRecordingTransport, get_json, post_json
from .records import write_new
from .wire_capture import require


async def require_status(api, path, status, *, payload=None):
    response = await (
        api.get(path) if payload is None else api.post(path, json=payload)
    )
    require(response.status_code == status, "isolation_status_mismatch")
    return {"path": path, "status": response.status_code, "body": response.json()}


async def create(api, **binding):
    return await post_json(
        api,
        "/api/v3/evaluation-sessions",
        {
            "idempotency_key": "stage1-isolation-" + uuid4().hex,
            "title": "Stage1 negative access",
            **binding,
        },
    )


def configured(context):
    return {
        "model_key": context.runtime.character_route,
        "compaction_model_key": context.runtime.character_route,
        "prompt_key": "chat_v20261019",
        "persona_key": "chat_linxiaotang",
        "tool_names": ["search_memory"],
    }


async def forged_reads(api, route, delivery):
    document, operation = delivery["document_id"], delivery["operation_id"]
    return [
        await require_status(api, route + "/sources/" + document, 404),
        await require_status(api, route + "/operations/" + operation, 404),
        await require_status(
            api,
            route + "/deliveries/" + operation + "/retry",
            404,
            payload={"expected_check_count": delivery["check_count"]},
        ),
    ]


async def secondary_ready(api):
    try:
        response = await api.get("/api/v2/health")
        return response.status_code == 200 and response.json().get("status") == "ok"
    except httpx.HTTPError:
        return False


async def isolation(context):
    anchor = await context.session("access anchor")
    accepted = await context.accept(
        anchor, "我周日下午去公园散步。今天路上看到了几只小鸟。"
    )
    await context.terminal(accepted["run_id"], expected="succeeded")
    retained = await context.retained(anchor)
    delivery = retained["deliveries"]["items"][0]
    route = memory_path(anchor)
    own_operation = await get_json(
        context.api, route + "/operations/" + delivery["operation_id"]
    )
    other_subject = await create(
        context.api, agent_definition_id=anchor["agent_definition"]["id"]
    )
    other_character = await create(
        context.api,
        memory_subject_id=anchor["memory_subject"]["id"],
        **configured(context),
    )
    require(
        other_subject["memory_subject"]["id"] != anchor["memory_subject"]["id"]
        and other_subject["agent_definition"]["agent_definition_id"]
        == anchor["agent_definition"]["agent_definition_id"],
        "subject_boundary_not_isolated_from_character",
    )
    require(
        other_character["memory_subject"]["id"] == anchor["memory_subject"]["id"]
        and other_character["agent_definition"]["agent_definition_id"]
        != anchor["agent_definition"]["agent_definition_id"],
        "character_boundary_not_isolated_from_subject",
    )
    boundaries = []
    for label, session in (("subject", other_subject), ("character", other_character)):
        write_new(context.root / (label + "-session.json"), session)
        state = await saved_state(context.api, session["conversation"]["id"])
        memories = await page(context.api, memory_path(session) + "/memories")
        deliveries = await page(context.api, memory_path(session) + "/deliveries")
        require(
            not state["conversation"]["messages"]
            and memories["total"] == deliveries["total"] == 0,
            "fresh_boundary_inherited_state",
        )
        boundaries.append(
            {
                "boundary": label,
                "memories": memories,
                "deliveries": deliveries,
                "denied": await forged_reads(
                    context.api, memory_path(session), delivery
                ),
            }
        )
    private_path = "/api/v3/private-observations/runs/" + accepted["run_id"]
    async with (
        httpx.AsyncClient(
            base_url=str(context.api.base_url),
            headers={
                "Authorization": "Bearer " + os.environ["ADE_INTEGRATION_READER_KEY"]
            },
            transport=PublicRecordingTransport(context.root / "reader-http"),
            timeout=30,
        ) as reader,
        httpx.AsyncClient(
            base_url=str(context.api.base_url),
            transport=PublicRecordingTransport(context.root / "unauth-http"),
            timeout=30,
        ) as unauth,
    ):
        roles = {
            "reader_denied_private": await require_status(reader, private_path, 403),
            "unauth_denied_private": await require_status(unauth, private_path, 401),
            "reader_source": await get_json(
                reader, route + "/sources/" + delivery["document_id"]
            ),
            "reader_denied_retry": await require_status(
                reader,
                route + "/deliveries/" + delivery["operation_id"] + "/retry",
                403,
                payload={"expected_check_count": delivery["check_count"]},
            ),
        }
    started = await context.host("start-isolation-api")
    async with httpx.AsyncClient(
        base_url="http://ade-isolation-api:8000",
        headers={"Authorization": "Bearer " + os.environ["ADE_INTEGRATION_API_KEY"]},
        transport=PublicRecordingTransport(context.root / "secondary-http"),
        timeout=30,
    ) as secondary:
        await context.until(
            lambda: secondary_ready(secondary),
            bool,
            seconds=60,
            code="secondary_api_did_not_start",
        )
        own = await create(secondary, **configured(context))
        own_state = await saved_state(secondary, own["conversation"]["id"])
        foreign = [
            await require_status(secondary, "/api/v3/runs/" + accepted["run_id"], 404),
            await require_status(secondary, private_path, 404),
            await require_status(
                secondary,
                f"/api/v3/evaluation-sessions/{anchor['conversation']['id']}/state",
                404,
            ),
            *await forged_reads(secondary, route, delivery),
            await require_status(secondary, route + "/memories", 404),
        ]
        reversed_access = await require_status(
            context.api,
            f"/api/v3/evaluation-sessions/{own['conversation']['id']}/state",
            404,
        )
        foreign_definition = await require_status(
            secondary,
            "/api/v3/evaluation-sessions",
            404,
            payload={
                "idempotency_key": "stage1-foreign-definition-" + uuid4().hex,
                "agent_definition_id": anchor["agent_definition"]["id"],
            },
        )
    stopped = await context.host("stop-isolation-api")
    return {
        "anchor": anchor,
        "anchor_sources": retained,
        "anchor_operation": own_operation,
        "boundaries": boundaries,
        "roles": roles,
        "secondary_start": started,
        "secondary_own_session": own,
        "secondary_own_state": own_state,
        "foreign_denied": foreign,
        "reverse_workspace_denied": reversed_access,
        "foreign_definition_denied": foreign_definition,
        "secondary_stop": stopped,
    }
