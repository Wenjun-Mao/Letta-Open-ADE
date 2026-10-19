"""Native feasibility fixtures, fault placement and evidence constraints."""

import asyncio
import json

import httpx
import pytest

from workflows.evals.hindsight_integration.native_cases import freeze_native_case
from workflows.evals.hindsight_integration.native_checks import require_document_source
from workflows.evals.hindsight_integration.native_transport import (
    NativeRecordingTransport,
    public_native_value,
)


@pytest.mark.parametrize(
    "case_id",
    ["q01-relevant", "q02-correction", "q02-change", "reference", "attribution"],
)
def test_native_sources_are_frozen_and_never_claim_product_establishment(case_id):
    plan, sources = freeze_native_case(case_id)
    assert plan["provenance"] == "controlled_native_sources_not_product_dialogue"
    assert len(sources) == len(plan["actor"]["history"])
    assert all(source.relationship == sources[0].relationship for source in sources)
    assert "rubric" not in plan["actor"]
    assert "calibration" not in plan["actor"]
    for source, seed in zip(sources, plan["actor"]["history"], strict=True):
        assert source.content == seed["content"]
        assert source.role == seed["role"]


def test_lost_ack_is_injected_only_after_a_real_transport_response_and_is_recorded(
    tmp_path,
):
    operation = "1824da03-1d25-4e5b-a287-7c5959720e65"
    calls = []

    def provider(request):
        calls.append(request)
        return httpx.Response(200, json={"operation_id": operation, "success": True})

    async def scenario():
        transport = NativeRecordingTransport(tmp_path, lose_first_ack=True)
        transport.inner = httpx.MockTransport(provider)
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(httpx.ReadTimeout):
                await client.post(
                    "http://native/v1/default/banks/test/memories",
                    json={"operation_id": operation},
                )
            assert transport.lost_operation_id == operation
            await client.post(
                "http://native/v1/default/banks/test/memories",
                json={"operation_id": operation},
            )

    asyncio.run(scenario())
    assert len(calls) == 2
    first = json.loads((tmp_path / "00001.response.json").read_bytes())
    second = json.loads((tmp_path / "00002.response.json").read_bytes())
    assert first["injected_lost_acknowledgement"] is True
    assert first["body"]["operation_id"] == operation
    assert second["injected_lost_acknowledgement"] is False


def test_native_document_checks_reject_source_or_antecedent_rewrites():
    item = {"content": "source", "context": "earlier attributed context"}
    require_document_source(
        {"original_text": "source", "retain_params": {"context": item["context"]}}, item
    )
    with pytest.raises(ValueError, match="source changed"):
        require_document_source({"original_text": "changed"}, item)
    with pytest.raises(ValueError, match="antecedent attribution"):
        require_document_source({"original_text": "source", "retain_params": {}}, item)


def test_native_credential_fields_are_removed_without_dropping_source_text():
    value = {
        "task_payload": {
            "_api_key_id": "private",
            "api_key": "secret",
            "content": "original source",
        }
    }
    result = public_native_value(value)
    assert result["task_payload"]["content"] == "original source"
    assert "private" not in json.dumps(result)
    assert "secret" not in json.dumps(result)
