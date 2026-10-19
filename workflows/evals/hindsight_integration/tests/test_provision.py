"""Candidate credentials are copied opaquely and never enter mounted evidence."""

import json
import os
from pathlib import Path

import pytest
from dotenv import dotenv_values

from workflows.evals.hindsight_integration.provision import prepare_environment
from workflows.evals.hindsight_integration.operations import Lease


def lease(root):
    value = Lease(
        "ade-hindsight-integration",
        "9292a50c-a607-45b4-89cb-7917c691e9b5",
        "a" * 40,
        1,
        3_601,
        7_201,
        "/mnt/projects",
        (),
    )
    value.save(root)


def test_existing_tokens_stay_in_separate_secret_files_and_are_not_printed(
    tmp_path, capsys
):
    root = tmp_path / "activation"
    lease(root)
    existing = tmp_path / "old.env"
    existing.write_text(
        'DEEPSEEK_API_KEY="private-token"\nDGX_EMBEDDING_API_KEY=embed-token\n'
    )
    environment = tmp_path / "credentials" / "candidate.env"
    result = prepare_environment(
        activation_root=root,
        environment_path=environment,
        existing_credentials=existing,
        database_image="sha256:" + "b" * 64,
        source_fingerprint="c" * 64,
    )
    values = dotenv_values(environment, interpolate=False)
    assert (
        Path(values["INTEGRATION_DEEPSEEK_SECRET_FILE"]).read_text() == "private-token"
    )
    assert (
        Path(values["INTEGRATION_EMBEDDING_SECRET_FILE"]).read_text() == "embed-token"
    )
    assert "private-token" not in environment.read_text()
    assert "private-token" not in json.dumps(result)
    assert "private-token" not in capsys.readouterr().out
    assert os.stat(environment).st_mode & 0o777 == 0o600
    assert not any(path.suffix == ".key" for path in root.rglob("*"))
    with pytest.raises(FileExistsError):
        prepare_environment(
            activation_root=root,
            environment_path=environment,
            existing_credentials=existing,
            database_image="sha256:" + "b" * 64,
            source_fingerprint="c" * 64,
        )


def test_credential_environment_cannot_be_written_into_the_mounted_activation(tmp_path):
    root = tmp_path / "activation"
    lease(root)
    with pytest.raises(ValueError, match="outside"):
        prepare_environment(
            activation_root=root,
            environment_path=root / "candidate.env",
            existing_credentials=tmp_path / "unread",
            database_image="sha256:" + "b" * 64,
            source_fingerprint="c" * 64,
        )
