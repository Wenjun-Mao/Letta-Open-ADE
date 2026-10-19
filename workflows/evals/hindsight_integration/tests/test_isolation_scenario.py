"""A foreign read must really fail; an empty or successful response is not denial."""

import asyncio

import httpx
import pytest

from ..isolation_scenario import forged_reads


@pytest.mark.parametrize("status", [200, 403, 404, 503])
def test_forged_source_operation_and_retry_require_exact_not_found(status):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(status, json={"detail": "controlled"})

    async def check():
        async with httpx.AsyncClient(
            base_url="http://synthetic.invalid", transport=httpx.MockTransport(respond)
        ) as api:
            return await forged_reads(
                api,
                "/relationship",
                {"document_id": "doc", "operation_id": "op", "check_count": 7},
            )

    if status == 404:
        result = asyncio.run(check())
        assert [row["status"] for row in result] == [404, 404, 404]
        assert [row.method for row in requests] == ["GET", "GET", "POST"]
        assert requests[-1].content == b'{"expected_check_count":7}'
    else:
        with pytest.raises(ValueError, match="isolation_status"):
            asyncio.run(check())
