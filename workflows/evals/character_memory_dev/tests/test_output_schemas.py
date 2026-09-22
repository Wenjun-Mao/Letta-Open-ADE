import pytest

from workflows.evals.character_memory_dev.output_schemas import output_schema
from workflows.evals.character_memory_dev.tasks import validate_result


@pytest.mark.parametrize("task", ["dialogue", "memory-review", "judge"])
def test_task_shapes_are_closed_objects(task):
    schema = output_schema(task)
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    if task == "memory-review":
        proposal = schema["properties"]["proposals"]["items"]
        assert proposal["additionalProperties"] is False
        assert set(proposal["required"]) == {"kind", "summary", "source_message_ids"}


def test_unknown_task_is_rejected():
    with pytest.raises(ValueError, match="Unknown task"):
        output_schema("unknown")


def test_structural_schema_does_not_replace_semantic_validation():
    with pytest.raises(ValueError, match="Invalid proposal evidence"):
        validate_result(
            "memory-review",
            '{"proposals":[{"kind":"user_fact","summary":"x",'
            '"source_message_ids":["missing"]}]}',
            {"messages": [{"id": "u1", "role": "user", "content": "x"}]},
        )
