from __future__ import annotations

import pytest

from ade_api.integrations.letta.tool_service import LettaToolService


def test_control_plane_mutations_are_not_implicitly_retried() -> None:
    attempts = 0

    class _FailingToolsApi:
        def create(self, **kwargs):
            nonlocal attempts
            attempts += 1
            raise RuntimeError("provider unavailable")

    class _FakeLettaClient:
        tools = _FailingToolsApi()

    service = LettaToolService(_FakeLettaClient())

    with pytest.raises(RuntimeError, match="provider unavailable"):
        service.create_tool(source_code="def demo():\n    return 'ok'\n")

    assert attempts == 1
