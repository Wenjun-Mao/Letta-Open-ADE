"""P0/P1 offline clean release export. No credentials, generated receipts or dirty files."""

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def bundle(output):
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip():
        raise RuntimeError("clean_commit_required")
    sha = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    )
    raw = subprocess.check_output(["git", "archive", "--format=tar", sha], cwd=ROOT)
    hashes = {}
    with tarfile.open(fileobj=io.BytesIO(raw)) as source:
        for member in source:
            if member.isfile():
                if (
                    member.name == ".env"
                    or "/outputs/" in member.name
                    or member.name.endswith("secrets.env")
                ):
                    raise RuntimeError("private_file_in_release")
                hashes[member.name] = hashlib.sha256(
                    source.extractfile(member).read()
                ).hexdigest()
    value = {
        "source_sha": sha,
        "source_dirty": False,
        "file_sha256": hashes,
        "git_archive_sha256": hashlib.sha256(raw).hexdigest(),
    }
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = output / (sha + ".tar")
    with target.open("xb") as stream:
        stream.write(raw)
    # tar append replaces terminal zero blocks with a clean-source manifest, no private state.
    with tarfile.open(target, "a") as archive:
        data = (json.dumps(value, sort_keys=True) + "\n").encode()
        info = tarfile.TarInfo(".probe-release.json")
        info.size, info.mode = len(data), 0o600
        archive.addfile(info, io.BytesIO(data))
    target.chmod(0o600)
    print(sha)
    return sha


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    bundle(parser.parse_args().output_directory)
