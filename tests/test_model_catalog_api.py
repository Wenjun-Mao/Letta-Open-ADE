from __future__ import annotations

import asyncio

import agent_platform_api.runtime as runtime
from agent_platform_api.routers import core, platform_meta
from utils.model_catalog import CatalogEntry, CatalogModelRecord, CatalogSnapshot, CatalogSourceRecord


def _snapshot_fixture() -> tuple[CatalogSnapshot, list[CatalogEntry]]:
    snapshot = CatalogSnapshot(
        generated_at=123.0,
        sources=(
            CatalogSourceRecord(
                id="local_unsloth",
                label="Local Unsloth",
                kind="openai-compatible",
                base_url="http://127.0.0.1:2234/v1",
                enabled_for=("comment",),
                letta_handle_prefix="lmstudio_openai",
                status="healthy",
                detail="ok",
                models=(
                    CatalogModelRecord(provider_model_id="gemma-4-31b-it", model_type="llm"),
                ),
                raw_model_count=1,
                filtered_model_count=1,
            ),
            CatalogSourceRecord(
                id="local_lmstudio",
                label="Local LM Studio",
                kind="openai-compatible",
                base_url="http://127.0.0.1:1234/v1",
                enabled_for=("chat", "comment"),
                letta_handle_prefix="lmstudio_openai",
                status="healthy",
                detail="ok",
                models=(CatalogModelRecord(provider_model_id="local-model", model_type="llm"),),
                raw_model_count=1,
                filtered_model_count=1,
            ),
            CatalogSourceRecord(
                id="ark",
                label="Volcengine Ark",
                kind="openai-compatible",
                base_url="https://ark.example/v3",
                enabled_for=("chat", "comment"),
                letta_handle_prefix="openai-proxy",
                status="healthy",
                detail="Allowlist applied: 1 of 3 catalog entries remain selectable.",
                models=(CatalogModelRecord(provider_model_id="doubao-seed-1-8-251228", model_type="llm"),),
                allowlist_applied=True,
                allowlist_checked_at="2026-04-22T12:00:00+00:00",
                raw_model_count=3,
                filtered_model_count=1,
            ),
        ),
    )
    entries = [
        CatalogEntry(
            source_id="local_unsloth",
            source_label="Local Unsloth",
            source_kind="openai-compatible",
            base_url="http://127.0.0.1:2234/v1",
            enabled_for=("comment",),
            provider_model_id="gemma-4-31b-it",
            model_type="llm",
            model_key="local_unsloth::gemma-4-31b-it",
            letta_handle="lmstudio_openai/gemma-4-31b-it",
        ),
        CatalogEntry(
            source_id="local_lmstudio",
            source_label="Local LM Studio",
            source_kind="openai-compatible",
            base_url="http://127.0.0.1:1234/v1",
            enabled_for=("chat", "comment"),
            provider_model_id="local-model",
            model_type="llm",
            model_key="local_lmstudio::local-model",
            letta_handle="lmstudio_openai/local-model",
        ),
        CatalogEntry(
            source_id="ark",
            source_label="Volcengine Ark",
            source_kind="openai-compatible",
            base_url="https://ark.example/v3",
            enabled_for=("chat", "comment"),
            provider_model_id="doubao-seed-1-8-251228",
            model_type="llm",
            model_key="ark::doubao-seed-1-8-251228",
            letta_handle="openai-proxy/doubao-seed-1-8-251228",
        ),
    ]
    return snapshot, entries


def test_options_api_filters_chat_handles_and_keeps_comment_model_keys(monkeypatch) -> None:
    snapshot, entries = _snapshot_fixture()
    monkeypatch.setattr(core, "ensure_platform_api_enabled", lambda: None)
    monkeypatch.setattr(runtime.model_catalog_service, "snapshot", lambda force_refresh=False: snapshot)
    monkeypatch.setattr(runtime.model_catalog_service, "flatten", lambda payload: entries)
    monkeypatch.setattr(
        runtime,
        "_resolve_letta_catalog_handles",
        lambda: (
            {
                "lmstudio_openai/local-model",
                "openai-proxy/doubao-seed-1-8-251228",
            },
            {"letta/letta-free"},
        ),
    )

    chat_payload = asyncio.run(core.api_get_options(refresh=True, scenario="chat"))
    assert chat_payload["defaults"]["model"] == ""
    assert [item["key"] for item in chat_payload["models"]] == [
        "openai-proxy/doubao-seed-1-8-251228",
        "lmstudio_openai/local-model",
    ]
    assert {item["source_id"] for item in chat_payload["models"]} == {"ark", "local_lmstudio"}

    comment_payload = asyncio.run(core.api_get_options(refresh=True, scenario="comment"))
    assert comment_payload["defaults"]["model"] == ""
    assert [item["key"] for item in comment_payload["models"]] == [
        "local_unsloth::gemma-4-31b-it",
        "local_lmstudio::local-model",
        "ark::doubao-seed-1-8-251228",
    ]
    assert comment_payload["models"][0]["provider_model_id"] == "gemma-4-31b-it"


def test_model_catalog_api_reports_source_health_and_enriched_items(monkeypatch) -> None:
    snapshot, entries = _snapshot_fixture()
    monkeypatch.setattr(platform_meta, "ensure_platform_api_enabled", lambda: None)
    monkeypatch.setattr(runtime.model_catalog_service, "snapshot", lambda force_refresh=False: snapshot)
    monkeypatch.setattr(runtime.model_catalog_service, "flatten", lambda payload: entries)
    monkeypatch.setattr(
        runtime,
        "_resolve_letta_catalog_handles",
        lambda: ({"lmstudio_openai/local-model", "openai-proxy/doubao-seed-1-8-251228"}, {"letta/letta-free"}),
    )

    payload = asyncio.run(platform_meta.api_platform_model_catalog(refresh=True))
    local_model = next(item for item in payload["items"] if item["provider_model_id"] == "local-model")
    ark_source = next(source for source in payload["sources"] if source["id"] == "ark")

    assert payload["generated_at"] == 123.0
    assert [source["status"] for source in payload["sources"]] == ["healthy", "healthy", "healthy"]
    assert ark_source["allowlist_applied"] is True
    assert ark_source["raw_model_count"] == 3
    assert ark_source["filtered_model_count"] == 1
    assert local_model["agent_studio_available"] is True
    assert local_model["comment_lab_available"] is True
