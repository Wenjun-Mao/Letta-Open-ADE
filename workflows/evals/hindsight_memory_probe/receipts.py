"""Private, immutable receipts. Capture is part of dispatch authorization."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path


class CaptureFailure(RuntimeError):
    def __init__(self):
        super().__init__("probe_capture_failed")


class ReceiptStore:
    def __init__(self, directory: Path):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or directory.stat().st_mode & 0o077:
            raise CaptureFailure()
        self.directory = directory
        self.failed = (
            any(directory.glob("*.failure.json"))
            or any(directory.glob(".*.partial"))
            or any(
                not (
                    directory
                    / (path.name.removesuffix(".incoming.json") + ".response.json")
                ).is_file()
                for path in directory.glob("*.incoming.json")
            )
        )

    def write(self, name: str, value: dict) -> None:
        self.write_bytes(
            name,
            (
                json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True)
                + "\n"
            ).encode(),
        )

    def write_bytes(self, name: str, value: bytes) -> None:
        if Path(name).name != name:
            raise CaptureFailure()
        try:
            temporary = self.directory / f".{uuid.uuid4().hex}.partial"
            descriptor = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
            # Exclusive atomic publication prevents concurrent guard readers seeing partial JSON.
            os.link(temporary, self.directory / name)
            os.unlink(temporary)
            descriptor = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except (OSError, ValueError, TypeError) as from_exception:
            raise CaptureFailure() from from_exception

    def failure(self, request_id: str, code: str) -> None:
        self.failed = True
        try:
            self.write(
                request_id + ".failure.json",
                {"qualification": "failed", "code": code, "request_id": request_id},
            )
        except CaptureFailure:
            # Disk loss cannot promise another durable write. Fixed code only, never exc text.
            os.write(2, b"probe_qualification_failed_capture_unavailable\n")
