"""P1 only: populate owned cache from exact HF snapshot, never remote-code loading."""

import hashlib
import json
import os
from pathlib import Path

REPOSITORY = "BAAI/bge-reranker-v2-m3"
REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"

if __name__ == "__main__":
    from huggingface_hub import snapshot_download

    target = Path("/models/bge-v2-m3")
    if target.exists():
        raise SystemExit("model_cache_already_exists_verify_manifest_instead")
    snapshot_download(repo_id=REPOSITORY, revision=REVISION, local_dir=target)
    files = {
        str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in target.rglob("*")
        if p.is_file() and ".cache" not in p.parts
    }
    manifest = {"repository": REPOSITORY, "revision": REVISION, "files_sha256": files}
    (target / "snapshot-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n"
    )
    # Provisioning runs as root without live credentials; ordinary Hindsight stays UID1000.
    for path in [Path("/models"), *Path("/models").rglob("*")]:
        os.chown(path, 1000, 1000)
    print("pinned_model_cache_created")
