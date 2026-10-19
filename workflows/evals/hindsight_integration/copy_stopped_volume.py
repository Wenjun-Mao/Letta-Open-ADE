"""Read-only physical copy of a stopped PostgreSQL store, with exact manifests."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat


def manifest(root):
    rows = []
    for path in [root, *sorted(root.rglob("*"))]:
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            kind, size, digest = "directory", 0, None
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            kind, size = "file", info.st_size
            hasher = hashlib.sha256()
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    hasher.update(chunk)
            digest = hasher.hexdigest()
        else:
            raise ValueError("stopped_store_contains_link_or_special_file")
        rows.append(
            {
                "path": str(path.relative_to(root)),
                "type": kind,
                "mode": stat.S_IMODE(info.st_mode),
                "uid": info.st_uid,
                "gid": info.st_gid,
                "mtime_ns": info.st_mtime_ns,
                "bytes": size,
                "sha256": digest,
            }
        )
    return rows


def copy_store(source, target):
    if source.resolve() == target.resolve() or any(target.iterdir()):
        raise ValueError("stopped_store_copy_requires_empty_distinct_target")
    before = manifest(source)
    if (
        not any(row["path"] == "PG_VERSION" for row in before)
        or (source / "postmaster.pid").exists()
    ):
        raise ValueError("stopped_store_not_a_shutdown_postgres_directory")
    for row in before:
        original, copied = source / row["path"], target / row["path"]
        if row["type"] == "directory":
            if row["path"] != ".":
                copied.mkdir()
            continue
        descriptor = os.open(original, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as reader, copied.open("xb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
    # Restore directory timestamps last; creating children changes their parents.
    for row in reversed(before):
        copied = target / row["path"]
        os.chown(copied, row["uid"], row["gid"])
        os.chmod(copied, row["mode"])
        os.utime(copied, ns=(row["mtime_ns"], row["mtime_ns"]))
    after, destination = manifest(source), manifest(target)
    if before != after or before != destination:
        raise ValueError("stopped_store_copy_manifest_mismatch")
    return {
        "source_before": before,
        "source_after": after,
        "target_before_startup": destination,
        "manifest_sha256": hashlib.sha256(
            json.dumps(before, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "source_unchanged": True,
        "copy_verified": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    result = copy_store(args.source, args.target)
    descriptor = os.open(args.receipt, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    owner = args.receipt.parent.stat()
    with os.fdopen(descriptor, "w") as target:
        os.fchown(target.fileno(), owner.st_uid, owner.st_gid)
        json.dump(result, target, sort_keys=True, allow_nan=False)
        target.flush()
        os.fsync(target.fileno())


if __name__ == "__main__":
    main()
