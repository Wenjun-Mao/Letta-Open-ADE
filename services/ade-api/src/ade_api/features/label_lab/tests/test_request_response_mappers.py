from __future__ import annotations

from ade_api.features.label_lab.request_builder import (
    build_label_repair_request_payload,
    build_label_request_payload,
)
from ade_api.features.label_lab.response_mapper import (
    append_finish_reason_diagnostic,
    build_label_generation_result,
    extract_validated_label_response,
)


def _schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "players": {"type": "array", "items": {"type": "string"}},
            "teams": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["players", "teams"],
        "additionalProperties": False,
    }


def test_label_request_builder_preserves_schema_and_sampling_controls() -> None:
    payload = build_label_request_payload(
        model="gemma",
        system_prompt="Extract entities.",
        article_input="Messi scored for Inter Miami.",
        output_schema=_schema(),
        output_schema_name="football_entities",
        output_mode="json_schema",
        max_tokens=0,
        temperature=0.2,
        top_p=0.9,
        top_k=64,
    )

    assert payload["model"] == "gemma"
    assert "max_tokens" not in payload
    assert payload["temperature"] == 0.2
    assert payload["top_p"] == 0.9
    assert payload["top_k"] == 64
    assert payload["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "football_entities",
            "strict": True,
            "schema": _schema(),
        },
    }


def test_label_repair_builder_preserves_primary_provider_shape() -> None:
    kwargs = {
        "model": "gemma",
        "system_prompt": "Extract entities.",
        "article_input": "Messi scored for Inter Miami.",
        "output_schema": _schema(),
        "output_schema_name": "football_entities",
        "output_mode": "json_schema",
        "max_tokens": 256,
        "temperature": 0.0,
        "top_p": 1.0,
        "top_k": None,
    }
    primary = build_label_request_payload(**kwargs)
    repair = build_label_repair_request_payload(
        **kwargs,
        invalid_output='{"players":["Ronaldo"]}',
        validation_errors=[
            "players[0] must exactly match a substring in the input article."
        ],
    )

    assert repair["model"] == primary["model"]
    assert repair["response_format"] == primary["response_format"]
    assert repair["messages"][0] == primary["messages"][0]
    assert repair["messages"][1]["role"] == "user"
    assert "Previous Invalid Output" in repair["messages"][1]["content"]
    assert "Ronaldo" in repair["messages"][1]["content"]


def test_label_response_mapper_reads_reasoning_when_content_is_empty() -> None:
    raw_reply = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "reasoning_content": '{"players":["Messi"],"teams":["Inter Miami"]}',
                },
                "finish_reason": "stop",
            }
        ]
    }

    result, invalid_output, errors, finish_reason = extract_validated_label_response(
        data=raw_reply,
        article_input="Messi scored for Inter Miami.",
        output_schema=_schema(),
    )

    assert result == {"players": ["Messi"], "teams": ["Inter Miami"]}
    assert invalid_output == '{"players":["Messi"],"teams":["Inter Miami"]}'
    assert errors == []
    assert finish_reason == "stop"


def test_label_response_diagnostics_include_one_non_stop_finish_reason() -> None:
    result, invalid_output, errors, finish_reason = extract_validated_label_response(
        data={
            "choices": [
                {
                    "message": {
                        "content": '{"players":["Ronaldo"],"teams":["Inter Miami"]}'
                    },
                    "finish_reason": "length",
                }
            ]
        },
        article_input="Messi scored for Inter Miami.",
        output_schema=_schema(),
    )

    assert result is None
    assert invalid_output == '{"players":["Ronaldo"],"teams":["Inter Miami"]}'
    assert any("substring" in error for error in errors)
    assert finish_reason == "length"
    append_finish_reason_diagnostic(errors, finish_reason)
    assert errors.count("Provider finished with finish_reason=length.") == 1


def test_label_generation_result_preserves_raw_provider_diagnostics() -> None:
    raw_request = {"model": "gemma"}
    raw_reply = {"choices": [], "usage": {"total_tokens": 7}}
    result = build_label_generation_result(
        result={"players": ["Messi"], "teams": ["Inter Miami"]},
        output_mode="json_schema",
        selected_attempt="repair",
        finish_reason="stop",
        data=raw_reply,
        payload=raw_request,
        runtime={"timeout_seconds": 60.0, "repair_retry_count": 1},
    )

    assert result["selected_attempt"] == "repair"
    assert result["usage"] == {"total_tokens": 7}
    assert result["validation_errors"] == []
    assert result["raw_request"] is raw_request
    assert result["raw_reply"] is raw_reply
    assert result["timeout_seconds"] == 60.0
    assert result["repair_retry_count"] == 1
