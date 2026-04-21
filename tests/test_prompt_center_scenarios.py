from __future__ import annotations

import pytest

from utils.prompt_persona_registry import PromptPersonaRegistry, RegistryError


def test_create_comment_persona_infers_comment_scenario_from_key(tmp_path) -> None:
    registry = PromptPersonaRegistry(tmp_path)

    record = registry.create_template(
        "persona",
        key="comment_test",
        content="Comment persona body",
    )

    assert record["scenario"] == "comment"
    assert record["key"] == "comment_test"
    assert record["source_path"] == "prompts/persona/comment/comment_test.py"
    assert (tmp_path / "prompts" / "persona" / "comment" / "comment_test.py").exists()


def test_create_chat_prompt_infers_chat_scenario_from_key(tmp_path) -> None:
    registry = PromptPersonaRegistry(tmp_path)

    record = registry.create_template(
        "prompt",
        key="chat_test",
        content="Chat prompt body",
    )

    assert record["scenario"] == "chat"
    assert record["key"] == "chat_test"
    assert record["source_path"] == "prompts/system_prompts/chat/chat_test.py"
    assert (tmp_path / "prompts" / "system_prompts" / "chat" / "chat_test.py").exists()


def test_create_template_rejects_mismatched_explicit_scenario(tmp_path) -> None:
    registry = PromptPersonaRegistry(tmp_path)

    with pytest.raises(RegistryError, match="must start with 'chat_'"):
        registry.create_template(
            "persona",
            key="comment_test",
            content="Comment persona body",
            scenario="chat",
        )


def test_comment_template_lifecycle_respects_scenario_filters(tmp_path) -> None:
    registry = PromptPersonaRegistry(tmp_path)

    registry.create_template("persona", key="chat_test", content="Chat persona body")
    registry.create_template("persona", key="comment_test", content="Comment persona body")

    listed = registry.list_templates("persona", scenario="comment")
    assert [item["key"] for item in listed] == ["comment_test"]

    archived = registry.archive_template("persona", "comment_test", scenario="comment")
    assert archived["archived"] is True
    assert archived["scenario"] == "comment"

    archived_list = registry.list_templates("persona", include_archived=True, scenario="comment")
    assert [item["key"] for item in archived_list] == ["comment_test"]

    restored = registry.restore_template("persona", "comment_test", scenario="comment")
    assert restored["archived"] is False
    assert restored["scenario"] == "comment"

    registry.archive_template("persona", "comment_test", scenario="comment")
    registry.purge_template("persona", "comment_test", scenario="comment")

    remaining = registry.list_templates("persona", include_archived=True, scenario="comment")
    assert remaining == []


def test_custom_templates_can_omit_label_and_description_metadata(tmp_path) -> None:
    registry = PromptPersonaRegistry(tmp_path)

    record = registry.create_template(
        "prompt",
        key="chat_optional_meta",
        content="Prompt body",
        label="",
        description="",
    )

    source_path = tmp_path / "prompts" / "system_prompts" / "chat" / "chat_optional_meta.py"
    source = source_path.read_text(encoding="utf-8")

    assert "LABEL =" not in source
    assert "DESCRIPTION =" not in source
    assert record["label"] == "Chat Optional Meta"
    assert record["description"] == ""
