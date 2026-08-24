from __future__ import annotations

import asyncio

from ade_api.features.schema_center import api as schema_center
from ade_api.features.schema_center.registry import (
    LabelSchemaRegistry,
    default_label_extraction_schema,
)


def test_schema_center_routes_manage_label_schemas(monkeypatch, tmp_path) -> None:
    registry = LabelSchemaRegistry(tmp_path)
    monkeypatch.setattr(schema_center, "ensure_ade_api_enabled", lambda: None)

    created = asyncio.run(
        schema_center.api_schema_center_create_label_schema(
            schema_center.LabelSchemaWriteRequest(
                key="label_test_schema",
                label="Test Schema",
                description="For tests.",
                schema=default_label_extraction_schema(),
            ),
            registry,
        )
    )
    assert created["key"] == "label_test_schema"

    listed = asyncio.run(schema_center.api_schema_center_list_label_schemas(registry))
    assert listed["total"] == 1
    assert listed["items"][0]["schema"]["required"] == [
        "people",
        "organizations",
        "locations",
        "dates",
        "events",
    ]

    updated = asyncio.run(
        schema_center.api_schema_center_update_label_schema(
            "label_test_schema",
            schema_center.LabelSchemaPatchRequest(description="Updated."),
            registry,
        )
    )
    assert updated["description"] == "Updated."

    archived = asyncio.run(
        schema_center.api_schema_center_archive_label_schema(
            "label_test_schema",
            registry,
        )
    )
    assert archived["archived"] is True
    restored = asyncio.run(
        schema_center.api_schema_center_restore_label_schema(
            "label_test_schema",
            registry,
        )
    )
    assert restored["archived"] is False
