"""HTTP version-contract assertions for the disposable scripted sequence."""

from uuid import uuid4

import pytest
from sqlalchemy import insert, select

from ade_api.features.agent_runtime.database_boundary import DEFAULT_WORKSPACE_ID
from ade_api.features.agent_runtime.persistence.definitions import (
    DefinitionVersionRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definitions,
    agent_definition_versions,
    workspaces,
)


async def create_checked_version(api, engine, primary, request):
    original = primary["agent_definition"]
    root_id = original["agent_definition_id"]
    async with engine.connect() as connection:
        before = (
            (
                await connection.execute(
                    select(agent_definition_versions).where(
                        agent_definition_versions.c.id == original["id"]
                    )
                )
            )
            .mappings()
            .one()
        )

    for expected in (None, 0):
        with pytest.raises(ValueError, match="422"):
            await api.create_version(
                root_id, {**request, "expected_current_version": expected}
            )
    for field, value in (
        ("definition_key", "wrong_key"),
        ("prompt_key", "chat_v20260516"),
    ):
        with pytest.raises(ValueError, match="422"):
            await api.create_version(root_id, {**request, field: value})

    # Synthetic inaccessible roots test HTTP ownership without changing real sessions.
    for purpose, foreign_workspace in (
        ("agent_studio", False),
        ("development", False),
        ("evaluation", True),
    ):
        foreign_root = str(uuid4())
        workspace_id = str(uuid4()) if foreign_workspace else DEFAULT_WORKSPACE_ID
        key = f"inaccessible_{uuid4().hex}"
        async with engine.begin() as connection:
            if foreign_workspace:
                await connection.execute(
                    insert(workspaces).values(
                        id=workspace_id,
                        workspace_key=key,
                        name="isolated ownership fixture",
                    )
                )
            await connection.execute(
                insert(agent_definitions).values(
                    id=foreign_root,
                    workspace_id=workspace_id,
                    definition_key=key,
                    name="inaccessible",
                    purpose=purpose,
                )
            )
        with pytest.raises(ValueError, match="404"):
            await api.create_version(foreign_root, {**request, "definition_key": key})
        async with engine.connect() as connection:
            assert not (
                await connection.execute(
                    select(agent_definition_versions.c.id).where(
                        agent_definition_versions.c.agent_definition_id == foreign_root
                    )
                )
            ).all()

    for field, value in (
        ("persona_key", "unrelated_character"),
        ("memory_policy_version", "typed-user-facts-v2"),
    ):
        # Only negative fixtures use persistence: never provision the trial's next version.
        key = f"unrelated_{uuid4().hex}"
        payload = {
            k: v
            for k, v in before.items()
            if k
            not in {
                "workspace_id",
                "agent_definition_id",
                "purpose",
                "version",
                "created_at",
            }
        }
        payload.update(id=str(uuid4()), definition_key=key, **{field: value})
        async with engine.begin() as connection:
            unrelated = await DefinitionVersionRepository(connection).create_next(
                DEFAULT_WORKSPACE_ID,
                payload,
                purpose="evaluation",
                expected_current_version=0,
            )
        with pytest.raises(ValueError, match="422"):
            await api.create_version(
                str(unrelated["agent_definition_id"]),
                {**request, "definition_key": key},
            )
        async with engine.connect() as connection:
            persisted = (
                (
                    await connection.execute(
                        select(agent_definition_versions).where(
                            agent_definition_versions.c.agent_definition_id
                            == unrelated["agent_definition_id"]
                        )
                    )
                )
                .mappings()
                .all()
            )
            assert len(persisted) == 1
            assert dict(persisted[0]) == unrelated
            current_id = await connection.scalar(
                select(agent_definitions.c.current_version_id).where(
                    agent_definitions.c.id == unrelated["agent_definition_id"]
                )
            )
            assert current_id == unrelated["id"]

    version = await api.create_version(root_id, request)
    with pytest.raises(ValueError, match="409"):
        await api.create_version(root_id, request)
    async with engine.connect() as connection:
        after = (
            (
                await connection.execute(
                    select(agent_definition_versions).where(
                        agent_definition_versions.c.id == original["id"]
                    )
                )
            )
            .mappings()
            .one()
        )
        assert dict(after) == dict(before)
        rows = (
            (
                await connection.execute(
                    select(agent_definition_versions)
                    .where(agent_definition_versions.c.agent_definition_id == root_id)
                    .order_by(agent_definition_versions.c.version)
                )
            )
            .mappings()
            .all()
        )
        assert [row["version"] for row in rows] == [1, 2]
        assert all(row["purpose"] == "evaluation" for row in rows)
        assert all(str(row["workspace_id"]) == DEFAULT_WORKSPACE_ID for row in rows)
    retained = await api.request(
        "GET", f"/api/v3/history-trial/sessions/{primary['conversation']['id']}"
    )
    assert retained["agent_definition"] == original
    assert version["agent_definition_id"] == root_id
    assert version["id"] != original["id"]
    assert version["version"] == 2
    return version
