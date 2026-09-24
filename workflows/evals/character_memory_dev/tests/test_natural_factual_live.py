"""Local alias contract for the one-shot factual diagnostic host."""

import socket
import json

from workflows.evals.character_memory_dev.natural_factual_live import (
    FIXTURE,
    install_spark_alias,
    selected_cases,
)


def test_spark_alias_accepts_sync_and_async_dns_forms(monkeypatch):
    resolved = []

    def fake_getaddrinfo(name, *args, **kwargs):
        resolved.append(name)
        return []

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    install_spark_alias("192.0.2.5")

    socket.getaddrinfo("dgx-spark", 8001)
    socket.getaddrinfo(b"dgx-spark", 8001)
    socket.getaddrinfo("example.com", 443)

    assert resolved == ["192.0.2.5", "192.0.2.5", "example.com"]


def test_followup_selects_only_frozen_failed_and_unrun_cases():
    fixture = json.loads(FIXTURE.read_text())
    schedule_id, schedule_sha256, cases = selected_cases(fixture, follow_up_eight=True)
    assert schedule_id == "natural-factual-continuity-followup-20260924-v1"
    assert len(schedule_sha256) == 64
    assert [case["id"] for case in cases] == [
        "distinct_evening_preference",
        "uncertainty_and_habit",
        "other_subject_probe",
    ]
    assert sum(len(case["turns"]) for case in cases) == 8
