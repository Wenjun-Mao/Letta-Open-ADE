from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass

import psycopg
from psycopg import sql


_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")


@dataclass(frozen=True)
class BootstrapConfig:
    admin_url: str
    database_name: str = "ade"
    owner_role: str = "ade_owner"
    app_role: str = "ade_app"
    app_password: str = ""

    def validate(self) -> None:
        if not self.admin_url.strip():
            raise ValueError("ADE_DATABASE_ADMIN_URL is required")
        for label, value in (
            ("database_name", self.database_name),
            ("owner_role", self.owner_role),
            ("app_role", self.app_role),
        ):
            if not _IDENTIFIER_RE.fullmatch(value):
                raise ValueError(f"{label} must be a safe lowercase SQL identifier")
        if not self.app_password:
            raise ValueError("ADE_PG_APP_PASSWORD is required")
        if self.owner_role == self.app_role:
            raise ValueError("owner and application roles must be different")


def bootstrap(config: BootstrapConfig) -> None:
    config.validate()
    with psycopg.connect(config.admin_url, autocommit=True) as connection:
        _ensure_roles(connection, config)
        _ensure_database(connection, config)
    database_url = _replace_database(config.admin_url, config.database_name)
    with psycopg.connect(database_url, autocommit=True) as connection:
        _ensure_schemas_and_grants(connection, config)


def _ensure_roles(connection: psycopg.Connection, config: BootstrapConfig) -> None:
    with connection.cursor() as cursor:
        if not _role_exists(cursor, config.owner_role):
            cursor.execute(
                sql.SQL("CREATE ROLE {} NOLOGIN").format(
                    sql.Identifier(config.owner_role)
                )
            )
        else:
            cursor.execute(
                sql.SQL("ALTER ROLE {} NOLOGIN").format(
                    sql.Identifier(config.owner_role)
                )
            )
        if not _role_exists(cursor, config.app_role):
            cursor.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(config.app_role), sql.Literal(config.app_password)
                )
            )
        else:
            cursor.execute(
                sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(config.app_role), sql.Literal(config.app_password)
                )
            )


def _role_exists(cursor: psycopg.Cursor, role: str) -> bool:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
    return cursor.fetchone() is not None


def _ensure_database(connection: psycopg.Connection, config: BootstrapConfig) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (config.database_name,)
        )
        if cursor.fetchone() is None:
            cursor.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(config.database_name),
                    sql.Identifier(config.owner_role),
                )
            )
        else:
            cursor.execute(
                sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                    sql.Identifier(config.database_name),
                    sql.Identifier(config.owner_role),
                )
            )


def _ensure_schemas_and_grants(
    connection: psycopg.Connection, config: BootstrapConfig
) -> None:
    owner = sql.Identifier(config.owner_role)
    app = sql.Identifier(config.app_role)
    database = sql.Identifier(config.database_name)
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS extensions AUTHORIZATION {};").format(
                owner
            )
        )
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;")
        cursor.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS ade AUTHORIZATION {};").format(owner)
        )
        cursor.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO {};").format(database, app)
        )
        cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC;")
        cursor.execute(
            sql.SQL("GRANT USAGE ON SCHEMA ade, extensions TO {};").format(app)
        )
        cursor.execute(
            sql.SQL(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ade TO {};"
            ).format(app)
        )
        cursor.execute(
            sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ade TO {};").format(
                app
            )
        )
        cursor.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA ade "
                "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {};"
            ).format(owner, app)
        )
        cursor.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA ade "
                "GRANT USAGE, SELECT ON SEQUENCES TO {};"
            ).format(owner, app)
        )
        cursor.execute(
            sql.SQL(
                "ALTER ROLE {} IN DATABASE {} SET search_path TO ade, extensions;"
            ).format(app, database)
        )
        cursor.execute(
            sql.SQL(
                "ALTER ROLE {} IN DATABASE {} SET search_path TO ade, extensions, public;"
            ).format(owner, database)
        )


def _replace_database(url: str, database_name: str) -> str:
    connection_info = psycopg.conninfo.conninfo_to_dict(url)
    connection_info["dbname"] = database_name
    return psycopg.conninfo.make_conninfo(**connection_info)


def config_from_env() -> BootstrapConfig:
    return BootstrapConfig(
        admin_url=os.getenv("ADE_DATABASE_ADMIN_URL", ""),
        database_name=os.getenv("ADE_PG_DB", "ade"),
        owner_role=os.getenv("ADE_PG_OWNER_ROLE", "ade_owner"),
        app_role=os.getenv("ADE_PG_APP_USER", "ade_app"),
        app_password=os.getenv("ADE_PG_APP_PASSWORD", ""),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the ADE-owned database")
    parser.parse_args()
    bootstrap(config_from_env())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
