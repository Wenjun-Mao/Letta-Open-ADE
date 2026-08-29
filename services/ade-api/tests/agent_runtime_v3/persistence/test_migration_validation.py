from __future__ import annotations

from ade_api.features.agent_runtime_v3.persistence.validation import (
    alembic_config,
    migration_heads,
    service_root,
)


def test_migration_has_one_reviewed_head() -> None:
    assert migration_heads() == ("20260829_0001",)


def test_initial_migration_is_static_not_live_metadata() -> None:
    migration = (
        service_root()
        / "migrations"
        / "versions"
        / "20260829_0001_ade_native_runtime.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS vector" in source
    assert "CREATE SCHEMA IF NOT EXISTS ade" in source
    assert "persistence.metadata" not in source


def test_alembic_version_table_is_owned_with_runtime_schema() -> None:
    config = alembic_config()
    assert config.get_main_option("version_table_schema") == "ade"
    assert config.get_main_option("owner_role") == "ade_owner"


def test_online_environment_owns_the_transaction_started_by_set_role() -> None:
    source = (service_root() / "migrations" / "env.py").read_text(encoding="utf-8")
    assert "with connectable.begin() as connection" in source
    assert "with connectable.connect() as connection" not in source
