"""Offline checks for minimal pinned model-cache selection and streamed hashes."""

import hashlib

from workflows.evals.hindsight_memory_probe.qualification import cache_model


def test_model_snapshot_allowlist_contains_runtime_and_license_files_only():
    assert cache_model.ALLOW_PATTERNS == (
        "model.safetensors", "config.json", "tokenizer.json", "tokenizer_config.json",
        "special_tokens_map.json", "sentencepiece.bpe.model", "README.md",
    )
    assert "pytorch_model.bin" not in cache_model.ALLOW_PATTERNS


def test_manifest_streams_weight_hash_and_records_selected_files(tmp_path, monkeypatch):
    weight = b"synthetic-safetensors-weight"
    expected_hash = hashlib.sha256(weight).hexdigest()
    (tmp_path / "model.safetensors").write_bytes(weight)
    (tmp_path / "config.json").write_text("{}")
    (tmp_path / "README.md").write_text("license provenance")
    (tmp_path / "pytorch_model.bin").write_bytes(b"excluded")
    monkeypatch.setattr(cache_model, "EXPECTED_WEIGHT_SIZE", len(weight))
    monkeypatch.setattr(cache_model, "EXPECTED_WEIGHT_SHA256", expected_hash)
    manifest = cache_model.snapshot_manifest(tmp_path)
    assert manifest["files_sha256"] == {
        "model.safetensors": expected_hash,
        "config.json": hashlib.sha256(b"{}").hexdigest(),
        "README.md": hashlib.sha256(b"license provenance").hexdigest(),
    }


def test_manifest_rejects_weight_hash_and_size_drift(tmp_path, monkeypatch):
    (tmp_path / "model.safetensors").write_bytes(b"weight")
    monkeypatch.setattr(cache_model, "EXPECTED_WEIGHT_SIZE", 6)
    monkeypatch.setattr(cache_model, "EXPECTED_WEIGHT_SHA256", "0" * 64)
    import pytest

    with pytest.raises(RuntimeError, match="hash_mismatch"):
        cache_model.snapshot_manifest(tmp_path)

    monkeypatch.setattr(cache_model, "EXPECTED_WEIGHT_SIZE", 99)
    with pytest.raises(RuntimeError, match="size_mismatch"):
        cache_model.snapshot_manifest(tmp_path)
