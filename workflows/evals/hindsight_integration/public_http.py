"""Private, create-only HTTP journals for the synthetic product actor and collector."""

import hashlib
import json
from pathlib import Path
import time

import httpx

from .checks import reject_sensitive_fields
from .records import json_bytes, seal, write_new


def safe_body(raw: bytes) -> dict:
    result = {"body_sha256": hashlib.sha256(raw).hexdigest()}
    if not raw:
        return {**result, "input_complete": True, "body_utf8": "", "body": None}
    try:
        text = raw.decode("utf-8")
        value = json.loads(text)
        reject_sensitive_fields(value)
        json_bytes(value)
    except (ValueError, TypeError, UnicodeError):
        return {
            **result,
            "input_complete": False,
            "limitation": "unsafe_or_non_json_body_excluded",
        }
    return {**result, "input_complete": True, "body_utf8": text, "body": value}


class PublicRecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, root: Path, *, inner: httpx.AsyncBaseTransport | None = None):
        root.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.root = root
        self.inner = inner or httpx.AsyncHTTPTransport(retries=0)
        self.sequence = 0
        self.files = []
        self.closed = False

    def write(self, name, value):
        path = self.root / name
        write_new(path, value)
        self.files.append(
            {"path": name, "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        )

    async def handle_async_request(self, request):
        self.sequence += 1
        prefix = f"{self.sequence:05d}"
        raw = await request.aread()
        self.write(
            prefix + ".request.json",
            {
                "method": request.method,
                "url": str(request.url),
                "time": time.time(),
                **safe_body(raw),
            },
        )
        try:
            response = await self.inner.handle_async_request(request)
            await response.aread()
        except Exception as exc:
            self.write(
                prefix + ".failure.json",
                {"time": time.time(), "error_type": type(exc).__name__},
            )
            raise
        self.write(
            prefix + ".response.json",
            {
                "status": response.status_code,
                "time": time.time(),
                **safe_body(response.content),
            },
        )
        return response

    async def aclose(self):
        if self.closed:
            return
        self.closed = True
        await self.inner.aclose()
        write_new(
            self.root / "index.json",
            seal(
                "product-http-journal",
                {"schema_version": 1, "requests": self.sequence, "files": self.files},
            ),
        )


async def get_json(client, path: str, **kwargs):
    response = await client.get(path, **kwargs)
    response.raise_for_status()
    value = response.json()
    reject_sensitive_fields(value)
    return value


async def post_json(client, path: str, body: dict):
    reject_sensitive_fields(body)
    response = await client.post(path, json=body)
    response.raise_for_status()
    value = response.json()
    reject_sensitive_fields(value)
    return value
