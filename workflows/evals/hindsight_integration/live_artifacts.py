"""Private sidecar paths, physical hashes and actual HTTP journal validation."""

import hashlib
import json
from pathlib import Path

from .checks import reject_sensitive_fields
from .live_capture_contracts import FileReference, HttpJournal
from .records import digest, load_sealed, read_json
from .wire_capture import require


def reference(root: Path, path: Path) -> FileReference:
    return FileReference(
        path=path.relative_to(root).as_posix(),
        file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def referenced_file(root: Path, ref: FileReference) -> Path:
    path = root / ref.path
    relative = Path(ref.path)
    require(
        not relative.is_absolute()
        and ".." not in relative.parts
        and relative.suffix == ".json",
        "unsafe_sidecar_path",
    )
    require(path.resolve().is_relative_to(root.resolve()), "unsafe_sidecar_link")
    current = path
    while current != root:
        require(not current.is_symlink(), "unsafe_sidecar_link")
        current = current.parent
    require(
        hashlib.sha256(path.read_bytes()).hexdigest() == ref.file_sha256,
        "sidecar_file_hash_mismatch",
    )
    return path


def journal_bodies(root: Path, ref: FileReference) -> set[str]:
    index = referenced_file(root, ref)
    journal, _ = load_sealed(index, "product-http-journal", HttpJournal)
    bodies = set()
    names = {item.path for item in journal.files}
    require(len(names) == len(journal.files), "duplicate_http_journal_file")
    for sequence in range(1, journal.requests + 1):
        prefix = f"{sequence:05d}"
        require(prefix + ".request.json" in names, "http_journal_request_missing")
        require(prefix + ".response.json" in names, "http_journal_response_missing")
    require(
        len(names) == journal.requests * 2,
        "http_journal_has_unexpected_or_failed_records",
    )
    for item in journal.files:
        value = read_json(referenced_file(index.parent, item))
        reject_sensitive_fields(value)
        require(
            value.get("input_complete") is True, "unsafe_or_incomplete_http_journal"
        )
        raw = value["body_utf8"].encode()
        require(
            hashlib.sha256(raw).hexdigest() == value["body_sha256"],
            "http_body_hash_mismatch",
        )
        require(
            (json.loads(raw) if raw else None) == value["body"],
            "http_body_projection_mismatch",
        )
        if item.path.endswith(".response.json"):
            require(200 <= value["status"] < 300, "http_readback_failed")
            bodies.add(digest(value["body"]))
    return bodies
