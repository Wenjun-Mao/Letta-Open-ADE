"""Exclusive, durable experiment receipts; capture errors are fatal."""

from __future__ import annotations

import os
from pathlib import Path

from .hindsight_eval_contracts import EvaluationError, json_bytes


class EvaluationCapture:
    def __init__(self, directory: Path):
        self.directory = directory
        try:
            directory.mkdir(mode=0o700)
            descriptor = os.open(directory.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise EvaluationError("capture_directory_unavailable") from exc

    def write(self, filename: str, value: object) -> None:
        created = False
        try:
            data = json_bytes(value)
            descriptor = os.open(
                self.directory / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
            created = True
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            descriptor = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except (OSError, ValueError, TypeError) as exc:
            if created:
                # A partially durable completion marker must not survive a
                # failed write. Never remove a pre-existing receipt.
                try:
                    (self.directory / filename).unlink()
                except OSError:
                    pass
            raise EvaluationError("capture_write_failed") from exc
