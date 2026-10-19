FROM python:3.12.12-slim-bookworm@sha256:228390eced221ad2986a3dd77e10b1accca6ba8ceb36f1572de1b346a337cc1a AS base
COPY --from=ghcr.io/astral-sh/uv:0.12.5@sha256:8ba8ac26ed7be9ce3f0fbd510f8d26a3fb9b19056efe6c08433baf9762129edd /uv /usr/local/bin/uv
WORKDIR /app
ARG ADE_SOURCE_REVISION=unknown
ARG ADE_SOURCE_FINGERPRINT=unknown
ENV ADE_SOURCE_REVISION=${ADE_SOURCE_REVISION} ADE_SOURCE_FINGERPRINT=${ADE_SOURCE_FINGERPRINT} ADE_SOURCE_DIRTY=false
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy PATH=/opt/venv/bin:$PATH
COPY pyproject.toml uv.lock ./
COPY compose.yaml ./
COPY services/model-router/ services/model-router/
COPY services/ade-api/ services/ade-api/
COPY packages/ packages/
COPY workflows/pyproject.toml workflows/pyproject.toml
COPY workflows/ workflows/
COPY scripts/ scripts/
COPY content/ content/
COPY config/ config/
ENV PYTHONPATH=/app/services/model-router/src:/app/services/ade-api/src:/app/packages/agent-runtime-eval-contracts/src:/app/packages/model-catalog-contracts/src:/app
FROM base AS router
RUN uv sync --frozen --no-dev --package ade-model-router --package ade-workflows
CMD ["uvicorn", "model_router.app:app", "--host", "0.0.0.0", "--port", "8010", "--no-access-log"]
FROM base AS runner
RUN uv sync --frozen --no-dev --package ade-api --package ade-workflows
ENTRYPOINT ["python"]
FROM runner AS api
ENTRYPOINT []
CMD ["uvicorn", "ade_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
