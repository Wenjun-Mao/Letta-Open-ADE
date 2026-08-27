from __future__ import annotations

from workflows.evals.agent_runtime_study.letta_baseline import _analyze_timeline


def test_baseline_observations_require_real_tool_events() -> None:
    observations = _analyze_timeline(
        [
            {
                "operation": "message_1",
                "payload": {
                    "sequence": [
                        {
                            "type": "reasoning",
                            "content": "I should call conversation_search",
                        },
                        {
                            "type": "tool_call",
                            "name": "memory_replace",
                            "arguments": '{"label":"human"}',
                        },
                        {"type": "assistant", "content": "hello"},
                    ]
                },
            },
            {
                "operation": "state_after_1",
                "payload": {
                    "memory_blocks": [{"label": "human", "value": "name: Zhang Wei"}],
                    "conversation_history": {
                        "total_persisted": 4,
                        "displayed": 4,
                        "counts_by_type": {"user_message": 1},
                    },
                },
            },
            {
                "operation": "raw_prompt_after_1",
                "payload": {
                    "messages": [
                        {"role": "user", "content": "hello"},
                        {"role": "assistant", "content": "hi"},
                    ]
                },
            },
        ]
    )

    assert observations["memory_write_observed"] is True
    assert observations["conversation_search_observed"] is False
    assert observations["tool_names"] == ["memory_replace"]
    assert observations["context_snapshots"][0]["total_persisted"] == 4
    assert observations["context_snapshots"][1]["character_count"] == 7
