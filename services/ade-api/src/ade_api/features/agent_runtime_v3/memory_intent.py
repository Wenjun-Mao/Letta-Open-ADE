from __future__ import annotations

import re


_CHINESE_FORGETTING_REQUESTS = (
    re.compile(
        r"(?:^|[。！？!?]\s*)(?:(?:请|麻烦(?:你)?|帮我)\s*)?"
        r"(?:忘掉|抹去)(?!了)"
    ),
    re.compile(
        r"(?:^|[。！？!?]\s*)(?:(?:请|麻烦(?:你)?|帮我)\s*)?"
        r"把[^。！？!?]+(?:忘掉|抹去|删除|移除|清除)"
    ),
    re.compile(
        r"(?:^|[。！？!?]\s*)(?:(?:请|麻烦(?:你)?|帮我)\s*)?"
        r"(?:不要(?:再)?|别(?:再)?)\s*(?:记住|记得|保留)"
    ),
    re.compile(
        r"(?:^|[。！？!?]\s*)(?:(?:请|麻烦(?:你)?|帮我)\s*)?"
        r"(?:删除|移除|清除)[^。！？!?]*(?:记忆|信息|资料|这件事)"
    ),
)
_ENGLISH_FORGETTING_REQUESTS = (
    re.compile(
        r"(?:^|[.!?]\s*)(?:(?:please|kindly)\s+)?(?:forget|erase)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:can|could|would|will)\s+you\s+(?:please\s+)?"
        r"(?:forget|erase)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bi\s+(?:want|need|would\s+like)\s+you\s+to\s+"
        r"(?:forget|erase)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[.!?]\s*)(?:(?:please|kindly)\s+)?(?:remove|delete)\b"
        r"[^\n]*(?:\b(?:memory|memories|detail|information)\b)",
        re.IGNORECASE,
    ),
)


def is_explicit_forgetting_request(content: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(content or "")).strip()
    if not normalized:
        return False
    return any(
        pattern.search(normalized)
        for pattern in (*_CHINESE_FORGETTING_REQUESTS, *_ENGLISH_FORGETTING_REQUESTS)
    )
