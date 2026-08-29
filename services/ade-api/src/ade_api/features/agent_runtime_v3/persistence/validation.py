"""Static and database checks for the reviewed Alembic migration chain."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection, make_url

from .metadata import METADATA, SCHEMA_NAME


def service_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "alembic.ini").is_file():
            return parent
    raise RuntimeError("unable to locate ADE API Alembic configuration")


def alembic_config(database_url: str | None = None) -> Config:
    root = service_root()
    config = Config(str(root / "alembic.ini"))
    if database_url is not None:
        url = make_url(database_url)
        if url.drivername in {"postgresql", "postgres"}:
            url = url.set(drivername="postgresql+psycopg")
        config.set_main_option(
            "sqlalchemy.url", url.render_as_string(hide_password=False)
        )
    return config


def migration_heads() -> tuple[str, ...]:
    script = ScriptDirectory.from_config(alembic_config())
    return tuple(sorted(script.get_heads()))


def validate_metadata_contract() -> None:
    """Fail fast if a new table, index, or constraint loses durable naming."""

    if {table.schema for table in METADATA.tables.values()} != {SCHEMA_NAME}:
        raise AssertionError("all persistence tables must live in the ade schema")
    for table in METADATA.tables.values():
        for constraint in table.constraints:
            if constraint.name is None:
                raise AssertionError(f"unnamed constraint on {table.name}")
        for index in table.indexes:
            if index.name is None:
                raise AssertionError(f"unnamed index on {table.name}")


def validate_database_at_head(connection: Connection) -> None:
    heads = set(migration_heads())
    config = alembic_config()
    current = set(
        MigrationContext.configure(
            connection,
            opts={
                "version_table": config.get_main_option("version_table"),
                "version_table_schema": config.get_main_option("version_table_schema"),
            },
        ).get_current_heads()
    )
    if current != heads:
        raise AssertionError(
            f"database migration heads {sorted(current)} do not match {sorted(heads)}"
        )
