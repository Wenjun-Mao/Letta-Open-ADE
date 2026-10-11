FROM python:3.12.12-slim-bookworm@sha256:228390eced221ad2986a3dd77e10b1accca6ba8ceb36f1572de1b346a337cc1a AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.5@sha256:8ba8ac26ed7be9ce3f0fbd510f8d26a3fb9b19056efe6c08433baf9762129edd /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy PATH=/opt/venv/bin:$PATH
# Only clean release inputs, never repository .env or host data.
COPY pyproject.toml uv.lock ./
COPY services/model-router/ services/model-router/
COPY services/ade-api/pyproject.toml services/ade-api/pyproject.toml
COPY packages/ packages/
COPY workflows/pyproject.toml workflows/pyproject.toml
FROM base AS router
RUN uv sync --frozen --no-dev --package ade-model-router --package ade-workflows
COPY workflows/evals/hindsight_memory_probe/ workflows/evals/hindsight_memory_probe/
ENV PYTHONPATH=/app/services/model-router/src:/app/packages/model-catalog-contracts/src:/app
CMD ["uvicorn", "workflows.evals.hindsight_memory_probe.router_entrypoint:create_app", "--factory", "--host", "0.0.0.0", "--port", "8010", "--no-access-log", "--log-level", "critical"]
FROM base AS runner
COPY services/ade-api/ services/ade-api/
RUN uv sync --frozen --no-dev --package ade-api
ENV PYTHONPATH=/app/services/ade-api/src:/app/packages/agent-runtime-eval-contracts/src:/app/packages/model-catalog-contracts/src:/app
ENTRYPOINT ["python", "-m", "ade_api.features.agent_runtime.hindsight_evaluation"]
CMD ["--help"]
