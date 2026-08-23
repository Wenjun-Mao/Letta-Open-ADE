.PHONY: setup up down status logs test check openapi smoke eval-chat-memory eval-comment-persona probe-models

SERVICE ?= ade-api
SOURCE ?= ark

setup:
	uv sync --all-packages --frozen --group dev
	npm ci --prefix apps/ade-web

up:
	docker compose up -d --build

down:
	docker compose down

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
	docker compose exec ade-api python workflows/smoke/platform_api_e2e_check.py

eval-chat-memory:
	docker compose exec ade-api python workflows/evals/chat_memory_eval/run.py --config workflows/evals/chat_memory_eval/config.toml --rounds 1

eval-comment-persona:
	docker compose exec ade-api python workflows/evals/comment_persona_eval/run.py --config workflows/evals/comment_persona_eval/config.toml

probe-models:
	docker compose exec model-router python workflows/evals/provider_model_probe/run.py --source-id $(SOURCE) --mode chat-probe --write
