import json
import sys

import pytest

from workflows.evals.character_memory_dev import run


@pytest.mark.parametrize(
    "answer,exit_code", [('{"reply":"hello"}', 0), ("bad-json", 1)]
)
def test_task_validation_artifacts(monkeypatch, tmp_path, answer, exit_code):
    source = tmp_path / "input.json"
    source.write_text(
        json.dumps({"messages": [{"id": "u1", "role": "user", "content": "hello"}]})
    )
    output = tmp_path / "call"
    calls = []

    def generate(prompt, destination, **kwargs):
        assert kwargs["output_schema"] == {
            "type": "object",
            "properties": {"reply": {"type": "string"}},
            "required": ["reply"],
            "additionalProperties": False,
        }
        calls.append(prompt)
        destination.mkdir()
        return answer

    monkeypatch.setattr(run, "generate", generate)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run",
            "--runtime",
            "luna-subscription",
            "--task",
            "dialogue",
            "--input",
            str(source),
            "--output",
            str(output),
        ],
    )
    assert run.main() == exit_code
    assert len(calls) == 1
    assert json.loads((output / "validation.json").read_text())["valid"] == (
        exit_code == 0
    )
    assert (output / "result.json").exists() == (exit_code == 0)


def test_invalid_input_never_launches(monkeypatch, tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{"messages": []}')
    monkeypatch.setattr(
        run, "generate", lambda *a, **kw: pytest.fail("must not launch")
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run",
            "--runtime",
            "luna-subscription",
            "--task",
            "dialogue",
            "--input",
            str(source),
        ],
    )
    assert run.main() == 1
