from ade_api.features.agent_runtime.model_response import first_choice, merge_usage


def test_first_choice_copies_all_continuation_fields():
    original = {
        "role": "assistant",
        "content": "",
        "reasoning_content": "private synthetic reasoning",
        "tool_calls": [{"id": "call-1"}],
        "provider_field": "retained",
    }
    copied, reason = first_choice(
        {"choices": [{"message": original, "finish_reason": "tool_calls"}]}
    )
    assert copied == original
    assert copied is not original
    copied["content"] = "changed"
    assert original["content"] == ""
    assert reason == "tool_calls"


def test_usage_accumulates_integer_fields_and_ignores_other_shapes():
    total = {"prompt_tokens": 2}
    merge_usage(
        total,
        {
            "prompt_tokens": 3,
            "completion_tokens": 4,
            "bool": False,
            "float": 1.5,
            "string": "5",
            "details": {},
        },
    )
    merge_usage(total, None)
    merge_usage(total, [])
    assert total == {"prompt_tokens": 5, "completion_tokens": 4}
