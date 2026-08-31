.PHONY: setup up down status logs test check openapi smoke eval-chat-memory eval-comment-persona eval-agent-runtime-v3 probe-models native-runtime-migrate native-runtime-up native-runtime-db-test native-runtime-lane-check native-runtime-policy-rebind native-runtime-preview-gate native-runtime-preview-up

SERVICE ?= ade-api
SOURCE ?= ark
ADE_SOURCE_REVISION ?= $(shell git rev-parse HEAD 2>/dev/null || echo unknown)
ADE_SOURCE_DIRTY ?= $(shell test -z "$$(git status --porcelain 2>/dev/null)" && echo false || echo true)
ADE_SOURCE_FINGERPRINT ?= $(shell python3 scripts/source_fingerprint.py 2>/dev/null || echo unknown)
export ADE_SOURCE_REVISION
export ADE_SOURCE_DIRTY
export ADE_SOURCE_FINGERPRINT

setup:
	uv sync --all-packages --frozen --group dev
	npm ci --prefix apps/ade-web

up:
	docker compose up -d --build

down:
	docker compose down

native-runtime-migrate:
	docker compose --profile native-runtime run --rm --build ade-runtime-migrate

native-runtime-lane-check:
	uv run python -m pytest tests/test_codebase_guardrails.py -q -k native_runtime_compose_lane

native-runtime-policy-rebind:
	uv run python scripts/rebind_agent_runtime_policy.py --apply

native-runtime-preview-gate:
	uv run python scripts/check_native_preview_gate.py

native-runtime-up: native-runtime-lane-check native-runtime-migrate
	ADE_API_AGENT_RUNTIME_V3_ENABLED=true ADE_API_AGENT_RUNTIME_V3_MODE=development docker compose --profile native-runtime up -d --build ade-native-api ade-runtime-worker

native-runtime-preview-up: native-runtime-lane-check native-runtime-preview-gate native-runtime-migrate
	ADE_API_AGENT_RUNTIME_V3_ENABLED=true ADE_API_AGENT_RUNTIME_V3_MODE=release ADE_NATIVE_PREVIEW_ENABLED=true docker compose --profile native-runtime up -d --build ade-native-api ade-runtime-worker ade-web

native-runtime-db-test: native-runtime-migrate
	docker compose --profile native-runtime run --rm --build --no-deps ade-runtime-db-test

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
	LETTA_ENV_FILE=.env.example docker compose --env-file .env.example config --quiet

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
	docker compose --profile native-runtime exec ade-native-api python workflows/evals/agent_runtime_v3_acceptance/run.py --config workflows/evals/agent_runtime_v3_acceptance/config.toml --rounds 3

probe-models:
	docker compose exec model-router python workflows/evals/provider_model_probe/run.py --source-id $(SOURCE) --mode chat-probe --write
