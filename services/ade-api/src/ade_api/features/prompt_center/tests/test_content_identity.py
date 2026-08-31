from __future__ import annotations

from ade_api.features.prompt_center.content_identity import template_content_sha256
from ade_api.features.prompt_center.mappers import as_template_record


def test_template_record_exposes_exact_content_identity() -> None:
    record = as_template_record(
        {
            "kind": "prompt",
            "scenario": "chat",
            "key": "chat_test",
            "content": "Be warm.\n",
        }
    )

    assert record["content_sha256"] == template_content_sha256("Be warm.\n")
    assert record["content_sha256"] != template_content_sha256("Be warm.")
