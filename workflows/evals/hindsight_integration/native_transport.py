"""Record native HTTP outcomes and inject a lost acknowledgement after real acceptance."""

import hashlib
import json
from pathlib import Path
import time

import httpx

from .records import write_new


def public_native_value(value):
    if isinstance(value, dict):
        return {
            key: (
                "[credential excluded]"
                if key.lower()
                in {
                    "authorization",
                    "api_key",
                    "password",
                    "access_token",
                    "refresh_token",
                    "_api_key_id",
                    "api_key_id",
                }
                or key.lower().endswith("_api_key")
                else public_native_value(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [public_native_value(item) for item in value]
    return value


class NativeRecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, root: Path, *, lose_first_ack=False):
        self.root = root
        self.inner = httpx.AsyncHTTPTransport(retries=0)
        self.lose_first_ack = lose_first_ack
        self.ack_lost = False
        self.lost_operation_id = None
        self.sequence = 0

    async def handle_async_request(self, request):
        self.sequence += 1
        prefix = f"{self.sequence:05d}"
        raw = await request.aread()
        write_new(
            self.root / f"{prefix}.request.json",
            {
                "method": request.method,
                "url": str(request.url),
                "time": time.time(),
                "body_utf8": raw.decode("utf-8"),
                "body_sha256": hashlib.sha256(raw).hexdigest(),
            },
        )
        try:
            response = await self.inner.handle_async_request(request)
            await response.aread()
        except Exception as exc:
            write_new(
                self.root / f"{prefix}.failure.json",
                {
                    "error_type": type(exc).__name__,
                    "time": time.time(),
                },
            )
            raise
        try:
            value = public_native_value(response.json())
        except ValueError:
            value = {
                "non_json_response": True,
                "body_sha256": hashlib.sha256(response.content).hexdigest(),
            }
        drop = (
            self.lose_first_ack
            and not self.ack_lost
            and request.method == "POST"
            and request.url.path.endswith("/memories")
            and response.is_success
        )
        write_new(
            self.root / f"{prefix}.response.json",
            {
                "status": response.status_code,
                "body": value,
                "time": time.time(),
                "injected_lost_acknowledgement": drop,
            },
        )
        if drop:
            self.ack_lost = True
            self.lost_operation_id = json.loads(raw)["operation_id"]
            await response.aclose()
            raise httpx.ReadTimeout(
                "Injected loss after server response", request=request
            )
        return response

    async def aclose(self):
        await self.inner.aclose()
