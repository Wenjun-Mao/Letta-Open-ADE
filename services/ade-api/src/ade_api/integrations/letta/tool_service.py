from __future__ import annotations

from typing import Any

from letta_client import Letta


class LettaToolService:
    """ADE's typed boundary for Letta's global tool catalog."""

    def __init__(self, client: Letta):
        self._client = client

    @staticmethod
    def _serialize_tool(tool: Any) -> dict[str, Any]:
        tags = [
            str(tag) for tag in (getattr(tool, "tags", None) or []) if str(tag).strip()
        ]
        return {
            "id": str(getattr(tool, "id", "") or ""),
            "name": str(getattr(tool, "name", "") or ""),
            "description": str(getattr(tool, "description", "") or ""),
            "tool_type": str(getattr(tool, "tool_type", "") or ""),
            "source_type": str(getattr(tool, "source_type", "") or ""),
            "created_at": str(getattr(tool, "created_at", "") or ""),
            "last_updated_at": str(getattr(tool, "last_updated_at", "") or ""),
            "tags": tags,
            "source_code": str(getattr(tool, "source_code", "") or ""),
            "return_char_limit": getattr(tool, "return_char_limit", None),
            "enable_parallel_execution": bool(
                getattr(tool, "enable_parallel_execution", False)
            ),
            "default_requires_approval": bool(
                getattr(tool, "default_requires_approval", False)
            ),
        }

    def list_available_tools(
        self,
        *,
        search: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        list_kwargs: dict[str, Any] = {"limit": max(1, min(int(limit), 500))}
        if query := (search or "").strip():
            list_kwargs["search"] = query
        return [
            self._serialize_tool(tool)
            for tool in self._client.tools.list(**list_kwargs)
        ]

    def retrieve_tool(self, *, tool_id: str) -> dict[str, Any]:
        resolved_tool_id = str(tool_id or "").strip()
        if not resolved_tool_id:
            raise ValueError("tool_id is required")
        return self._serialize_tool(
            self._client.tools.retrieve(tool_id=resolved_tool_id)
        )

    def create_tool(
        self,
        *,
        source_code: str,
        description: str | None = None,
        tags: list[str] | None = None,
        source_type: str | None = "python",
        enable_parallel_execution: bool | None = None,
        default_requires_approval: bool | None = None,
        return_char_limit: int | None = None,
        pip_requirements: list[dict[str, Any]] | None = None,
        npm_requirements: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not str(source_code or "").strip():
            raise ValueError("source_code is required")

        create_kwargs: dict[str, Any] = {"source_code": source_code}
        optional_values = {
            "description": description,
            "tags": tags or None,
            "source_type": source_type,
            "enable_parallel_execution": enable_parallel_execution,
            "default_requires_approval": default_requires_approval,
            "return_char_limit": return_char_limit,
            "pip_requirements": pip_requirements or None,
            "npm_requirements": npm_requirements or None,
        }
        create_kwargs.update(
            {key: value for key, value in optional_values.items() if value is not None}
        )
        return self._serialize_tool(self._client.tools.create(**create_kwargs))

    def update_tool(
        self,
        *,
        tool_id: str,
        source_code: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        source_type: str | None = None,
        enable_parallel_execution: bool | None = None,
        default_requires_approval: bool | None = None,
        return_char_limit: int | None = None,
        pip_requirements: list[dict[str, Any]] | None = None,
        npm_requirements: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        resolved_tool_id = str(tool_id or "").strip()
        if not resolved_tool_id:
            raise ValueError("tool_id is required")

        optional_values = {
            "source_code": source_code,
            "description": description,
            "tags": tags,
            "source_type": source_type,
            "enable_parallel_execution": enable_parallel_execution,
            "default_requires_approval": default_requires_approval,
            "return_char_limit": return_char_limit,
            "pip_requirements": pip_requirements,
            "npm_requirements": npm_requirements,
        }
        update_kwargs = {
            key: value for key, value in optional_values.items() if value is not None
        }
        if not update_kwargs:
            raise ValueError("At least one updatable tool field is required")
        return self._serialize_tool(
            self._client.tools.update(tool_id=resolved_tool_id, **update_kwargs)
        )

    def delete_tool(self, *, tool_id: str) -> None:
        resolved_tool_id = str(tool_id or "").strip()
        if not resolved_tool_id:
            raise ValueError("tool_id is required")
        self._client.tools.delete(tool_id=resolved_tool_id)
