"""Guarded invocation of ADE's public bootstrap/migration CLIs for the candidate."""

import os
import subprocess
from urllib.parse import urlsplit


def validate_environment(environment) -> None:
    expected = {
        "ADE_PG_DB": "ade_integration",
        "ADE_PG_OWNER_ROLE": "ade_integration_owner",
        "ADE_PG_APP_USER": "ade_integration_app",
    }
    if any(environment.get(key) != value for key, value in expected.items()):
        raise ValueError("Candidate database/role identity mismatch")
    for key, scheme, database in (
        ("ADE_DATABASE_ADMIN_URL", "postgresql", "postgres"),
        ("ADE_DATABASE_MIGRATION_URL", "postgresql+psycopg", "ade_integration"),
    ):
        url = urlsplit(environment.get(key, ""))
        if (
            url.scheme != scheme
            or url.hostname != "ade-db"
            or url.port != 5432
            or url.username != "ade_integration_admin"
            or not url.password
            or url.path != f"/{database}"
            or url.query
            or url.fragment
        ):
            raise ValueError("Only the isolated candidate ADE database is allowed")
    if not environment.get("ADE_PG_APP_PASSWORD"):
        raise ValueError("Candidate application credential is required")


def main() -> None:
    validate_environment(os.environ)
    subprocess.run(
        ["python", "-m", "ade_api.features.agent_runtime.bootstrap"],
        check=True,
        timeout=60,
    )
    subprocess.run(
        ["alembic", "-c", "services/ade-api/alembic.ini", "upgrade", "head"],
        check=True,
        timeout=120,
    )
    print("Candidate ADE database bootstrapped and migrated")


if __name__ == "__main__":
    main()
