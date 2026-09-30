import ast
import asyncio
import json
import socket
import subprocess
import sys

import httpx
import pytest

from ..annotation import check_annotation, freeze_annotation
from ..api import OfflineADE
from ..schedule import (
    ROOT,
    FIXTURE,
    dependency_status,
    frozen_schedule,
    prepare,
    prompt_for,
)


def test_offline_prepare_pins_real_prompt_reviewer_and_settings(monkeypatch):
    def no_socket(*args, **kwargs):
        raise AssertionError("Network is not permitted")

    monkeypatch.setattr(socket, "create_connection", no_socket)
    packet = prepare()
    assert packet["provider_dispatch"] == "unavailable"
    assert packet["status"] == "offline_ready_live_approval_required"
    assert (
        packet["governed_source_fingerprint_v2"]
        == subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "scripts/source_fingerprint.py"),
                "--root",
                str(ROOT),
            ],
            text=True,
        ).strip()
    )
    assert (
        packet["model_profiles_sha256"]
        == packet["source_files"]["config/model-router/model-profiles.json"]
    )
    assert len(packet["offline_readiness_items"]) == 3
    assert packet["native_prerequisites"]
    assert len(packet["schedule"]) == 10
    for suffix in (
        "chat_v20260926.py",
        "natural_memory_review.py",
        "natural_memory_reviewer.py",
        "history_capacity.py",
        "deployment-manifest.json",
        "model-profiles.json",
        "personas.jsonl",
    ):
        assert any(path.endswith(suffix) for path in packet["source_files"])
    assert all(len(value) == 64 for value in packet["source_files"].values())


def test_no_runtime_internals_or_database_imports_in_workflow():
    for path in FIXTURE.parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
            assert not any(
                name.startswith(("ade_api", "sqlalchemy", "psycopg")) for name in names
            )


def test_schedule_dependencies_and_no_answer_slots_in_recalls():
    schedule = frozen_schedule()
    assert {control["annotation"] for control in schedule["controls"]} >= {
        "concrete_solo_episode",
        "hypothetical_not_established",
        "faithful_user_recall",
        "warm_nonhistorical_expression",
        "demonstrable_correction",
        "core_contradiction",
    }
    assert all(
        control["expected_user_fact_changes"] == 0 for control in schedule["controls"]
    )
    for turn in schedule["turns"]:
        if turn["depends_on"]:
            assert dependency_status(turn, {}) == "unassessable_dependency"
            assert (
                dependency_status(turn, {1: {"disposition": "rejected"}})
                == "unassessable_dependency"
            )
        if turn["id"] != 4:
            assert "{" not in prompt_for(turn)
            with pytest.raises(ValueError, match="context"):
                prompt_for(turn, replacement_suggestion="诊断答案")
    assert schedule["turns"][6]["archive_before"] == ["origin", "callback"]
    assert schedule["turns"][6]["version"] == 2


def test_annotation_freezes_actual_arbitrary_native_details_before_targets():
    args = dict(
        run_id="r",
        reply="我独自看过海边的灯塔。",
        committed=True,
        at_turn=1,
        observed_turns=[1],
        quotes=["海边的灯塔"],
        rationale="具体独自经历",
        replacement_suggestion="改成山里的木屋",
    )
    record = freeze_annotation(**args)
    assert check_annotation(
        record, expected_sha256=record["sha256"], run_id="r", reply=args["reply"]
    )
    for changes in (
        {"committed": False},
        {"observed_turns": [1, 2]},
        {"quotes": ["银杏叶"]},
    ):
        with pytest.raises(ValueError):
            freeze_annotation(**(args | changes))
    with pytest.raises(ValueError, match="Stale"):
        check_annotation(
            record, expected_sha256="0" * 64, run_id="r", reply=args["reply"]
        )


def test_no_network_transport_or_implicit_retry():
    with pytest.raises(ValueError, match="in-process"):
        OfflineADE(httpx.AsyncHTTPTransport())
    requests = []

    def handler(request):
        requests.append(request)
        assert json.loads(request.content)["retry_count"] == 0
        return httpx.Response(503, json={"detail": "scripted failure"})

    with pytest.raises(ValueError, match="503"):
        asyncio.run(
            OfflineADE(httpx.MockTransport(handler)).accept(
                "c", prompt="你好", key="one"
            )
        )
    assert len(requests) == 1
