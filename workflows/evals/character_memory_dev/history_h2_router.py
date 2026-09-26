"""Run H2 embedding calls inside the configured development router container."""

from __future__ import annotations

import asyncio
import json
import subprocess
from typing import Any

from ade_api.features.agent_runtime.history_native_rank import HISTORY_EMBEDDING_ROUTE

CONTAINER_ROUTER_SCRIPT = """
import asyncio, json, sys
from ade_api.platform.settings import AdeApiSettings
from ade_api.features.agent_runtime.embeddings import EmbeddingClient
from ade_api.features.agent_runtime.router_transport import RouterTransport

request = json.load(sys.stdin)
settings = AdeApiSettings()
transport = RouterTransport(
    settings.model_router_v1_base_url(),
    settings.resolve_model_router_api_key(),
)
async def main():
    if request['op'] == 'catalog':
        result = await transport.catalog(timeout_seconds=10)
        return {'items': [item for item in result.get('items', [])
                if item.get('model_key') == request['route']]}
    return {'vectors': await EmbeddingClient(transport).embed(
        model_key=request['route'], inputs=request['inputs'],
        timeout_seconds=request['timeout_seconds'])}
print(json.dumps(asyncio.run(main())))
"""


class ContainerEmbeddingClient:
    """Use the configured dev router without copying its credential to the host."""

    def __init__(self, container: str) -> None:
        self.container = container

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        completed = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                self.container,
                "python",
                "-c",
                CONTAINER_ROUTER_SCRIPT,
            ],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
            timeout=max(15, float(payload.get("timeout_seconds", 10)) + 15),
        )
        if completed.returncode:
            # The container's stderr can contain provider details. Preserve only
            # the exit status in the redacted probe record.
            raise RuntimeError(
                f"configured router request exited {completed.returncode}"
            )
        return json.loads(completed.stdout)

    async def catalog(self) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._request, {"op": "catalog", "route": HISTORY_EMBEDDING_ROUTE}
        )

    async def embed(
        self, *, inputs: list[str], timeout_seconds: float
    ) -> list[list[float]]:
        result = await asyncio.to_thread(
            self._request,
            {
                "op": "embed",
                "route": HISTORY_EMBEDDING_ROUTE,
                "inputs": inputs,
                "timeout_seconds": timeout_seconds,
            },
        )
        return result["vectors"]
