from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from letta_client import Letta

try:
    SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    SHANGHAI_TZ = timezone(timedelta(hours=8), name="CST")

DATETIME_QUERY_TOKENS = (
    "today",
    "date",
    "time",
    "current date",
    "current time",
    "what day",
    "what time",
    "今天",
    "日期",
    "几月",
    "几号",
    "几日",
    "星期",
    "周几",
    "礼拜几",
    "现在几点",
    "当前时间",
)


def derive_last_interaction_at(
    agent_id: str,
    client: Letta,
    last_updated_at: str = "",
) -> str:
    if last_updated_at:
        return last_updated_at
    try:
        messages = list(client.agents.messages.list(agent_id=agent_id))
    except Exception:
        return ""

    latest = ""
    for message in messages:
        if str(getattr(message, "message_type", "")) == "system_message":
            continue
        created_at = str(
            getattr(message, "created_at", None) or getattr(message, "date", None) or ""
        )
        if created_at and created_at > latest:
            latest = created_at
    return latest


def is_datetime_query(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(token in lowered for token in DATETIME_QUERY_TOKENS)


def runtime_datetime_system_hint() -> str:
    now = datetime.now(SHANGHAI_TZ)
    iso_time = now.strftime("%Y-%m-%d %H:%M:%S %Z%z")
    return (
        "Runtime datetime context for this turn. "
        "Timezone: Asia/Shanghai. "
        f"Current datetime: {iso_time}. "
        "If the user asks about current date or time, answer directly using this value. "
        "Do not say you cannot access a calendar."
    )
