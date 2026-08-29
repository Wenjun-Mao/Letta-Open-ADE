from __future__ import annotations

import pytest

from ade_api.features.agent_runtime_v3.bootstrap import (
    BootstrapConfig,
    _replace_database,
)


def test_bootstrap_rejects_unsafe_identifiers() -> None:
    config = BootstrapConfig(
        admin_url="postgresql://postgres:secret@postgres/postgres",
        database_name="ade; DROP DATABASE letta",
        app_password="secret",
    )
    with pytest.raises(ValueError, match="safe lowercase SQL identifier"):
        config.validate()


def test_bootstrap_requires_distinct_least_privilege_role() -> None:
    config = BootstrapConfig(
        admin_url="postgresql://postgres:secret@postgres/postgres",
        owner_role="ade_owner",
        app_role="ade_owner",
        app_password="secret",
    )
    with pytest.raises(ValueError, match="must be different"):
        config.validate()


def test_replace_database_preserves_connection_authority() -> None:
    result = _replace_database(
        "postgresql://postgres:secret@postgres:5432/postgres?connect_timeout=4",
        "ade",
    )
    assert "dbname=ade" in result
    assert "host=postgres" in result
    assert "connect_timeout=4" in result
