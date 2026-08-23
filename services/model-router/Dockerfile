FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/model-router/src:/app/packages/model-catalog-contracts/src:/app \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock ./
COPY services/model-router ./services/model-router
COPY packages/model-catalog-contracts ./packages/model-catalog-contracts
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package ade-model-router --frozen --no-dev

COPY config ./config
COPY content/model-catalog ./content/model-catalog
COPY workflows/evals/provider_model_probe ./workflows/evals/provider_model_probe

EXPOSE 8010

CMD ["/opt/venv/bin/uvicorn", "model_router.app:app", "--host", "0.0.0.0", "--port", "8010"]
