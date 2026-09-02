from __future__ import annotations

from typing import Any, Callable

import httpx


def get_json(
    client: httpx.Client,
    url: str,
    api_key: str,
    *,
    params: dict[str, str] | None = None,
) -> dict[str, Any]:
    response = client.get(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        params=params,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("invalid_health_payload")
    return payload


def snapshot_native_state(
    client: httpx.Client,
    base_url: str,
    api_key: str,
) -> dict[str, Any]:
    root = f"{base_url.rstrip('/')}/api/v3/agent-studio"
    definitions = _list_all(client, f"{root}/definitions", api_key)
    subjects = _list_all(client, f"{root}/subjects", api_key)
    sessions = _list_all(client, f"{root}/sessions", api_key)
    memories = {
        str(subject["id"]): get_json(
            client,
            f"{root}/subjects/{subject['id']}/memories",
            api_key,
        )
        for subject in subjects
    }
    conversation_states = {
        conversation_id: _conversation_state(
            client,
            f"{root}/sessions/{conversation_id}/state",
            api_key,
        )
        for session in sessions
        if (conversation_id := _session_conversation_id(session))
    }
    if len(conversation_states) != len(sessions):
        raise RuntimeError("invalid_agent_studio_session_snapshot")
    return {
        "definitions": definitions,
        "subjects": subjects,
        "sessions": sessions,
        "memories": memories,
        "conversation_states": conversation_states,
    }


def wait_for_native(
    client: httpx.Client,
    base_url: str,
    api_key: str,
    *,
    sleep: Callable[[float], None],
) -> None:
    for _ in range(60):
        try:
            health = get_json(
                client,
                f"{base_url.rstrip('/')}/api/v3/worker-health",
                api_key,
            )
            if health.get("worker_ready") is True:
                return
        except (httpx.HTTPError, RuntimeError, ValueError):
            pass
        sleep(2)
    raise RuntimeError("native_lane_did_not_recover")


def _list_all(client: httpx.Client, url: str, api_key: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    offset = 0
    total: int | None = None
    while total is None or len(items) < total:
        page = get_json(
            client,
            url,
            api_key,
            params={
                "include_archived": "true",
                "limit": "200",
                "offset": str(offset),
            },
        )
        page_items = page.get("items")
        page_total = page.get("total")
        if (
            not isinstance(page_items, list)
            or any(not isinstance(item, dict) for item in page_items)
            or type(page_total) is not int
            or page_total < 0
        ):
            raise RuntimeError("invalid_agent_studio_list_snapshot")
        total = page_total
        if not page_items and len(items) < total:
            raise RuntimeError("incomplete_agent_studio_list_snapshot")
        items.extend(page_items)
        offset += len(page_items)
    if len(items) != total:
        raise RuntimeError("unstable_agent_studio_list_snapshot")
    return items


def _conversation_state(
    client: httpx.Client,
    url: str,
    api_key: str,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    before_sequence: int | None = None
    state: dict[str, Any] | None = None
    seen_cursors: set[int] = set()
    while state is None or before_sequence is not None:
        params = {"message_limit": "200"}
        if before_sequence is not None:
            params["before_sequence"] = str(before_sequence)
        page = get_json(client, url, api_key, params=params)
        page_messages = page.get("messages")
        if not isinstance(page_messages, list) or any(
            not isinstance(item, dict) for item in page_messages
        ):
            raise RuntimeError("invalid_agent_studio_message_snapshot")
        if state is None:
            state = {
                key: value
                for key, value in page.items()
                if key
                not in {
                    "messages",
                    "messages_truncated",
                    "next_before_sequence",
                }
            }
        messages.extend(page_messages)
        cursor = page.get("next_before_sequence")
        if cursor is None:
            before_sequence = None
        elif type(cursor) is not int or cursor < 1 or cursor in seen_cursors:
            raise RuntimeError("invalid_agent_studio_message_cursor")
        else:
            seen_cursors.add(cursor)
            before_sequence = cursor
    assert state is not None
    expected_total = state.get("message_total")
    if type(expected_total) is not int or len(messages) != expected_total:
        raise RuntimeError("incomplete_agent_studio_message_snapshot")
    state["messages"] = sorted(messages, key=lambda item: int(item["sequence"]))
    return state


def _session_conversation_id(session: dict[str, Any]) -> str:
    conversation = session.get("conversation")
    if not isinstance(conversation, dict):
        return ""
    return str(conversation.get("id") or "")
