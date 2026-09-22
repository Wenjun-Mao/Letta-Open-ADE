"""Subscription-authenticated generation with one fresh Codex CLI turn."""

from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from .json_contract import loads


MODEL = "gpt-5.6-luna"
MAX_BYTES = 2_000_000


class LunaFailure(RuntimeError):
    pass


def subscription_environment() -> dict[str, str]:
    env = {
        key: os.environ[key]
        for key in ("HOME", "PATH", "LANG", "LC_ALL", "TMPDIR")
        if key in os.environ
    }
    if not env.get("HOME") or not env.get("PATH"):
        raise LunaFailure("HOME and PATH are required for subscription login")
    return env


def preflight(env: dict[str, str]) -> str:
    version = subprocess.run(
        ["codex", "--version"], env=env, capture_output=True, text=True, timeout=15
    )
    auth = subprocess.run(
        ["codex", "login", "status"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    if version.returncode or auth.returncode:
        raise LunaFailure("Codex version/login preflight failed")
    if (auth.stdout + auth.stderr).strip() != "Logged in using ChatGPT":
        raise LunaFailure("This lane requires ChatGPT login, not API-key billing")
    return version.stdout.strip()


def validate_events(raw: str, final: str) -> dict:
    events = [loads(line) for line in raw.splitlines() if line.strip()]
    if any(not isinstance(event, dict) for event in events):
        raise LunaFailure("CLI event must be an object")
    if [event.get("type") for event in events] != [
        "thread.started",
        "turn.started",
        "item.completed",
        "turn.completed",
    ]:
        raise LunaFailure("Unexpected CLI events; no tools or extra turns allowed")
    item = events[2].get("item", {})
    if not isinstance(item, dict):
        raise LunaFailure("CLI message item must be an object")
    if any(
        not isinstance(value, str) or not value.strip()
        for value in (events[0].get("thread_id"), item.get("id"))
    ):
        raise LunaFailure("Missing event identity")
    if item.get("type") != "agent_message" or not final.strip():
        raise LunaFailure("Expected one nonempty final agent message")
    if not isinstance(item.get("text"), str) or item["text"].strip() != final.strip():
        raise LunaFailure("Final file and event message disagree")
    return {"thread_id": events[0]["thread_id"], "usage": events[3].get("usage")}


def _stop(proc: subprocess.Popen) -> None:
    # The session owns the entire CLI process group, including spawned children.
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


@contextmanager
def _termination_signals():
    requested = []
    previous = {}

    def defer(signum, frame):
        # Do not raise between spawning the process and acquiring its handle.
        requested.append(signum)

    try:
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[signum] = signal.signal(signum, defer)
        yield requested
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def generate(prompt: str, output: Path, *, timeout_seconds: float = 180) -> str:
    """Reserve an output directory once; never replay a failed/uncertain call."""
    if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 600:
        raise ValueError("timeout_seconds must be in (0, 600]")
    if len(prompt.encode("utf-8")) > 64_000:
        raise ValueError("Prompt exceeds the 64 KB development limit")
    if os.name != "posix":
        raise LunaFailure("This transport is qualified only for macOS/Linux")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        "status": "reserved",
        "requested_model": MODEL,
        "reasoning_effort": "medium",
        "service_tier": "default",
        "timeout_seconds": timeout_seconds,
        "adapter_retry_count": 0,
        "generation_started": False,
    }
    manifest_path = output / "manifest.json"

    def save() -> None:
        temporary = output / "manifest.tmp"
        temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        temporary.replace(manifest_path)

    save()
    started = time.monotonic()
    try:
        env = subscription_environment()
        manifest["cli_version"] = preflight(env)
        manifest["authentication"] = "ChatGPT"
        (output / "prompt.txt").write_text(prompt, encoding="utf-8")
        final_path = output / "final.txt"
        with tempfile.TemporaryDirectory(prefix="ade-luna-") as cwd:
            args = [
                "codex",
                "exec",
                "--ignore-user-config",
                "--ignore-rules",
                "-c",
                'approval_policy="never"',
                "-c",
                'model_reasoning_effort="medium"',
                "-c",
                'service_tier="default"',
                "--json",
                "--ephemeral",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--model",
                MODEL,
                "-C",
                cwd,
                "--output-last-message",
                str(final_path),
                "-",
            ]
            paths = [output / "events.jsonl", output / "stderr.txt", final_path]
            with (
                (output / "prompt.txt").open("rb") as stdin,
                paths[0].open("wb") as stdout,
                paths[1].open("wb") as stderr,
                _termination_signals() as termination,
            ):
                manifest["status"] = "running"
                save()
                proc = None
                try:
                    if termination:
                        raise LunaFailure("Terminated before generation")
                    proc = subprocess.Popen(
                        args,
                        cwd=cwd,
                        env=env,
                        stdin=stdin,
                        stdout=stdout,
                        stderr=stderr,
                        start_new_session=True,
                    )
                    manifest["generation_started"] = True
                    deadline = time.monotonic() + timeout_seconds
                    save()
                    while proc.poll() is None:
                        if termination:
                            raise LunaFailure(f"Terminated by signal {termination[0]}")
                        if time.monotonic() >= deadline:
                            raise LunaFailure(
                                "Generation timed out; usage is uncertain"
                            )
                        if any(
                            p.exists() and p.stat().st_size > MAX_BYTES for p in paths
                        ):
                            raise LunaFailure("CLI output exceeded capture limit")
                        time.sleep(0.05)
                    if termination:
                        raise LunaFailure(f"Terminated by signal {termination[0]}")
                finally:
                    if proc is not None:
                        _stop(proc)
                        manifest["exit_code"] = proc.returncode
            if proc.returncode:
                raise LunaFailure(f"CLI exited {proc.returncode}; inspect stderr.txt")
            if any(p.exists() and p.stat().st_size > MAX_BYTES for p in paths):
                raise LunaFailure("CLI output exceeded capture limit")
            final = final_path.read_text(encoding="utf-8")
            manifest.update(
                validate_events(paths[0].read_text(encoding="utf-8"), final)
            )
        manifest["status"] = "transport_validated"
        return final
    except BaseException as exc:
        manifest["status"] = (
            "failed" if not manifest["generation_started"] else "uncertain_or_invalid"
        )
        manifest["error"] = str(exc)
        raise
    finally:
        manifest["elapsed_seconds"] = round(time.monotonic() - started, 3)
        save()
