"""Reject ambiguous duplicate keys in inputs, CLI events, and task outputs."""

import json


def loads(raw: str):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    return json.loads(raw, object_pairs_hook=unique_object)
