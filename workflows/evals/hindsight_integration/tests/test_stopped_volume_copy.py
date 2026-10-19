"""Physical-copy integrity without running a database or reading existing stores."""

import json
import os

import pytest

from .. import copy_stopped_volume as copy


@pytest.fixture
def stores(tmp_path):
    source, target = tmp_path / "source", tmp_path / "target"
    source.mkdir(mode=0o700)
    target.mkdir()
    (source / "PG_VERSION").write_text("17\n")
    (source / "base").mkdir(mode=0o700)
    (source / "base/data").write_bytes(b"controlled physical pages\0" * 7)
    (source / "base/data").chmod(0o600)
    return source, target


def test_exact_contents_modes_owners_and_timestamps_are_preserved(stores):
    source, target = stores
    before = copy.manifest(source)
    result = copy.copy_store(source, target)
    assert result["source_before"] == result["source_after"] == before
    assert result["target_before_startup"] == copy.manifest(target) == before
    assert result["copy_verified"] and result["source_unchanged"]
    assert len(result["manifest_sha256"]) == 64


@pytest.mark.parametrize(
    "bad",
    ["symlink", "hardlink", "postmaster.pid", "no_version", "nonempty", "same_target"],
)
def test_unbounded_or_nonshutdown_sources_and_existing_targets_are_rejected(
    stores, bad
):
    source, target = stores
    if bad == "symlink":
        (source / "base/link").symlink_to("/outside")
    elif bad == "hardlink":
        os.link(source / "PG_VERSION", source / "version-link")
    elif bad == "postmaster.pid":
        (source / bad).write_text("123")
    elif bad == "no_version":
        (source / "PG_VERSION").unlink()
    elif bad == "nonempty":
        (target / "previous").write_text("keep")
    else:
        target = source
    with pytest.raises(ValueError):
        copy.copy_store(source, target)


@pytest.mark.parametrize("changed", ["source", "target"])
def test_changed_source_or_corrupted_copy_cannot_be_certified(
    stores, monkeypatch, changed
):
    source, target = stores
    manifest, calls = copy.manifest, []

    def read(root):
        calls.append(root)
        if len(calls) == 2:
            ((source if changed == "source" else target) / "PG_VERSION").write_text(
                "changed"
            )
        return manifest(root)

    monkeypatch.setattr(copy, "manifest", read)
    with pytest.raises(ValueError, match="manifest_mismatch"):
        copy.copy_store(source, target)


def test_cli_receipt_is_create_only_private_and_owned_by_evidence_directory(
    stores, tmp_path, monkeypatch
):
    source, target = stores
    receipt = tmp_path / "copy.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "copy",
            "--source",
            str(source),
            "--target",
            str(target),
            "--receipt",
            str(receipt),
        ],
    )
    copy.main()
    assert json.loads(receipt.read_bytes())["copy_verified"]
    assert receipt.stat().st_mode & 0o777 == 0o600
    assert receipt.stat().st_uid == tmp_path.stat().st_uid


def test_symlink_directory_is_not_traversed(stores, tmp_path):
    source, target = stores
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "data").write_text("must not copy")
    (source / "tablespace").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="link_or_special"):
        copy.copy_store(source, target)
    assert list(target.iterdir()) == []
