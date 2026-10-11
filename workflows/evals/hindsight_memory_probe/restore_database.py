"""Exact disposable PostgreSQL Compose configuration and Docker identity checks."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from . import host_guard, restart_selection

RESTORE_MEMORY = host_guard.GIB
RESTORE_CPU = 0.25
DATA_PATH = "/var/lib/postgresql/data"
COMMAND_RUNNER = None
TEXT_RUNNER = None


def sha256_file(path: Path) -> str:
    return restart_selection.sha256_file(path)


def project_for(token: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        raise RuntimeError("restore_token_invalid")
    return "ade-hindsight-restore-" + token[:16]


def volume_for(project: str) -> str:
    if not re.fullmatch(r"ade-hindsight-restore-[0-9a-f]{16}", project):
        raise RuntimeError("restore_project_invalid")
    return project + "_data"


def write_compose(directory: Path, token: str, source_image: str, image_id: str) -> dict:
    project = project_for(token)
    volume = volume_for(project)
    if (not isinstance(source_image, str) or not source_image
            or any(character in source_image for character in "\n\r\0 '")):
        raise RuntimeError("restore_source_image_invalid")
    if not isinstance(image_id, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise RuntimeError("restore_source_image_id_invalid")
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(directory, 0o700)
    config = directory / "compose.yaml"
    # This one-service file has no network, ports, bind mounts, env_file, build, or dependency.
    content = (
        f"name: {project}\n"
        "services:\n"
        "  db:\n"
        f"    image: {source_image}\n"
        "    platform: linux/arm64\n"
        "    restart: \"no\"\n"
        f"    mem_limit: {RESTORE_MEMORY}\n"
        f"    cpus: {RESTORE_CPU}\n"
        "    network_mode: none\n"
        "    environment:\n"
        "      POSTGRES_DB: hindsight_probe\n"
        "      POSTGRES_USER: hindsight_probe\n"
        f"      POSTGRES_PASSWORD: restore-{token}\n"
        "    labels:\n"
        f'      ade.hindsight.restore.token: "{token}"\n'
        "    volumes:\n"
        f"      - data:{DATA_PATH}\n"
        "volumes:\n"
        "  data:\n"
        f"    name: {volume}\n"
        "    labels:\n"
        f'      ade.hindsight.restore.token: "{token}"\n'
    )
    descriptor = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(config), "sha256": sha256_file(config), "project": project,
            "volume": volume, "source_image": source_image, "source_image_id": image_id}


def verify_compose(operation: dict) -> None:
    config = Path(operation["compose"]["path"])
    if (config.is_symlink() or not config.is_file()
            or sha256_file(config) != operation["compose"]["sha256"]):
        raise RuntimeError("restore_compose_config_changed")
    text = config.read_text(encoding="utf-8")
    expected = write_contract(operation)
    if text != expected:
        raise RuntimeError("restore_compose_config_contract_changed")


def write_contract(operation: dict) -> str:
    compose = operation["compose"]
    token, project, volume = operation["token"], compose["project"], compose["volume"]
    return (
        f"name: {project}\nservices:\n  db:\n"
        f"    image: {compose['source_image']}\n    platform: linux/arm64\n"
        "    restart: \"no\"\n"
        f"    mem_limit: {RESTORE_MEMORY}\n    cpus: {RESTORE_CPU}\n"
        "    network_mode: none\n    environment:\n"
        "      POSTGRES_DB: hindsight_probe\n      POSTGRES_USER: hindsight_probe\n"
        f"      POSTGRES_PASSWORD: restore-{token}\n    labels:\n"
        f'      ade.hindsight.restore.token: "{token}"\n    volumes:\n'
        f"      - data:{DATA_PATH}\nvolumes:\n  data:\n"
        f"    name: {volume}\n"
        "    labels:\n"
        f'      ade.hindsight.restore.token: "{token}"\n'
    )


def docker_json(arguments: list[str], timeout: int = 10):
    if COMMAND_RUNNER is not None:
        return COMMAND_RUNNER(arguments, timeout)
    result = subprocess.run(arguments, check=True, capture_output=True, timeout=timeout)
    return json.loads(result.stdout)


def docker_text(arguments: list[str], timeout: int = 10) -> list[str]:
    if TEXT_RUNNER is not None:
        return TEXT_RUNNER(arguments, timeout)
    result = subprocess.run(arguments, check=True, capture_output=True, timeout=timeout)
    return result.stdout.decode().splitlines()


def source_container(directory: Path, operation: dict) -> dict:
    matches = [row for row in operation["finalization"]["containers"] if row["service"] == "db"]
    if len(matches) != 1:
        raise RuntimeError("restore_source_database_identity_ambiguous")
    source = matches[0]
    # Never infer source ownership from a prefix; this must remain the exact main release row.
    release_dir = Path(operation["release_path"]) / "workflows/evals/hindsight_memory_probe"
    current = docker_json(["docker", "inspect", source["id"]])[0]
    labels = current.get("Config", {}).get("Labels") or {}
    if (current.get("Id") != source["id"] or current.get("Image") != source["image_id"]
            or current.get("State", {}).get("Status") != "exited"
            or current.get("State", {}).get("StartedAt") != source.get("started_at")
            or labels.get("com.docker.compose.project") != host_guard.PROJECT
            or labels.get("com.docker.compose.service") != "db"
            or labels.get("com.docker.compose.project.working_dir") != str(release_dir)
            or labels.get("com.docker.compose.project.config_files") != str(release_dir / "compose.yaml")):
        raise RuntimeError("restore_source_database_identity_changed")
    image = docker_json(["docker", "image", "inspect", current["Config"]["Image"]])[0]
    if image.get("Id") != source["image_id"]:
        raise RuntimeError("restore_source_database_image_changed")
    return current


def restore_container(operation: dict, *, allow_unregistered: bool = False,
                      inventory: list[dict] | None = None) -> dict | None:
    if inventory is None:
        containers = docker_text(["docker", "ps", "-aq", "--no-trunc"])
        if not containers:
            return None
        values = docker_json(["docker", "inspect", *containers])
    else:
        # Host ownership checks classify the same Docker snapshot they compare.
        # A create between reads can place the token/project in only one set;
        # unknown rows in the shared snapshot remain fatal.
        values = inventory
    token, project = operation["token"], operation["compose"]["project"]
    found = []
    for row in values:
        labels = row.get("Config", {}).get("Labels") or {}
        if labels.get("ade.hindsight.restore.token") == token or labels.get("com.docker.compose.project") == project:
            found.append(row)
    if len(found) != 1:
        if found:
            raise RuntimeError("restore_container_identity_ambiguous")
        return None
    row = found[0]
    labels = row.get("Config", {}).get("Labels") or {}
    expected_config = operation["compose"]["path"]
    mount_rows = [mount for mount in row.get("Mounts", []) if mount.get("Destination") == DATA_PATH]
    create_path = Path(operation["state_directory"]) / f"restore-{token}-create.result.json"
    created = None
    if create_path.is_file():
        created = json.loads(create_path.read_text())
    elif not allow_unregistered:
        raise RuntimeError("restore_container_not_registered")
    if (labels.get("ade.hindsight.restore.token") != token
            or labels.get("com.docker.compose.project") != project
            or labels.get("com.docker.compose.service") != "db"
            or labels.get("com.docker.compose.project.config_files") != expected_config
            or labels.get("com.docker.compose.project.working_dir") != str(Path(expected_config).parent)
            or row.get("Image") != operation["compose"]["source_image_id"]
            or row.get("Config", {}).get("Image") != operation["compose"]["source_image"]
            or row.get("HostConfig", {}).get("NetworkMode") != "none"
            or row.get("HostConfig", {}).get("Memory") != RESTORE_MEMORY
            or abs(float(row.get("HostConfig", {}).get("NanoCpus", 0)) / 1_000_000_000 - RESTORE_CPU) > 1e-6
            or row.get("NetworkSettings", {}).get("Ports") not in ({}, None)
            or len(mount_rows) != 1 or mount_rows[0].get("Name") != operation["compose"]["volume"]
            or mount_rows[0].get("RW") is not True
            or set(mount.get("Destination") for mount in row.get("Mounts", [])) != {DATA_PATH}
            or (created is not None and (row.get("Id") != created.get("container_id")
                or row.get("State", {}).get("StartedAt") != created.get("started_at")))):
        raise RuntimeError("restore_container_identity_changed")
    env = row.get("Config", {}).get("Env") or []
    if any(item.split("=", 1)[0].startswith(("HINDSIGHT", "OPENAI", "DEEPSEEK", "DGX_", "MODEL_ROUTER", "ADE_EVAL"))
           for item in env):
        raise RuntimeError("restore_provider_environment_detected")
    return row


def verify_volume(operation: dict, *, allow_unregistered: bool = False) -> dict | None:
    volumes = docker_text(["docker", "volume", "ls", "-q", "--filter",
                           "name=" + operation["compose"]["volume"]])
    matches = [name for name in volumes if name == operation["compose"]["volume"]]
    if not matches:
        return None
    if len(matches) != 1:
        raise RuntimeError("restore_volume_identity_ambiguous")
    value = docker_json(["docker", "volume", "inspect", matches[0]])[0]
    labels = value.get("Labels") or {}
    if (value.get("Name") != operation["compose"]["volume"]
            or labels.get("com.docker.compose.project") != operation["compose"]["project"]
            or labels.get("com.docker.compose.volume") != "data"
            or labels.get("ade.hindsight.restore.token") != operation["token"]
            or value.get("Driver") != "local" or value.get("Scope") != "local"
            or value.get("Options") not in ({}, None)):
        raise RuntimeError("restore_volume_identity_changed")
    create_path = Path(operation["state_directory"]) / f"restore-{operation['token']}-create.result.json"
    if create_path.is_file():
        created = json.loads(create_path.read_text())
        expected = created.get("volume_identity", {})
        if any(value.get(key) != expected.get(key) for key in ("Name", "Driver", "Scope", "Mountpoint", "CreatedAt")):
            raise RuntimeError("restore_volume_identity_changed")
    elif not allow_unregistered:
        raise RuntimeError("restore_volume_not_registered")
    return value
