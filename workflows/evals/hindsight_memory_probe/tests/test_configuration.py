import copy
import json
import shutil
from pathlib import Path

import pytest

from workflows.evals.hindsight_memory_probe.campaign_clock import (
    activation_receipts_root,
)
from workflows.evals.hindsight_memory_probe.validate import ROOT, render, validate


@pytest.fixture
def resolved(monkeypatch):
    monkeypatch.setenv("DGX_EMBEDDING_API_KEY", "")
    if not shutil.which("docker"):
        pytest.skip(
            "Docker Compose CLI unavailable; config rendering is an explicit gap"
        )
    private_dir = Path("/tmp/ade-hindsight-probe-dummy")
    return render(
        ROOT / "config/dummy.env.example", activation_receipts_root(private_dir)
    )


def test_owned_dummy_compose_and_optional_existing_embedding_key(resolved):
    validate(resolved, Path("/tmp/ade-hindsight-probe-dummy"), "0" * 40)
    assert (
        resolved["services"]["model-router"]["environment"]["DGX_EMBEDDING_API_KEY"]
        == ""
    )
    assert (
        "\n"
        in resolved["services"]["hindsight"]["environment"][
            "HINDSIGHT_API_EMBEDDINGS_QUERY_PREFIX"
        ]
    )
    assert (
        "\\n"
        not in resolved["services"]["hindsight"]["environment"][
            "HINDSIGHT_API_EMBEDDINGS_QUERY_PREFIX"
        ]
    )
    env = resolved["services"]["hindsight"]["environment"]
    assert env["HINDSIGHT_API_LLM_TRACE_ENABLED"] == "false"
    assert env["HINDSIGHT_API_OTEL_TRACES_ENABLED"] == "false"
    assert env["HINDSIGHT_API_OTEL_EXPORTER_OTLP_ENDPOINT"] == ""
    assert not (ROOT / "config/unqualified-deployment-manifest.absent.json").exists()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d["services"]["db"].update(
            ports=[{"host_ip": "127.0.0.1", "published": "5432", "target": 5432}]
        ),
        lambda d: d["services"]["hindsight"].update(container_name="global-name"),
        lambda d: d["services"]["hindsight"].update(restart="always"),
        lambda d: d["services"]["hindsight"]["environment"].update(
            HINDSIGHT_API_TENANT_API_KEY=""
        ),
        lambda d: d["services"]["hindsight"]["environment"].update(
            HINDSIGHT_API_DATABASE_URL="postgresql://shared/db"
        ),
        lambda d: d["services"]["hindsight"]["environment"].update(
            HINDSIGHT_API_WORKER_CONSOLIDATION_RESERVED_SLOTS="2"
        ),
        lambda d: d["services"]["hindsight"]["environment"].update(
            HINDSIGHT_API_LLM_REASONING_EFFORT="high"
        ),
        lambda d: d["services"]["hindsight"]["environment"].update(
            HINDSIGHT_API_LLM_TRACE_ENABLED="true"
        ),
        lambda d: d["services"]["hindsight"]["environment"].update(
            HINDSIGHT_API_OTEL_EXPORTER_OTLP_ENDPOINT="http://external"
        ),
        lambda d: d["services"]["model-router"]["environment"].update(
            MODEL_ROUTER_SOURCES="[]"
        ),
        lambda d: d["services"]["hindsight"]["environment"].update(
            HINDSIGHT_API_RETAIN_LLM_MODEL="new-provider"
        ),
        lambda d: d["networks"]["default"].update(external=True),
        lambda d: d["volumes"]["db-data"].update(external=True),
        lambda d: d["services"]["runner"]["volumes"].append(
            {"type": "bind", "source": "/var/run/docker.sock", "target": "/sock"}
        ),
        lambda d: d["services"]["hindsight"]["ports"][0].update(host_ip="0.0.0.0"),
    ],
)
def test_dangerous_configuration_drift_fails(resolved, mutation):
    value = copy.deepcopy(resolved)
    mutation(value)
    with pytest.raises((AssertionError, KeyError)):
        validate(value, Path("/tmp/ade-hindsight-probe-dummy"), "0" * 40)


def test_recipe_and_model_pins():
    recipe = (ROOT / "docker/postgres.Dockerfile").read_text()
    assert "postgresql-17-pgvector=0.8.6-1.pgdg13+1" in recipe
    assert (
        "@sha256:229a259a79cdfa771fdb9e3974f60ea8ac479c57285da520daab039517b4baf3"
        in recipe
    )
    pins = json.loads((ROOT / "config/pins.json").read_text())
    assert pins["bge_revision"] == "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    assert pins["embedding_served_max_input_tokens"] == 8192
