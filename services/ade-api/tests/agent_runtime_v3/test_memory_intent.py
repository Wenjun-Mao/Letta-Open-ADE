from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.memory_intent import (
    is_explicit_forgetting_request,
)


@pytest.mark.parametrize(
    "content",
    [
        "请忘掉我喜欢蓝色这件事。",
        "把我喜欢爵士乐这件事忘掉。",
        "不要再记住我的鞋码。",
        "Please forget that my favorite color is blue.",
        "Could you forget my old address?",
        "I want you to forget my shoe size.",
        "Delete that detail from your memory.",
    ],
)
def test_explicit_forgetting_request_is_conservatively_recognized(
    content: str,
) -> None:
    assert is_explicit_forgetting_request(content) is True


@pytest.mark.parametrize(
    "content",
    [
        "别忘了我喜欢蓝色。",
        "不要忘记我的名字。",
        "我忘了自己以前住在哪里。",
        "Don't forget that my favorite color is blue.",
        "I forgot my old address.",
        "This is an unforgettable trip.",
        "Please remember my shoe size.",
        "Remove the lid from the jar.",
    ],
)
def test_non_removal_language_is_not_classified_as_forgetting(content: str) -> None:
    assert is_explicit_forgetting_request(content) is False
