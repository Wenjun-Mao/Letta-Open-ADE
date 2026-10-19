"""Public recording is byte-bound and excludes headers/unsafe bodies at collection."""

import asyncio
import json

import httpx
import pytest

from ..live_artifacts import reference, journal_bodies
from ..public_http import PublicRecordingTransport, safe_body


def test_private_journal_records_actual_bytes_and_closes_idempotently(tmp_path):
    async def check():
        seen = []

        def server(request):
            seen.append(request)
            assert request.headers["Authorization"] == "Bearer DO-NOT-CAPTURE"
            return httpx.Response(
                200, json={"id": "actual", "content": "Original visible data"}
            )

        transport = PublicRecordingTransport(
            tmp_path / "http", inner=httpx.MockTransport(server)
        )
        async with httpx.AsyncClient(
            base_url="http://candidate",
            headers={"Authorization": "Bearer DO-NOT-CAPTURE"},
            transport=transport,
        ) as client:
            await client.post("/turns", json={"content": "Exact original input"})
            await client.get("/state")
        await transport.aclose()
        bodies = journal_bodies(
            tmp_path, reference(tmp_path, tmp_path / "http/index.json")
        )
        assert len(bodies) == 1
        raw = "".join(path.read_text() for path in (tmp_path / "http").glob("*.json"))
        assert "DO-NOT-CAPTURE" not in raw and "Authorization" not in raw
        request = json.loads((tmp_path / "http/00001.request.json").read_bytes())
        assert request["body_utf8"].encode() == seen[0].content
        assert (tmp_path / "http/00001.request.json").stat().st_mode & 0o777 == 0o600

    asyncio.run(check())


@pytest.mark.parametrize(
    "body",
    [
        b'{"api_key":"SECRET"}',
        b'{"choices":[{"reasoning_content":"SECRET"}]}',
        b'{"x":NaN}',
        b"not-json",
    ],
)
def test_unsafe_or_non_json_bodies_are_incomplete_without_raw_values(body):
    value = safe_body(body)
    assert value["input_complete"] is False
    assert "body" not in value and "body_utf8" not in value
    assert "SECRET" not in json.dumps(value)
