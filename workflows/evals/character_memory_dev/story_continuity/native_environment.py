"""Owned disposable PostgreSQL and loopback services; never the retained trial."""

from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4

from dotenv import dotenv_values
import httpx

from .baseline import MANIFEST, SOURCES, validate_catalog
from .native_artifacts import check_preparation, read, write_once
from .schedule import ROOT

IMAGE = "pgvector/pgvector:0.8.1-pg15"
SERVICE = "workflows.evals.character_memory_dev.story_continuity.native_service"


def command(*args: str, env=None) -> str:
    result = subprocess.run(
        args, cwd=ROOT, env=env, check=True, capture_output=True, text=True, timeout=90
    )
    return result.stdout.strip()


def free_port() -> int:
    with socket.socket() as bound:
        bound.bind(("127.0.0.1", 0))
        return bound.getsockname()[1]


def owned_container(receipt: dict) -> dict:
    inspected = json.loads(command("docker", "inspect", receipt["container_id"]))[0]
    if (
        inspected["Id"] != receipt["container_id"]
        or inspected["Config"]["Labels"].get("ade.pc11.owner") != receipt["token"]
        or inspected["Config"]["Image"] != IMAGE
        or inspected["HostConfig"].get("Binds")
    ):
        raise ValueError("Container ownership/image/mount binding differs")
    return inspected


def bind_alias(directory: Path, host: str) -> None:
    path = directory / "network-binding.json"
    binding = {"dgx-spark": host}
    if path.exists():
        if read(path) != binding:
            raise ValueError(
                "Pinned Spark address changed after native environment freeze"
            )
    else:
        write_once(path, binding)


