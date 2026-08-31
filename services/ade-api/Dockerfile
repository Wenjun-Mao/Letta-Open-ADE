FROM python:3.12-slim AS base

ARG ADE_SOURCE_REVISION=unknown
ARG ADE_SOURCE_DIRTY=true
ARG ADE_SOURCE_FINGERPRINT=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/services/ade-api/src:/app/packages/agent-runtime-eval-contracts/src:/app/packages/model-catalog-contracts/src:/app \
    PATH="/opt/venv/bin:${PATH}" \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    ADE_SOURCE_REVISION=${ADE_SOURCE_REVISION} \
    ADE_SOURCE_DIRTY=${ADE_SOURCE_DIRTY} \
    ADE_SOURCE_FINGERPRINT=${ADE_SOURCE_FINGERPRINT}

WORKDIR /app

# Install runtime dependencies at build time so container startup is instant.
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /usr/local/bin/
COPY pyproject.toml uv.lock ./
COPY Makefile compose.yaml ./
COPY scripts/check_native_preview_gate.py ./scripts/check_native_preview_gate.py
COPY scripts/source_fingerprint.py ./scripts/source_fingerprint.py
COPY services/ade-api ./services/ade-api
COPY packages/agent-runtime-eval-contracts ./packages/agent-runtime-eval-contracts
COPY packages/model-catalog-contracts ./packages/model-catalog-contracts
COPY workflows/pyproject.toml ./workflows/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --package ade-api --package ade-workflows --frozen --no-dev

# Copy runtime assets required by ADE API and Test Center workflows.
COPY config ./config
COPY content ./content
COPY workflows ./workflows

FROM base AS test

# Database contracts run in a dedicated test image using the committed workspace lock.
COPY services/model-router ./services/model-router
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --all-packages --frozen --group dev

FROM base AS runtime

EXPOSE 8000

CMD ["/opt/venv/bin/uvicorn", "ade_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
