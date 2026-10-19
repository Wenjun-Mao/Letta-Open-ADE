"""Seed/copy integrity is independent from Memory and Character quality."""

import pytest

from ..runtime_assets import manifest, require_runtime_assets, seed_runtime_assets


def test_fresh_assets_are_exact_private_copies_without_mutating_source(tmp_path):
    source = tmp_path / "staged/content"
    source.mkdir(parents=True)
    (source / "persona.jsonl").write_text('{"content":"exact seed"}\n')
    (source / "__pycache__").mkdir()
    (source / "__pycache__/generated.pyc").write_bytes(b"not source")
    activation = tmp_path / "activation"
    (activation / "runtime-data").mkdir(parents=True, mode=0o700)
    receipt = seed_runtime_assets(activation, source)
    target = activation / "runtime-data/content"
    assert receipt["files"] == manifest(source)["files"] == manifest(target)["files"]
    assert not (target / "__pycache__").exists()
    require_runtime_assets(activation)
    with pytest.raises(FileExistsError):
        seed_runtime_assets(activation, source)
    (target / "persona.jsonl").write_text("changed")
    assert (source / "persona.jsonl").read_text() == '{"content":"exact seed"}\n'
    with pytest.raises(ValueError, match="assets changed"):
        require_runtime_assets(activation)


def test_asset_seed_rejects_empty_or_symlinked_authority(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ValueError, match="empty"):
        manifest(source)
    (source / "escape").symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="symlinks"):
        manifest(source)
