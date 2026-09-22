import json
import subprocess
import sys
from pathlib import Path

import pytest

from workflows.evals.character_memory_dev import luna
from workflows.evals.character_memory_dev.tasks import build_prompt, validate_result


def events(final='{"reply":"hello"}'):
    return "\n".join(
        json.dumps(event)
        for event in [
            {"type": "thread.started", "thread_id": "test-thread"},
            {"type": "turn.started"},
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "id": "item-1",
                    "text": final,
                },
            },
            {"type": "turn.completed"},
        ]
    )


def fake_cli(monkeypatch, source):
    real_popen = subprocess.Popen
    calls = []
    monkeypatch.setattr(luna, "preflight", lambda env: "fixture-cli")

    def launch(args, **kwargs):
        calls.append(args)
        assert args[0:4] == ["codex", "exec", "--ignore-user-config", "--ignore-rules"]
        assert args[args.index("--model") + 1] == "gpt-5.6-luna"
        assert args[args.index("--sandbox") + 1] == "read-only"
        assert not list(Path(kwargs["cwd"]).iterdir())
        assert kwargs["env"] == luna.subscription_environment()
        final = args[args.index("--output-last-message") + 1]
        return real_popen([sys.executable, "-c", source, final], **kwargs)

    monkeypatch.setattr(luna.subprocess, "Popen", launch)
    return calls


def test_success_and_existing_output_never_replayed(monkeypatch, tmp_path):
    raw = '{"reply":"hello"}'
    source = (
        "import sys; from pathlib import Path; sys.stdin.read(); "
        f"Path(sys.argv[1]).write_text({raw!r}); print({events(raw)!r})"
    )
    calls = fake_cli(monkeypatch, source)
    output = tmp_path / "one"
    assert luna.generate("test", output) == raw
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["status"] == "transport_validated"
    assert manifest["usage"] is None
    assert manifest["adapter_retry_count"] == 0
    with pytest.raises(FileExistsError):
        luna.generate("test", output)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "source,timeout,error",
    [
        (
            "import sys; sys.stderr.write('unsupported flag'); sys.exit(2)",
            10,
            "CLI exited 2",
        ),
        ("import time; time.sleep(20)", 0.1, "timed out"),
        ("import sys; print('x' * 2000100)", 10, "capture limit"),
    ],
)
def test_failure_captured_without_retry(monkeypatch, tmp_path, source, timeout, error):
    calls = fake_cli(monkeypatch, source)
    with pytest.raises(luna.LunaFailure, match=error):
        luna.generate("test", tmp_path / "call", timeout_seconds=timeout)
    manifest = json.loads((tmp_path / "call/manifest.json").read_text())
    assert manifest["status"] == "uncertain_or_invalid"
    assert len(calls) == 1
    assert (tmp_path / "call/stderr.txt").exists()


@pytest.mark.parametrize(
    "auth,code", [("Logged in using an API key", 0), ("Not logged in", 1)]
)
def test_auth_rejected(monkeypatch, auth, code):
    def run(args, **kwargs):
        return subprocess.CompletedProcess(
            args,
            code if "login" in args else 0,
            "fixture-cli" if "--version" in args else "",
            auth,
        )

    monkeypatch.setattr(luna.subprocess, "run", run)
    with pytest.raises(luna.LunaFailure):
        luna.preflight(luna.subscription_environment())


def test_environment_drops_keys_and_overrides(monkeypatch):
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_HOME", "OPENAI_BASE_URL"):
        monkeypatch.setenv(key, "must-not-propagate")
    assert set(luna.subscription_environment()) <= {
        "HOME",
        "PATH",
        "LANG",
        "LC_ALL",
        "TMPDIR",
    }


@pytest.mark.parametrize(
    "raw,final",
    [
        ("not json", "x"),
        (events() + '\n{"type":"turn.started"}', '{"reply":"hello"}'),
        (events().replace("agent_message", "command_execution"), '{"reply":"hello"}'),
        (events(), "different"),
        (events(""), ""),
        (events().replace("test-thread", ""), '{"reply":"hello"}'),
    ],
)
def test_invalid_event_stream(raw, final):
    with pytest.raises((ValueError, luna.LunaFailure)):
        luna.validate_events(raw, final)


@pytest.mark.parametrize(
    "raw",
    ["null", "[]", events().replace('"thread_id": "test-thread"', '"thread_id": 1')],
)
def test_event_shape_rejected(raw):
    with pytest.raises(luna.LunaFailure):
        luna.validate_events(raw, '{"reply":"hello"}')


DATA = {"messages": [{"id": "u1", "role": "user", "content": "My dog is Rocky"}]}


def test_real_persona_used_and_prompt_data_encoded():
    prompt = build_prompt("dialogue", DATA)
    assert "林小棠" in prompt
    assert "chat_linxiaotang" not in prompt
    assert "My dog is Rocky" in prompt


@pytest.mark.parametrize(
    "raw", ["oops", "[]", '{"reply":""}', '{"reply":"hi","extra":1}']
)
def test_dialogue_schema_failure(raw):
    with pytest.raises(ValueError):
        validate_result("dialogue", raw, DATA)


def test_review_rejects_unknown_and_assistant_evidence():
    data = {
        "messages": DATA["messages"]
        + [{"id": "a1", "role": "assistant", "content": "fiction"}]
    }
    for ref in ("invented", "a1"):
        raw = json.dumps(
            {
                "proposals": [
                    {
                        "kind": "user_fact",
                        "summary": "a fact",
                        "source_message_ids": [ref],
                    }
                ]
            }
        )
        with pytest.raises(ValueError):
            validate_result("memory-review", raw, data)


def test_review_and_judge_valid():
    assert validate_result("memory-review", '{"proposals":[]}', DATA) == {
        "proposals": []
    }
    result = validate_result(
        "judge", '{"assessment":"uncertain","reason":"No evidence"}', DATA
    )
    assert result["assessment"] == "uncertain"


def test_timeout_kills_spawned_child(monkeypatch, tmp_path):
    pid_path = tmp_path / "child.pid"
    source = (
        "import subprocess,sys,time; from pathlib import Path; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
        f"Path({str(pid_path)!r}).write_text(str(child.pid)); time.sleep(30)"
    )
    fake_cli(monkeypatch, source)
    with pytest.raises(luna.LunaFailure, match="timed out"):
        luna.generate("test", tmp_path / "call", timeout_seconds=0.5)
    pid = int(pid_path.read_text())
    monkeypatch.undo()
    # A terminated orphan may briefly remain a zombie until the OS reaps it.
    result = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True
    )
    assert result.returncode != 0 or result.stdout.strip().startswith("Z")
