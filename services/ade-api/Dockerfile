FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/ade-api/src:/app/packages/model-catalog-contracts/src:/app \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy

WORKDIR /app

# Install runtime dependencies at build time so container startup is instant.
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock ./
COPY services/ade-api ./services/ade-api
COPY packages/model-catalog-contracts ./packages/model-catalog-contracts
COPY workflows/pyproject.toml ./workflows/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package ade-api --package ade-workflows --frozen --no-dev

# Copy runtime assets required by ADE API and Test Center workflows.
COPY config ./config
COPY content ./content
COPY workflows ./workflows

EXPOSE 8000

CMD ["/opt/venv/bin/uvicorn", "ade_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
