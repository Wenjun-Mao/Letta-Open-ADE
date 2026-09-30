"""Scripted HTTP controls only; no native model-quality evidence."""

import asyncio

import httpx
import pytest

from ..native_transport import NativeADE


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8000",
        "http://localhost:8000",
        "http://example.com:8000",
        "http://127.0.0.1",
        "http://x:y@127.0.0.1:8000",
        "http://127.0.0.1:8000/api",
        "http://127.0.0.1:8000?x=1",
    ],
)
def test_remote_ambiguous_or_credentialed_address_rejected(url):
    with pytest.raises(ValueError, match="loopback"):
        NativeADE(url, "test-only")


def test_http_failures_are_not_retried_or_echoed():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(503, text="sensitive provider error body")

    async def scenario():
        api = NativeADE(
            "http://127.0.0.1:9000", "test-only", transport=httpx.MockTransport(handle)
        )
        try:
            with pytest.raises(ValueError, match="HTTP 503") as error:
                await api.request("POST", "/api/v3/conversations/c/turns", {})
            assert "sensitive" not in str(error.value)
            assert len(calls) == 1
            assert calls[0].headers["Authorization"] == "Bearer test-only"
        finally:
            await api.close()

    asyncio.run(scenario())


def test_only_readback_polling_repeats(monkeypatch):
    calls = []

    def handle(request):
        calls.append(request.method)
        return httpx.Response(
            200,
            json={"id": "r", "status": "running" if len(calls) == 1 else "succeeded"},
        )

    async def no_sleep(_):
        pass

    monkeypatch.setattr("asyncio.sleep", no_sleep)

    async def scenario():
        api = NativeADE(
            "http://127.0.0.1:9000", "test-only", transport=httpx.MockTransport(handle)
        )
        try:
            assert (await api.wait_terminal("r"))["status"] == "succeeded"
            assert calls == ["GET", "GET"]
            with pytest.raises(TimeoutError, match="never resubmit"):
                await api.wait_terminal("r", seconds=0)
        finally:
            await api.close()

    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["truncated", "subject", "purpose", "conversation"])
def test_incomplete_or_cross_scope_readback_rejected(failure):
    state = {
        "id": "c",
        "memory_subject_id": "s",
        "purpose": "evaluation",
        "messages_truncated": False,
    }
    if failure == "truncated":
        state["messages_truncated"] = True
    elif failure == "subject":
        state["memory_subject_id"] = "other"
    elif failure == "purpose":
        state["purpose"] = "development"
    else:
        state["id"] = "other"

    def handle(request):
        return httpx.Response(
            200,
            json=state if request.url.path.endswith("/state") else {"subject_id": "s"},
        )

    async def scenario():
        api = NativeADE(
            "http://127.0.0.1:9000", "test-only", transport=httpx.MockTransport(handle)
        )
        try:
            with pytest.raises(ValueError, match="cross-scope"):
                await api.readback(
                    "c", "s", {"id": "r", "status": "succeeded", "conversation_id": "c"}
                )
        finally:
            await api.close()

    asyncio.run(scenario())
