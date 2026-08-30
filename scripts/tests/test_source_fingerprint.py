from __future__ import annotations

import os
from pathlib import Path

from scripts.source_fingerprint import source_fingerprint


def test_source_fingerprint_is_order_independent_and_content_addressed(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "b.txt").write_text("beta", encoding="utf-8")

    first = source_fingerprint(tmp_path, (b"b.txt", b"a.txt"))
    second = source_fingerprint(tmp_path, (b"a.txt", b"b.txt"))
    (tmp_path / "b.txt").write_text("changed", encoding="utf-8")
    changed = source_fingerprint(tmp_path, (b"a.txt", b"b.txt"))

    assert first == second
    assert changed != first


def test_source_fingerprint_distinguishes_missing_symlink_and_executable(
    tmp_path: Path,
) -> None:
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link"
    link.symlink_to("target.txt")
    script = tmp_path / "run.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    paths = (b"missing.txt", b"link", b"run.sh")

    initial = source_fingerprint(tmp_path, paths)
    script.chmod(script.stat().st_mode | 0o100)
    executable = source_fingerprint(tmp_path, paths)
    link.unlink()
    link.write_text("target.txt", encoding="utf-8")
    regular_file = source_fingerprint(tmp_path, paths)

    assert executable != initial
    assert regular_file != executable
    assert len(initial) == 64
    assert os.path.islink(tmp_path / "link") is False
