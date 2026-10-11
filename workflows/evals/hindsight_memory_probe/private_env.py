"""P1 only: create scoped private env interactively; never source the native .env."""

import argparse
import getpass
import os
import re
import secrets
from pathlib import Path

from .releases import PARENT
from .qualification_gate import require_oci_proof


def create(directory, sha, dummy_provider=False):
    if directory.resolve() != PARENT.parent / "private" or not re.fullmatch(
        "[a-f0-9]{40}", sha
    ):
        raise RuntimeError("owned_private_path_and_sha_required")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_mode & 0o077 or directory.is_symlink():
        raise RuntimeError("private_directory_permissions")
    (directory / "receipts").mkdir(mode=0o700, exist_ok=True)
    if not dummy_provider:
        require_oci_proof(directory)
    provider_key = (
        "synthetic-provider"
        if dummy_provider
        else getpass.getpass("Existing DeepSeek API key (private input): ").strip()
    )
    if not re.fullmatch("[A-Za-z0-9_.-]+", provider_key):
        raise RuntimeError("valid_existing_deepseek_key_required")
    values = {
        "PROBE_RELEASE_SHA": sha,
        "PROBE_PRIVATE_DIR": str(directory),
        "PROBE_UID": str(os.getuid()),
        "PROBE_GID": str(os.getgid()),
        "PROBE_DB_PASSWORD": secrets.token_hex(32),
        "PROBE_HINDSIGHT_KEY": secrets.token_hex(32),
        "PROBE_CP_ACCESS_KEY": secrets.token_hex(32),
        "PROBE_ROUTER_KEY": secrets.token_hex(32),
        "DEEPSEEK_API_KEY": provider_key,
        "DGX_EMBEDDING_API_KEY": "",
    }
    descriptor = os.open(
        directory / "secrets.env",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w") as stream:
        stream.write("".join(f"{key}={value}\n" for key, value in values.items()))
        stream.flush()
        os.fsync(stream.fileno())
    # No value echoes; duplication refuses to overwrite retained credentials.
    print("private_env_created")


def activate(directory):
    if directory.resolve() != PARENT.parent / "private":
        raise RuntimeError("owned_private_directory_required")
    path = directory / "secrets.env"
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise RuntimeError("private_env_permissions")
    require_oci_proof(directory)
    lines = path.read_text().splitlines()
    if "DEEPSEEK_API_KEY=synthetic-provider" not in lines:
        raise RuntimeError("provider_already_activated_or_conflicting")
    key = getpass.getpass("Existing DeepSeek API key (private input): ").strip()
    if not re.fullmatch("[A-Za-z0-9_.-]+", key):
        raise RuntimeError("valid_existing_deepseek_key_required")
    descriptor = os.open(
        directory / ".secrets.tmp",
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w") as stream:
        stream.write(
            "\n".join(
                "DEEPSEEK_API_KEY=" + key
                if line.startswith("DEEPSEEK_API_KEY=")
                else line
                for line in lines
            )
            + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(directory / ".secrets.tmp", path)
    print("private_provider_activated")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--release-sha")
    parser.add_argument("--activate-provider", action="store_true")
    parser.add_argument("--dummy-provider", action="store_true")
    args = parser.parse_args()
    if args.activate_provider:
        activate(args.private_dir)
    else:
        create(args.private_dir, args.release_sha, args.dummy_provider)