class NativeEnvironment:
    def __init__(self, directory: Path):
        self.directory = directory
        self.processes: list[subprocess.Popen] = []
        self.logs = []
        self.receipt = None
        self.api_key = secrets.token_hex(32)
        self.router_key = secrets.token_hex(32)
        self.api_port = free_port()
        self.router_port = free_port()
        while self.router_port == self.api_port:
            self.router_port = free_port()
        self.api_url = f"http://127.0.0.1:{self.api_port}"
        self.router_url = f"http://127.0.0.1:{self.router_port}"

    def __enter__(self):
        try:
            self.start()
            return self
        except BaseException:
            self.close()
            raise

    def __exit__(self, *_):
        self.close()

    def start(self) -> None:
        preparation = check_preparation(self.directory)
        configured = {**dotenv_values(ROOT / ".env"), **os.environ}
        if not configured.get("DEEPSEEK_API_KEY"):
            raise ValueError("Configured DeepSeek credential is required")
        host = str(ipaddress.IPv4Address(configured.get("DGX_SPARK_HOST", "")))
        if Path("/run/secrets").is_dir():
            raise ValueError(
                "Native local services must not inherit mounted settings overrides"
            )
        bind_alias(self.directory, host)
        previous = self.directory / "database.json"
        new_database = not previous.exists()
        if new_database:
            token = uuid4().hex
            database = f"ade_history_test_{token}"
            container_id = command(
                "docker",
                "create",
                "--name",
                f"ade-pc11-native-{token}",
                "--label",
                f"ade.pc11.owner={token}",
                "-e",
                "POSTGRES_USER=ade_owner",
                "-e",
                "POSTGRES_HOST_AUTH_METHOD=trust",
                "-e",
                f"POSTGRES_DB={database}",
                "-p",
                "127.0.0.1::5432",
                IMAGE,
            )
            self.receipt = {
                "token": token,
                "container_id": container_id,
                "database": database,
            }
            write_once(previous, self.receipt)
        else:
            self.receipt = read(previous)
        owned_container(self.receipt)
        command("docker", "start", self.receipt["container_id"])
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                command(
                    "docker",
                    "exec",
                    self.receipt["container_id"],
                    "pg_isready",
                    "-U",
                    "ade_owner",
                )
                break
            except subprocess.CalledProcessError:
                time.sleep(0.5)
        else:
            raise TimeoutError("Owned PostgreSQL did not start")
        inspected = owned_container(self.receipt)
        ports = inspected["NetworkSettings"]["Ports"]["5432/tcp"]
        if len(ports) != 1 or ports[0]["HostIp"] != "127.0.0.1":
            raise ValueError("Owned database must be exclusively loopback-bound")
        database_url = (
            f"postgresql+psycopg://ade_owner@127.0.0.1:{ports[0]['HostPort']}/"
            f"{self.receipt['database']}"
        )
        env = {str(k): str(v) for k, v in configured.items() if v is not None}
        env.update(
            ADE_REPOSITORY_ROOT=str(ROOT),
            ADE_SOURCE_REVISION=preparation["source_revision"],
            ADE_SOURCE_DIRTY="false",
            ADE_SOURCE_FINGERPRINT=preparation["governed_source_fingerprint_v2"],
            ADE_NATURAL_MEMORY_CAPTURE="1",
            ADE_API_AUTH_ENABLED="true",
            ADE_API_ADMIN_KEY=self.api_key,
            ADE_API_OPERATOR_KEY="",
            ADE_API_READER_KEY="",
            ADE_API_AGENT_RUNTIME_ENABLED="true",
            ADE_API_AGENT_RUNTIME_MODE="development",
            ADE_API_HISTORY_TRIAL_ENABLED="true",
            ADE_API_DATABASE_URL=database_url,
            ADE_API_MODEL_ROUTER_BASE_URL=self.router_url,
            ADE_API_MODEL_ROUTER_API_KEY_ENV="MODEL_ROUTER_API_KEY",
            ADE_API_MODEL_ROUTER_API_KEY_SECRET="",
            ADE_API_RUNTIME_DATA_DIR=str(self.directory / "runtime"),
            ADE_API_PERSONA_DB_PATH=str(self.directory / "personas.sqlite3"),
            ADE_API_PERSONA_SEED_JSONL_PATH=str(
                ROOT / "content/personas/personas.jsonl"
            ),
            ADE_API_AGENT_RUNTIME_WORKER_ID=f"pc11-{self.receipt['token']}",
            ADE_API_AGENT_RUNTIME_WORKER_POLL_SECONDS="0.5",
            ADE_API_AGENT_RUNTIME_LEASE_SECONDS="60",
            ADE_API_AGENT_RUNTIME_HEARTBEAT_SECONDS="15",
            ADE_API_AGENT_RUNTIME_WORKER_HEARTBEAT_SECONDS="5",
            ADE_API_AGENT_RUNTIME_WORKER_STALE_SECONDS="15",
            MODEL_ROUTER_API_KEY=self.router_key,
            MODEL_ROUTER_API_KEY_SECRET="",
            MODEL_ROUTER_SOURCES="[]",
            MODEL_ROUTER_SOURCES_FILE=str(SOURCES),
            MODEL_ROUTER_DEPLOYMENT_MANIFEST_FILE=str(MANIFEST),
            MODEL_ROUTER_MODEL_PROFILES_FILE=str(
                ROOT / "config/model-router/model-profiles.json"
            ),
            MODEL_ROUTER_REQUEST_TIMEOUT_SECONDS="600",
            MODEL_ROUTER_CACHE_TTL_SECONDS="30",
            MODEL_ROUTER_DISCOVERY_TIMEOUT_SECONDS="5",
            ADE_API_OPTIONS_CACHE_TTL_SECONDS="30",
            ADE_API_MODEL_DISCOVERY_TIMEOUT_SECONDS="5",
            DGX_SPARK_HOST=host,
        )
        for name in ("TEMPERATURE", "TOP_P", "TOP_K"):
            if env.get(f"ADE_API_AGENT_STUDIO_{name}", ""):
                raise ValueError(
                    "Native baseline must not override deployment sampling"
                )
        if new_database:
            command(
                "docker",
                "exec",
                self.receipt["container_id"],
                "psql",
                "-U",
                "ade_owner",
                "-d",
                self.receipt["database"],
                "-v",
                "ON_ERROR_STOP=1",
                "-c",
                "CREATE SCHEMA ade; CREATE EXTENSION vector;",
            )
            migration_env = {
                **env,
                "ADE_DATABASE_MIGRATION_URL": database_url,
                "ADE_PG_OWNER_ROLE": "ade_owner",
            }
            command(
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "services/ade-api/alembic.ini",
                "upgrade",
                "head",
                env=migration_env,
            )
        self.launch = self.directory / f"launch-{uuid4().hex}"
        self.launch.mkdir(mode=0o700)
        self.spawn("router", env, self.router_port)
        self.wait_http(f"{self.router_url}/v1/health", self.router_key)
        with httpx.Client(trust_env=False, timeout=30) as client:
            response = client.get(
                f"{self.router_url}/v1/router/model-catalog",
                headers={"Authorization": f"Bearer {self.router_key}"},
            )
            response.raise_for_status()
            catalog = response.json()
        write_once(self.launch / "catalog.json", catalog)
        roles = validate_catalog(catalog)
        self.spawn("worker", env)
        self.spawn("api", env, self.api_port)
        health = self.wait_http(f"{self.api_url}/api/v3/worker-health", self.api_key)
        if (
            not health["worker_ready"]
            or health["source_dirty"]
            or health["source_revision"] != preparation["source_revision"]
            or health["source_fingerprint"]
            != preparation["governed_source_fingerprint_v2"]
            or health["matching_build_worker_count"] != 1
        ):
            raise ValueError("Native worker does not match the frozen isolated source")
        write_once(self.launch / "worker-health.json", health)
        write_once(
            self.launch / "environment.json",
            {
                "database": self.receipt,
                "database_url": database_url,
                "api_url": self.api_url,
                "router_url": self.router_url,
                "spark_alias": {"dgx-spark": host},
                "roles": roles,
                "settings": {
                    k: v
                    for k, v in env.items()
                    if k
                    in {
                        "ADE_SOURCE_REVISION",
                        "ADE_SOURCE_DIRTY",
                        "ADE_SOURCE_FINGERPRINT",
                        "ADE_NATURAL_MEMORY_CAPTURE",
                        "ADE_API_AGENT_RUNTIME_MODE",
                        "ADE_API_HISTORY_TRIAL_ENABLED",
                        "ADE_API_PERSONA_DB_PATH",
                        "MODEL_ROUTER_SOURCES_FILE",
                        "MODEL_ROUTER_DEPLOYMENT_MANIFEST_FILE",
                        "MODEL_ROUTER_MODEL_PROFILES_FILE",
                        "MODEL_ROUTER_REQUEST_TIMEOUT_SECONDS",
                    }
                },
            },
        )

    def spawn(self, service: str, env: dict, port: int | None = None) -> None:
        stream = (self.launch / f"{service}.log").open("x")
        self.logs.append(stream)
        args = [sys.executable, "-m", SERVICE, service]
        if port:
            args.extend(["--port", str(port)])
        self.processes.append(
            subprocess.Popen(
                args, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT
            )
        )

    def wait_http(self, url: str, token: str) -> dict:
        deadline = time.monotonic() + 60
        with httpx.Client(
            trust_env=False, timeout=3, headers={"Authorization": f"Bearer {token}"}
        ) as client:
            while time.monotonic() < deadline:
                if any(process.poll() is not None for process in self.processes):
                    raise RuntimeError(
                        "Owned service exited; inspect its private launch log"
                    )
                try:
                    response = client.get(url)
                    if response.is_success:
                        return response.json()
                except httpx.TransportError:
                    pass
                time.sleep(0.5)
        raise TimeoutError("Owned service readiness deadline")

    def close(self) -> None:
        for process in reversed(self.processes):
            if process.poll() is None:
                process.terminate()
        for process in reversed(self.processes):
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for stream in self.logs:
            stream.close()
        if self.receipt is not None:
            owned_container(self.receipt)
            command("docker", "stop", "-t", "10", self.receipt["container_id"])


def remove_owned_database(directory: Path) -> None:
    receipt = read(directory / "database.json")
    inspected = owned_container(receipt)
    if inspected["State"]["Running"]:
        raise ValueError("Stop this probe's services/database before removing it")
    command("docker", "rm", "-v", receipt["container_id"])
    write_once(directory / "database-removed.json", receipt)
