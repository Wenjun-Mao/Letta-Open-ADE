"""Populate or verify the candidate's exact public CPU reranker snapshot."""

import hashlib
import json
import os
from pathlib import Path


REPOSITORY = "BAAI/bge-reranker-v2-m3"
REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
WEIGHT_SIZE = 2_271_071_852
WEIGHT_SHA256 = "d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286"
FILES = (
    "model.safetensors",
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "sentencepiece.bpe.model",
    "README.md",
)


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify(target: Path) -> dict:
    weight = target / "model.safetensors"
    if weight.stat().st_size != WEIGHT_SIZE or file_sha256(weight) != WEIGHT_SHA256:
        raise ValueError("Pinned reranker weight mismatch")
    if not all(
        (target / name).is_file() for name in ("config.json", "tokenizer_config.json")
    ):
        raise ValueError("Pinned reranker configuration is incomplete")
    return {
        "repository": REPOSITORY,
        "revision": REVISION,
        "files_sha256": {
            name: file_sha256(target / name)
            for name in FILES
            if (target / name).is_file()
        },
    }


def main() -> None:
    from huggingface_hub import snapshot_download

    target = Path("/models/bge-v2-m3")
    manifest_path = target / "snapshot-manifest.json"
    if not manifest_path.is_file():
        snapshot_download(
            repo_id=REPOSITORY,
            revision=REVISION,
            local_dir=target,
            allow_patterns=list(FILES),
            max_workers=1,
        )
        manifest = verify(target)
        with manifest_path.open("x") as output:
            json.dump(manifest, output, sort_keys=True)
    elif json.loads(manifest_path.read_text()) != verify(target):
        raise ValueError("Pinned reranker manifest changed")
    for path in [Path("/models"), *Path("/models").rglob("*")]:
        os.chown(path, 1000, 1000)
    print("pinned_reranker_cache_verified")


if __name__ == "__main__":
    main()
