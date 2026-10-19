"""Create private candidate credentials/configuration without printing their values."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex

from .operations import Lease, create_record


def read_existing_credentials(path: Path) -> dict[str, str]:
    values = {}
    selected = {"DEEPSEEK_API_KEY", "DGX_EMBEDDING_API_KEY"}
    for line in path.read_text().splitlines():
        line = line.strip().removeprefix("export ")
        key, separator, _ = line.partition("=")
        if not separator or key not in selected:
            continue
        tokens = shlex.split(line, comments=True)
        if len(tokens) != 1 or "=" not in tokens[0]:
            raise ValueError("Existing credential syntax requires explicit parsing")
        parsed_key, value = tokens[0].split("=", 1)
        values[parsed_key] = value
    if not values.get("DEEPSEEK_API_KEY"):
        raise ValueError("Existing DeepSeek credential is unavailable")
    return values


def _private_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as output:
        output.write(value)
        output.flush()
        os.fsync(output.fileno())


def prepare_environment(
    *,
    activation_root: Path,
    environment_path: Path,
    existing_credentials: Path,
    database_image: str,
) -> dict:
    activation_root = activation_root.resolve()
    environment_path = environment_path.resolve()
    if environment_path.is_relative_to(activation_root):
        raise ValueError(
            "Credentials must stay outside the mounted activation directory"
        )
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", database_image):
        raise ValueError("Native database must bind an inspected immutable image ID")
    lease = Lease.load(activation_root)
    credentials = read_existing_credentials(existing_credentials)
    secrets_root = environment_path.parent / lease.activation_id
    deepseek_path = secrets_root / "deepseek.key"
    embedding_path = secrets_root / "embedding.key"
    _private_text(deepseek_path, credentials["DEEPSEEK_API_KEY"])
    _private_text(embedding_path, credentials.get("DGX_EMBEDDING_API_KEY", ""))
    # Non-root candidate tools share only the operator's private artifact directories.
    for name in ("observations", "evidence"):
        (activation_root / name).mkdir(mode=0o700, exist_ok=False)
    environment = {
        "INTEGRATION_PROJECT": lease.project,
        "INTEGRATION_ACTIVATION_ID": lease.activation_id,
        "INTEGRATION_SOURCE_REVISION": lease.source_revision,
        "INTEGRATION_ACTIVATION_ROOT": str(activation_root),
        "INTEGRATION_OBSERVATION_ROOT": str(activation_root / "observations"),
        "INTEGRATION_EVIDENCE_ROOT": str(activation_root / "evidence"),
        "INTEGRATION_NATIVE_DB_IMAGE": database_image,
        "INTEGRATION_DB_PASSWORD": secrets.token_urlsafe(36),
        "INTEGRATION_ROUTER_KEY": secrets.token_urlsafe(36),
        "INTEGRATION_HINDSIGHT_KEY": secrets.token_urlsafe(36),
        "INTEGRATION_CP_KEY": secrets.token_urlsafe(36),
        "INTEGRATION_DEEPSEEK_SECRET_FILE": str(deepseek_path),
        "INTEGRATION_EMBEDDING_SECRET_FILE": str(embedding_path),
        "INTEGRATION_UID": str(os.getuid()),
        "INTEGRATION_GID": str(os.getgid()),
    }
    _private_text(
        environment_path,
        "".join(f"{key}={json.dumps(value)}\n" for key, value in environment.items()),
    )
    create_record(
        activation_root / "provisioned.json",
        {
            "activation_id": lease.activation_id,
            "environment_path": str(environment_path),
            "environment_sha256": hashlib.sha256(
                environment_path.read_bytes()
            ).hexdigest(),
        },
    )
    return {
        "activation_id": lease.activation_id,
        "environment_file": str(environment_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation-root", type=Path, required=True)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--existing-credentials", type=Path, required=True)
    parser.add_argument("--database-image", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            prepare_environment(
                activation_root=args.activation_root,
                environment_path=args.environment,
                existing_credentials=args.existing_credentials,
                database_image=args.database_image,
            )
        )
    )


if __name__ == "__main__":
    main()
