from __future__ import annotations

import os
import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from ade_api.features.agent_runtime_v3.persistence.metadata import METADATA


config = context.config

migration_url = os.getenv("ADE_DATABASE_MIGRATION_URL", "").strip()
if migration_url:
    config.set_main_option("sqlalchemy.url", migration_url)
owner_role_override = os.getenv("ADE_PG_OWNER_ROLE", "").strip()
if owner_role_override:
    config.set_main_option("owner_role", owner_role_override)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = METADATA


def _migration_options() -> dict[str, object]:
    return {
        "target_metadata": target_metadata,
        "include_schemas": True,
        "version_table": config.get_main_option("version_table"),
        "version_table_schema": config.get_main_option("version_table_schema"),
    }


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_migration_options(),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # SET ROLE starts SQLAlchemy's implicit transaction. Own that transaction here
    # so the migration and version row commit instead of rolling back on close.
    with connectable.begin() as connection:
        owner_role = config.get_main_option("owner_role")
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,62}", owner_role):
            raise RuntimeError("Alembic owner_role must be a safe lowercase identifier")
        connection.execute(text(f'SET ROLE "{owner_role}"'))
        connection.execute(text("SET search_path TO ade, extensions, public"))
        context.configure(
            connection=connection,
            **_migration_options(),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
