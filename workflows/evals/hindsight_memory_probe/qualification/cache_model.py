"""P1 only: populate the owned cache from an exact, minimal HF snapshot."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

REPOSITORY = "BAAI/bge-reranker-v2-m3"
REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
EXPECTED_WEIGHT_SIZE = 2_271_071_852
EXPECTED_WEIGHT_SHA256 = "d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286"
ALLOW_PATTERNS = (
    "model.safetensors",
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "sentencepiece.bpe.model",
    "README.md",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_manifest(target: Path) -> dict:
    files = {}
    for relative in ALLOW_PATTERNS:
        path = target / relative
        if not path.is_file():
            continue
        if relative == "model.safetensors":
            if path.stat().st_size != EXPECTED_WEIGHT_SIZE:
                raise RuntimeError("pinned_model_weight_size_mismatch")
            digest = sha256_file(path)
            if digest != EXPECTED_WEIGHT_SHA256:
                raise RuntimeError("pinned_model_weight_hash_mismatch")
        files[relative] = sha256_file(path)
    if "model.safetensors" not in files:
        raise RuntimeError("pinned_model_weight_missing")
    return {"repository": REPOSITORY, "revision": REVISION, "files_sha256": files}


def main() -> None:
    from huggingface_hub import snapshot_download

    target = Path("/models/bge-v2-m3")
    if target.exists():
        raise SystemExit("model_cache_already_exists_verify_manifest_instead")
    snapshot_download(
        repo_id=REPOSITORY,
        revision=REVISION,
        local_dir=target,
        allow_patterns=list(ALLOW_PATTERNS),
        max_workers=1,
    )
    manifest = snapshot_manifest(target)
    (target / "snapshot-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n"
    )
    # Provisioning runs as root without live credentials; ordinary Hindsight stays UID1000.
    for path in [Path("/models"), *Path("/models").rglob("*")]:
        os.chown(path, 1000, 1000)
    print("pinned_model_cache_created")


if __name__ == "__main__":
    main()
