from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime

from ade_api.features.agent_runtime.release_evidence import (
    REQUIRED_CONFORMANCE_TESTS,
    canonical_sha256,
)
from scripts.record_agent_studio_conformance import (
    CONFORMANCE_TESTS,
    record_conformance,
)


def _patch_clean_source(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.record_agent_studio_conformance._git",
        lambda _root, *args: "a" * 40 if args[0] == "rev-parse" else "",
    )
    monkeypatch.setattr(
        "scripts.record_agent_studio_conformance.source_fingerprint",
        lambda _root: "b" * 64,
    )


def test_conformance_receipt_records_the_exact_release_contract_suite(
    tmp_path, monkeypatch
) -> None:
    _patch_clean_source(monkeypatch)
    output = tmp_path / "conformance.json"

    receipt = record_conformance(
        project_root=tmp_path,
        output_path=output,
        run=lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="20 passed", stderr=""
        ),
        now=lambda: datetime(2026, 9, 7, tzinfo=UTC),
    )

    assert CONFORMANCE_TESTS == REQUIRED_CONFORMANCE_TESTS
    assert receipt["passed"] is True
    assert receipt["test_paths"] == list(REQUIRED_CONFORMANCE_TESTS)
    assert json.loads(output.read_text(encoding="utf-8")) == receipt
    assert (
        canonical_sha256(
            {key: value for key, value in receipt.items() if key != "artifact_sha256"}
        )
        == receipt["artifact_sha256"]
    )


def test_conformance_receipt_fails_closed_for_dirty_source_or_failed_contracts(
    tmp_path, monkeypatch
) -> None:
    _patch_clean_source(monkeypatch)
    failed = record_conformance(
        project_root=tmp_path,
        output_path=tmp_path / "failed.json",
        run=lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=1, stdout="1 failed", stderr=""
        ),
    )
    assert failed["passed"] is False

    monkeypatch.setattr(
        "scripts.record_agent_studio_conformance._git",
        lambda _root, *args: "a" * 40 if args[0] == "rev-parse" else " M runtime.py",
    )
    dirty = record_conformance(
        project_root=tmp_path,
        output_path=tmp_path / "dirty.json",
        run=lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="passed", stderr=""
        ),
    )
    assert dirty["passed"] is False
