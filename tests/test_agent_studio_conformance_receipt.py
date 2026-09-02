from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime

from scripts.record_agent_studio_conformance import (
    CONFORMANCE_TESTS,
    record_conformance,
)


def test_conformance_receipt_records_exact_contract_suite(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "scripts.record_agent_studio_conformance._git",
        lambda _root, *args: "a" * 40 if args[0] == "rev-parse" else "",
    )
    monkeypatch.setattr(
        "scripts.record_agent_studio_conformance.source_fingerprint",
        lambda _root: "b" * 64,
    )
    output = tmp_path / "conformance.json"

    receipt = record_conformance(
        project_root=tmp_path,
        output_path=output,
        run=lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="20 passed", stderr=""
        ),
        now=lambda: datetime(2026, 9, 3, tzinfo=UTC),
    )

    assert receipt["passed"] is True
    assert receipt["test_paths"] == list(CONFORMANCE_TESTS)
    assert json.loads(output.read_text(encoding="utf-8")) == receipt
    assert len(receipt["artifact_sha256"]) == 64


def test_conformance_receipt_fails_for_dirty_source(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.record_agent_studio_conformance._git",
        lambda _root, *args: "a" * 40 if args[0] == "rev-parse" else " M file",
    )
    monkeypatch.setattr(
        "scripts.record_agent_studio_conformance.source_fingerprint",
        lambda _root: "b" * 64,
    )

    receipt = record_conformance(
        project_root=tmp_path,
        output_path=tmp_path / "receipt.json",
        run=lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="passed", stderr=""
        ),
    )

    assert receipt["passed"] is False
