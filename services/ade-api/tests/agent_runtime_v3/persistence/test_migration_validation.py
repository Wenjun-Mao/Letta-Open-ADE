from __future__ import annotations

from ade_api.features.agent_runtime_v3.persistence.validation import (
    alembic_config,
    migration_heads,
    service_root,
)


def test_migration_has_one_reviewed_head() -> None:
    assert migration_heads() == ("20260902_0006",)


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


def test_compaction_migration_preserves_legacy_rows_and_enforces_provenance() -> None:
    migration = (
        service_root()
        / "migrations"
        / "versions"
        / "20260830_0002_ade_conversation_compaction.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert "legacy-unattributed" in source
    assert "previous_summary_id" in source
    assert "prompt_sha256" in source
    assert "input_sha256" in source


def test_worker_health_migration_has_process_level_heartbeat_contract() -> None:
    migration = (
        service_root()
        / "migrations"
        / "versions"
        / "20260830_0003_agent_runtime_worker_health.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert "ade.worker_instances" in source
    assert "contract_version" in source
    assert "heartbeat_at" in source
    assert "stopped_at" in source


def test_worker_source_fingerprint_migration_preserves_existing_health_rows() -> None:
    migration = (
        service_root()
        / "migrations"
        / "versions"
        / "20260830_0004_agent_runtime_source_fingerprint.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert "source_fingerprint" in source
    assert "DEFAULT 'unknown'" in source
    assert "DROP DEFAULT" in source


def test_agent_studio_cutover_migration_adds_lifecycle_and_reset_boundaries() -> None:
    migration = (
        service_root()
        / "migrations"
        / "versions"
        / "20260902_0005_agent_studio_cutover.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert "ade.agent_definitions" in source
    assert "agent_definition_id" in source
    assert "purpose" in source
    assert "archived_at" in source
    assert "state_generation" in source
    assert "ade.agent_studio_reset_receipts" in source


def test_run_runtime_mode_migration_binds_claims_to_acceptance_mode() -> None:
    migration = (
        service_root() / "migrations" / "versions" / "20260902_0006_run_runtime_mode.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert "accepted_runtime_mode" in source
    assert "'development', 'release'" in source


def test_alembic_version_table_is_owned_with_runtime_schema() -> None:
    config = alembic_config()
    assert config.get_main_option("version_table_schema") == "ade"
    assert config.get_main_option("owner_role") == "ade_owner"


def test_online_environment_owns_the_transaction_started_by_set_role() -> None:
    source = (service_root() / "migrations" / "env.py").read_text(encoding="utf-8")
    assert "with connectable.begin() as connection" in source
    assert "with connectable.connect() as connection" not in source
