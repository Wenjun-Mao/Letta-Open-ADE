"""Native wire shapes and failure behavior of the concrete integration client."""

import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from ade_api.integrations.hindsight import HindsightClient, HindsightError


BANK = "ade-bank-a"
OPERATION = str(uuid4())
PAYLOAD = json.dumps(
    {"async": True, "operation_id": OPERATION, "items": [{"content": "source"}]},
    ensure_ascii=False,
).encode()


def run(handler, exercise):
    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as transport:
            client = HindsightClient(
                base_url="http://hindsight:8888",
                api_key="private-key",
                client=transport,
            )
            await exercise(client)

    asyncio.run(scenario())


def test_lost_acknowledgement_can_be_polled_without_automatic_resubmission():
    requests = []

    def handler(request):
        requests.append(request)
        if request.method == "POST":
            assert request.content == PAYLOAD
            raise httpx.ReadTimeout("acknowledgement lost", request=request)
        assert request.url.params["include_payload"] == "true"
        return httpx.Response(
            200,
            json={"operation_id": OPERATION, "status": "completed", "bank_id": BANK},
        )

    async def exercise(client):
        with pytest.raises(HindsightError, match="hindsight_unavailable"):
            await client.submit(BANK, operation_id=OPERATION, payload=PAYLOAD)
        assert len(requests) == 1
        result = await client.operation(BANK, OPERATION)
        assert result["status"] == "completed"

    run(handler, exercise)
    assert [request.method for request in requests] == ["POST", "GET"]


def test_terminal_failure_uses_the_native_retry_endpoint_and_same_identity():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.method == "POST"
        assert request.url.path.endswith(f"/operations/{OPERATION}/retry")
        return httpx.Response(200, json={"operation_id": OPERATION, "success": True})

    async def exercise(client):
        assert (await client.retry_operation(BANK, OPERATION))["success"] is True

    run(handler, exercise)
    assert len(requests) == 1


def test_native_missing_operation_is_an_explicit_reconciliation_state():
    async def exercise(client):
        assert (await client.operation(BANK, OPERATION))["status"] == "not_found"

    run(
        lambda request: httpx.Response(
            200, json={"operation_id": OPERATION, "status": "not_found"}
        ),
        exercise,
    )


@pytest.mark.parametrize("status", [401, 404, 409, 429, 500])
def test_recall_errors_remain_errors_and_do_not_expose_response_or_credentials(status):
    def handler(request):
        return httpx.Response(status, json={"detail": "sensitive provider contents"})

    async def exercise(client):
        with pytest.raises(HindsightError) as captured:
            await client.recall(BANK, {"query": "test"})
        assert captured.value.status_code == status
        assert str(captured.value) == "hindsight_http_error"

    run(handler, exercise)


@pytest.mark.parametrize("response", [{}, {"results": None}, {"results": ["bad"]}])
def test_successful_http_does_not_turn_malformed_recall_into_empty_memory(response):
    async def exercise(client):
        with pytest.raises(HindsightError, match="hindsight_recall_invalid"):
            await client.recall(BANK, {"query": "test"})

    run(lambda request: httpx.Response(200, json=response), exercise)


def test_successful_empty_recall_is_distinct_from_failure():
    async def exercise(client):
        assert await client.recall(BANK, {"query": "test"}) == {"results": []}

    run(lambda request: httpx.Response(200, json={"results": []}), exercise)


def test_submit_rejects_a_changed_operation_before_sending():
    def handler(request):
        pytest.fail("A mismatched payload must not be sent")

    async def exercise(client):
        with pytest.raises(ValueError, match="bind one source"):
            await client.submit(BANK, operation_id=str(uuid4()), payload=PAYLOAD)

    run(handler, exercise)


@pytest.mark.parametrize(
    "response",
    [
        {"bank_id": "other", "operation_id": OPERATION, "async": True, "success": True},
        {"bank_id": BANK, "operation_id": str(uuid4()), "async": True, "success": True},
        {"bank_id": BANK, "operation_id": OPERATION, "success": True},
    ],
)
def test_native_acknowledgement_must_match_bank_operation_and_async_mode(response):
    async def exercise(client):
        with pytest.raises(HindsightError):
            await client.submit(BANK, operation_id=OPERATION, payload=PAYLOAD)

    run(lambda request: httpx.Response(200, json=response), exercise)


@pytest.mark.parametrize("status", ["unknown", None, 1])
def test_unknown_operation_states_are_not_processing_success(status):
    async def exercise(client):
        with pytest.raises(HindsightError, match="hindsight_operation_invalid"):
            await client.operation(BANK, OPERATION)

    run(
        lambda request: httpx.Response(
            200, json={"operation_id": OPERATION, "status": status}
        ),
        exercise,
    )
