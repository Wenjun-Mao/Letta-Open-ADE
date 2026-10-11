"""Fail closed on isolation/auth/resource drift in resolved Compose. Prints no secrets."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

PROJECT = "ade-hindsight-probe"
ROOT = Path(__file__).resolve().parent
HINDSIGHT_IMAGE = "ghcr.io/vectorize-io/hindsight:0.10.3@sha256:acf5e76bd9a5b65f9f7c540a3414007c7f874b34346587dac7e4feab7ae80cba"
CAPS = {
    "db": (1024**3, 0.25),
    "hindsight": (6 * 1024**3, 1.0),
    "model-router": (256 * 1024**2, 0.125),
    "runner": (512 * 1024**2, 0.125),
}
CRITICAL = {
    "HINDSIGHT_API_TENANT_EXTENSION": "hindsight_api.extensions.builtin.tenant:ApiKeyTenantExtension",
    "HINDSIGHT_API_LLM_TRACE_ENABLED": "false",
    "HINDSIGHT_API_OTEL_TRACES_ENABLED": "false",
    "HINDSIGHT_API_OTEL_EXPORTER_OTLP_ENDPOINT": "",
    "HINDSIGHT_API_OTEL_EXPORTER_OTLP_HEADERS": "",
    "HINDSIGHT_API_MCP_ENABLED": "false",
    "HINDSIGHT_API_WORKERS": "1",
    "HINDSIGHT_API_WORKER_ENABLED": "true",
    "HINDSIGHT_API_WORKER_ID": "ade-hindsight-probe-worker-1",
    "HINDSIGHT_API_WORKER_MAX_SLOTS": "1",
    "HINDSIGHT_API_WORKER_CONSOLIDATION_RESERVED_SLOTS": "0",
    "HINDSIGHT_API_WORKER_MAX_RETRIES": "0",
    "HINDSIGHT_API_LLM_MAX_RETRIES": "0",
    "HINDSIGHT_API_CONSOLIDATION_MAX_ATTEMPTS": "1",
    "HINDSIGHT_API_ENABLE_AUTO_CONSOLIDATION": "false",
    "HINDSIGHT_API_FAIL_ON_EXTRACTION_ERRORS": "true",
    "HINDSIGHT_API_LLM_PROVIDER": "openai",
    "HINDSIGHT_API_LLM_BASE_URL": "http://model-router:8010/v1",
    "HINDSIGHT_API_LLM_MODEL": "deepseek::deepseek-flash",
    "HINDSIGHT_API_LLM_EXTRA_BODY": '{"thinking":{"type":"disabled"}}',
    "HINDSIGHT_API_LLM_STRICT_SCHEMA": "false",
    "HINDSIGHT_API_EMBEDDINGS_PROVIDER": "openai",
    "HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
    "HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL": "http://model-router:8010/v1",
    "HINDSIGHT_API_EMBEDDINGS_QUERY_PREFIX": "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: ",
    "HINDSIGHT_API_EMBEDDINGS_PASSAGE_PREFIX": "",
    "HINDSIGHT_API_RERANKER_PROVIDER": "local",
    "HINDSIGHT_API_RERANKER_LOCAL_MODEL": "/models/bge-v2-m3",
    "HINDSIGHT_API_RERANKER_LOCAL_FORCE_CPU": "true",
    "HINDSIGHT_API_RERANKER_LOCAL_TRUST_REMOTE_CODE": "false",
    "HINDSIGHT_API_RERANKER_LOCAL_BATCH_SIZE": "1",
    "HINDSIGHT_API_RERANKER_LOCAL_MAX_CONCURRENT": "1",
    "HINDSIGHT_API_TEXT_SEARCH_EXTENSION": "pgroonga",
    "HINDSIGHT_API_VECTOR_EXTENSION": "pgvector",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "OMP_NUM_THREADS": "1",
}


def validate(document, private_dir, release_sha, workflow_dir=ROOT, allocations=None):
    assert document["name"] == PROJECT
    assert set(document["services"]) == set(CAPS)
    assert set(document.get("volumes", {})) == {"db-data", "model-cache"}
    for name, value in document.get("volumes", {}).items():
        assert set(value) <= {"name"} and value.get("name") == PROJECT + "_" + name
    network = document.get("networks", {})
    assert set(network) == {"default"}
    assert network["default"].get("name") == PROJECT + "_default"
    assert set(network["default"]) <= {"name", "ipam"} and not network["default"].get(
        "ipam"
    )
    allowed_binds = {
        str(workflow_dir / "docker/extensions.sql"),
        str(private_dir / "receipts"),
        str(workflow_dir / "qualification"),
    }
    for name, service in document["services"].items():
        assert service.get("restart") == "no"
        assert service.get("platform") == "linux/arm64"
        expected = (
            allocations[name]
            if allocations
            else {"memory": CAPS[name][0], "cpu": CAPS[name][1]}
        )
        assert int(service["mem_limit"]) == expected["memory"]
        assert float(service["cpus"]) == expected["cpu"]
        assert not any(
            key in service
            for key in (
                "container_name",
                "network_mode",
                "privileged",
                "devices",
                "external_links",
                "volumes_from",
            )
        )
        assert service.get("networks") == {"default": None}
        for mount in service.get("volumes", []):
            assert mount["type"] in {"bind", "volume"}
            if mount["type"] == "bind":
                assert mount["source"] in allowed_binds
            else:
                assert mount["source"] in {"db-data", "model-cache"}
        expected_mounts = {
            "db": {
                ("/var/lib/postgresql/data", "db-data"),
                (
                    "/docker-entrypoint-initdb.d/01-extensions.sql",
                    str(workflow_dir / "docker/extensions.sql"),
                ),
            },
            "hindsight": {
                ("/models", "model-cache"),
                ("/probe", str(workflow_dir / "qualification")),
            },
            "model-router": {("/receipts", str(private_dir / "receipts"))},
            "runner": {("/receipts", str(private_dir / "receipts"))},
        }
        assert {
            (m["target"], m["source"]) for m in service.get("volumes", [])
        } == expected_mounts[name]
        ports = service.get("ports", [])
        if name == "hindsight":
            assert {
                (p["host_ip"], str(p["published"]), p["target"]) for p in ports
            } == {("127.0.0.1", "18888", 8888), ("127.0.0.1", "19999", 9999)}
            assert service["image"] == HINDSIGHT_IMAGE
        else:
            assert not ports
            role = (
                "db"
                if name == "db"
                else "router"
                if name == "model-router"
                else "runner"
            )
            assert service["image"] == f"{PROJECT}-{role}:{release_sha}"
    henv = document["services"]["hindsight"]["environment"]
    assert all(henv.get(k) == v for k, v in CRITICAL.items())
    for key in (
        "HINDSIGHT_API_LLM_STRICT_SCHEMA_RETAIN",
        "HINDSIGHT_API_LLM_STRICT_SCHEMA_CONSOLIDATION",
    ):
        assert henv[key] == "false"
    for key, ceiling in [
        ("HINDSIGHT_API_LLM_TIMEOUT", 120),
        ("HINDSIGHT_API_RETAIN_WALL_TIMEOUT", 600),
        ("HINDSIGHT_API_CONSOLIDATION_WALL_TIMEOUT", 600),
        ("HINDSIGHT_API_RERANKER_LOCAL_TIMEOUT", 120),
        ("HINDSIGHT_API_MODEL_INIT_TIMEOUT", 180),
    ]:
        assert 0 < float(henv[key]) <= ceiling
    assert "HINDSIGHT_API_LLM_REASONING_EFFORT" not in henv
    runner_env = document["services"]["runner"]["environment"]
    assert runner_env["ADE_EVAL_SOURCE_SHA"] == release_sha
    assert runner_env["PROBE_RELEASE_SHA"] == release_sha
    for key in ("ADE_PROBE_REGISTRY_SHA256", "ADE_PROBE_EPOCH_SHA256"):
        assert re.fullmatch(r"[0-9a-f]{64}", runner_env[key])
    assert runner_env["ADE_PROBE_REGISTRY_SHA256"] != runner_env["ADE_PROBE_EPOCH_SHA256"]
    assert henv["HINDSIGHT_API_DATABASE_URL"].startswith(
        "postgresql://hindsight_probe:"
    )
    assert henv["HINDSIGHT_API_DATABASE_URL"].endswith("@db:5432/hindsight_probe")
    assert henv["HINDSIGHT_API_TENANT_API_KEY"] and henv["HINDSIGHT_CP_ACCESS_KEY"]
    assert (
        henv["HINDSIGHT_API_TENANT_API_KEY"] == henv["HINDSIGHT_CP_DATAPLANE_API_KEY"]
    )
    assert henv["HINDSIGHT_CP_ACCESS_KEY"] != henv["HINDSIGHT_API_TENANT_API_KEY"]
    renv = document["services"]["model-router"]["environment"]
    assert set(renv) == {
        "MODEL_ROUTER_SOURCES_FILE",
        "MODEL_ROUTER_MODEL_PROFILES_FILE",
        "MODEL_ROUTER_DEPLOYMENT_MANIFEST_FILE",
        "MODEL_ROUTER_API_KEY_SECRET",
        "MODEL_ROUTER_API_KEY",
        "MODEL_ROUTER_REQUEST_TIMEOUT_SECONDS",
        "DEEPSEEK_API_KEY",
        "DGX_EMBEDDING_API_KEY",
        "PROBE_RECEIPTS",
        "PROBE_PHASE_FILE",
    }
    assert (
        renv["MODEL_ROUTER_SOURCES_FILE"]
        == "workflows/evals/hindsight_memory_probe/config/sources.json"
    )
    assert (
        renv["MODEL_ROUTER_MODEL_PROFILES_FILE"]
        == "workflows/evals/hindsight_memory_probe/config/model-profiles.json"
    )
    assert (
        renv["MODEL_ROUTER_DEPLOYMENT_MANIFEST_FILE"]
        == "workflows/evals/hindsight_memory_probe/config/unqualified-deployment-manifest.absent.json"
    )
    assert not (
        workflow_dir / "config/unqualified-deployment-manifest.absent.json"
    ).exists()
    assert not any(
        k.startswith(("HINDSIGHT_API_RETAIN_LLM_", "HINDSIGHT_API_CONSOLIDATION_LLM_"))
        and k not in {"HINDSIGHT_API_CONSOLIDATION_LLM_PARALLELISM"}
        for k in henv
    )
    for field in (
        "HINDSIGHT_API_RETAIN_MAX_COMPLETION_TOKENS",
        "HINDSIGHT_API_CONSOLIDATION_MAX_COMPLETION_TOKENS",
    ):
        assert 0 < int(henv[field]) <= 4096

    assert renv["MODEL_ROUTER_API_KEY"] and renv["DEEPSEEK_API_KEY"]
    assert (
        renv["MODEL_ROUTER_API_KEY"]
        == henv["HINDSIGHT_API_LLM_API_KEY"]
        == henv["HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY"]
    )
    assert renv["MODEL_ROUTER_API_KEY_SECRET"] == ""
    sources = json.loads((workflow_dir / "config/sources.json").read_text())
    assert {s["id"] for s in sources} == {"deepseek", "dgx_embedding_sidecar"}
    for source in sources:
        assert source["enabled"] and source["api_key_secret"] == ""
        if source["id"] == "deepseek":
            assert (
                source["adapter"] == "deepseek_openai"
                and source["base_url"] == "https://api.deepseek.com"
            )
            assert source["api_key_env"] == "DEEPSEEK_API_KEY" and source[
                "model_allowlist"
            ] == ["deepseek-flash"]
        else:
            assert (
                source["base_url"] == "http://100.64.35.71:8001/v1"
                and source["base_url_env"] == ""
            )
            assert source["model_allowlist"] == ["Qwen/Qwen3-Embedding-0.6B"]
    profile = json.loads((workflow_dir / "config/model-profiles.json").read_text())
    assert set(profile) == {"deepseek::deepseek-flash"}
    assert profile["deepseek::deepseek-flash"]["thinking_default_enabled"] is True
    assert profile["deepseek::deepseek-flash"]["reasoning_effort_default"] == "high"


def render(env_file):
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(env_file),
            "-f",
            str(ROOT / "compose.yaml"),
            "--profile",
            "runner",
            "config",
            "--format",
            "json",
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError("compose_configuration_failed")
    return json.loads(result.stdout)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--allocations", type=Path)
    args = parser.parse_args()
    try:
        validate(
            render(args.env_file),
            args.private_dir,
            args.release_sha,
            allocations=json.loads(args.allocations.read_text())
            if args.allocations
            else None,
        )
    except Exception:
        raise SystemExit("probe_static_validation_failed") from None
    print("probe_static_validation_passed")
