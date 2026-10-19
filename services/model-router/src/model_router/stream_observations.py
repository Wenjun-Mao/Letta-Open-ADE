"""Capture visible SSE response fields while preserving downstream byte streaming."""

import codecs
import json

from model_router.request_observations import RequestObservation, visible_response


class StreamObservation:
    def __init__(self, observation: RequestObservation | None):
        self.observation = observation
        self.decoder = codecs.getincrementaldecoder("utf-8")()
        self.pending = ""
        self.events = []
        self.complete = False
        self.valid = True
        self.bytes_seen = 0

    def feed(self, chunk: bytes) -> None:
        if self.observation is None or not self.valid:
            return
        self.bytes_seen += len(chunk)
        if self.bytes_seen > 8 * 1024 * 1024:
            self.valid = False
            return
        try:
            self.pending += self.decoder.decode(chunk)
            while "\n" in self.pending:
                line, self.pending = self.pending.split("\n", 1)
                line = line.rstrip("\r")
                if not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    self.complete = True
                elif data:
                    value = json.loads(data)
                    if not isinstance(value, dict):
                        raise ValueError("Invalid SSE object")
                    self.events.append(visible_response(value))
        except (ValueError, UnicodeError):
            self.valid = False

    def finish(self, status_code: int, *, error_type: str | None = None) -> bool:
        if self.observation is None:
            return True
        try:
            tail = self.decoder.decode(b"", final=True)
            if tail or self.pending.strip():
                self.valid = False
        except UnicodeError:
            self.valid = False
        return self.observation.outcome(
            {
                "http_status": status_code,
                "status": "stream_finished",
                "response_capture_complete": self.complete
                and self.valid
                and error_type is None,
                "visible_events": self.events,
                "error_type": error_type,
            }
        )
