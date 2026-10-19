"""A workflow migration command cannot target an incumbent database or role."""

import pytest

from .. import product_database


def environment():
    return {
        "ADE_PG_DB": "ade_integration",
        "ADE_PG_OWNER_ROLE": "ade_integration_owner",
        "ADE_PG_APP_USER": "ade_integration_app",
        "ADE_PG_APP_PASSWORD": "synthetic",
        "ADE_DATABASE_ADMIN_URL": "postgresql://ade_integration_admin:synthetic@ade-db:5432/postgres",
        "ADE_DATABASE_MIGRATION_URL": "postgresql+psycopg://ade_integration_admin:synthetic@ade-db:5432/ade_integration",
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("ADE_PG_DB", "ade"),
        ("ADE_PG_OWNER_ROLE", "ade_integration_admin"),
        ("ADE_PG_APP_USER", "ade_integration_owner"),
        (
            "ADE_DATABASE_ADMIN_URL",
            "postgresql://admin:synthetic@postgres_shared:5432/postgres",
        ),
        (
            "ADE_DATABASE_MIGRATION_URL",
            "postgresql+psycopg://ade_integration_admin:synthetic@ade-db:5432/ade",
        ),
        ("ADE_PG_APP_PASSWORD", ""),
    ],
)
def test_only_fixed_owned_candidate_database_and_distinct_roles_are_allowed(key, value):
    values = environment()
    product_database.validate_environment(values)
    values[key] = value
    with pytest.raises(ValueError):
        product_database.validate_environment(values)


def test_candidate_bootstrap_precedes_public_alembic_cli_without_secret_arguments(
    monkeypatch,
):
    for key, value in environment().items():
        monkeypatch.setenv(key, value)
    calls = []
    monkeypatch.setattr(
        product_database.subprocess, "run", lambda command, **kw: calls.append(command)
    )
    product_database.main()
    assert calls == [
        ["python", "-m", "ade_api.features.agent_runtime.bootstrap"],
        ["alembic", "-c", "services/ade-api/alembic.ini", "upgrade", "head"],
    ]
    assert "synthetic" not in str(calls)
