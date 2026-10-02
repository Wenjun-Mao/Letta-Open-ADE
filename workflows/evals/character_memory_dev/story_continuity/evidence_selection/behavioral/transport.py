"""Public Model Router HTTP only; one send, no redirect or transport retry."""

import asyncio
import base64
from urllib.parse import urlsplit

import httpx

from .contracts import wire


class Router:
    def __init__(self, base_url: str, token: str, *, transport=None):
        address = urlsplit(base_url)
        if (
            address.scheme != "http"
            or address.hostname != "127.0.0.1"
            or not address.port
            or address.username
            or address.password
            or address.path
            or address.query
            or address.fragment
            or not token
        ):
            raise ValueError("Authenticated isolated loopback Model Router required")
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=180,
            trust_env=False,
            follow_redirects=False,
            transport=transport,
        )

    async def close(self):
        await self.client.aclose()

    async def catalog(self):
        async with asyncio.timeout(180):
            response = await self.client.get("/v1/router/model-catalog?refresh=true")
        return self.capture(response)

    async def send(self, request: dict):
        async with asyncio.timeout(180):
            response = await self.client.post(
                "/v1/chat/completions",
                content=wire(request).encode(),
                headers={"Content-Type": "application/json"},
            )
        return self.capture(response)

    @staticmethod
    def capture(response):
        # No auth or endpoint headers enter receipts. Exact body bytes remain
        # private, including reasoning/errors; publication requires review.
        return {
            "status": response.status_code,
            "body_base64": base64.b64encode(response.content).decode(),
        }
