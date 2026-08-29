.PHONY: setup up down status logs test check openapi smoke eval-chat-memory eval-comment-persona eval-agent-runtime-v3 probe-models native-runtime-migrate native-runtime-up native-runtime-db-test

SERVICE ?= ade-api
SOURCE ?= ark
ADE_SOURCE_REVISION ?= $(shell git rev-parse HEAD 2>/dev/null || echo unknown)
ADE_SOURCE_DIRTY ?= $(shell test -z "$$(git status --porcelain 2>/dev/null)" && echo false || echo true)
export ADE_SOURCE_REVISION
export ADE_SOURCE_DIRTY

setup:
	uv sync --all-packages --frozen --group dev
	npm ci --prefix apps/ade-web

up:
	docker compose up -d --build

down:
	docker compose down

native-runtime-migrate:
	docker compose --profile native-runtime run --rm ade-runtime-migrate

native-runtime-up: native-runtime-migrate
	ADE_API_AGENT_RUNTIME_V3_ENABLED=true ADE_API_AGENT_RUNTIME_V3_MODE=development docker compose --profile native-runtime up -d --build ade-api ade-runtime-worker

native-runtime-db-test: native-runtime-migrate
	docker compose --profile native-runtime run --rm \
		ade-runtime-migrate /bin/sh -ec \
		'export ADE_TEST_DATABASE_URL="postgresql+psycopg://$${ADE_PG_APP_USER:-ade_app}:$${ADE_PG_APP_PASSWORD}@postgres:5432/$${ADE_PG_DB:-ade}"; uv pip install --quiet --python /opt/venv/bin/python pytest && /opt/venv/bin/python -m pytest services/ade-api/tests/agent_runtime_v3/persistence -q'

status:
	docker compose ps

logs:
	docker compose logs --tail=200 $(SERVICE)

test:
	uv run python -m pytest
	npm --prefix apps/ade-web run test

check: test
	uv run ruff check services packages workflows scripts tests
	uv run python scripts/check_python_format.py --base origin/main
	npm --prefix apps/ade-web run lint
	npm --prefix apps/ade-web run build
	docker compose --env-file .env.example config --quiet

openapi:
	uv run python scripts/export_openapi.py
	uv run python scripts/generate_openapi_zh_manual.py

smoke:
	docker compose exec ade-api python workflows/smoke/ade_api_e2e_check.py

eval-chat-memory:
	docker compose exec ade-api python workflows/evals/chat_memory_eval/run.py --config workflows/evals/chat_memory_eval/config.toml --rounds 1

eval-comment-persona:
	docker compose exec ade-api python workflows/evals/comment_persona_eval/run.py --config workflows/evals/comment_persona_eval/config.toml

eval-agent-runtime-v3: native-runtime-up
	docker compose exec ade-api python workflows/evals/agent_runtime_v3_acceptance/run.py --config workflows/evals/agent_runtime_v3_acceptance/config.toml --rounds 3

probe-models:
	docker compose exec model-router python workflows/evals/provider_model_probe/run.py --source-id $(SOURCE) --mode chat-probe --write
