"""CLI output shapes; semantic validation remains in tasks.validate_result."""


def _object(properties: dict) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def output_schema(task: str) -> dict:
    text = {"type": "string"}
    if task == "dialogue":
        return _object({"reply": text})
    if task == "judge":
        return _object(
            {
                "assessment": {
                    "type": "string",
                    "enum": ["pass", "fail", "uncertain"],
                },
                "reason": text,
            }
        )
    if task == "memory-review":
        return _object(
            {
                "proposals": {
                    "type": "array",
                    "items": _object(
                        {
                            "kind": {
                                "type": "string",
                                "enum": ["user_fact", "shared_experience"],
                            },
                            "summary": text,
                            "source_message_ids": {"type": "array", "items": text},
                        }
                    ),
                }
            }
        )
    raise ValueError(f"Unknown task: {task}")
