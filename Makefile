.DEFAULT_GOAL := help
.PHONY: help setup up down status logs test check openapi smoke eval-chat-memory eval-comment-persona eval-agent-runtime probe-models runtime-migrate runtime-development-up runtime-policy-rebind runtime-qualification runtime-conformance runtime-release-promote runtime-release-gate runtime-release-up

SERVICE ?= ade-api
SOURCE ?= ark
ADE_SOURCE_REVISION ?= $(shell git rev-parse HEAD 2>/dev/null || echo unknown)
ADE_SOURCE_DIRTY ?= $(shell test -z "$$(git status --porcelain 2>/dev/null)" && echo false || echo true)
ADE_SOURCE_FINGERPRINT ?= $(shell python3 scripts/source_fingerprint.py 2>/dev/null || echo unknown)
AGENT_RUNTIME_EVIDENCE_DIR ?= tests/outputs/agent-studio-release
AGENT_RUNTIME_CONFORMANCE_RECEIPT ?= $(AGENT_RUNTIME_EVIDENCE_DIR)/conformance.json
AGENT_RUNTIME_QUALIFICATION_PROPOSAL ?=
AGENT_RUNTIME_REVIEWER ?=
export ADE_SOURCE_REVISION
export ADE_SOURCE_DIRTY
export ADE_SOURCE_FINGERPRINT

help:
	@printf '%s\n' \
		'make up                         Start the local development stack' \
		'make check                      Run all source and frontend checks' \
		'make smoke                      Exercise the current stack' \
		'make runtime-qualification      Run three native qualification rounds' \
		'make runtime-conformance        Record deterministic conformance' \
		'make runtime-release-promote    Promote reviewed evidence (requires variables)' \
		'make runtime-release-up         Gate and start the qualified release stack'

setup:
	uv sync --all-packages --frozen --group dev
	npm ci --prefix apps/ade-web

up:
	ADE_API_AGENT_RUNTIME_MODE=development docker compose up -d --build

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
	ADE_ENV_FILE=.env.example docker compose --env-file .env.example config --quiet

openapi:
	uv run python scripts/export_openapi.py
	uv run python scripts/generate_openapi_zh_manual.py

smoke:
	docker compose exec ade-api python workflows/smoke/ade_api_e2e_check.py

eval-chat-memory:
	docker compose exec ade-api python workflows/evals/chat_memory_eval/run.py --config workflows/evals/chat_memory_eval/config.toml --rounds 1

eval-comment-persona:
	docker compose exec ade-api python workflows/evals/comment_persona_eval/run.py --config workflows/evals/comment_persona_eval/config.toml

eval-agent-runtime: runtime-development-up
	docker compose exec ade-api python workflows/evals/agent_runtime_acceptance/run.py --config workflows/evals/agent_runtime_acceptance/config.toml --rounds 3

probe-models:
	docker compose exec model-router python workflows/evals/provider_model_probe/run.py --source-id $(SOURCE) --mode chat-probe --write

runtime-migrate:
	docker compose run --rm --build ade-runtime-migrate

runtime-development-up: up

runtime-policy-rebind:
	uv run python scripts/rebind_agent_runtime_policy.py --apply

runtime-qualification: eval-agent-runtime

runtime-conformance:
	uv run python scripts/record_agent_studio_conformance.py --output "$(AGENT_RUNTIME_CONFORMANCE_RECEIPT)"

runtime-release-promote:
	@test -n "$(AGENT_RUNTIME_QUALIFICATION_PROPOSAL)" || { echo "Set AGENT_RUNTIME_QUALIFICATION_PROPOSAL" >&2; exit 2; }
	@test -n "$(AGENT_RUNTIME_REVIEWER)" || { echo "Set AGENT_RUNTIME_REVIEWER" >&2; exit 2; }
	uv run python scripts/promote_agent_studio_release.py --qualification-proposal "$(AGENT_RUNTIME_QUALIFICATION_PROPOSAL)" --conformance-receipt "$(AGENT_RUNTIME_CONFORMANCE_RECEIPT)" --reviewer "$(AGENT_RUNTIME_REVIEWER)" --apply

runtime-release-gate:
	uv run python scripts/check_agent_studio_release_gate.py

runtime-release-up: runtime-release-gate
	ADE_API_AGENT_RUNTIME_MODE=release docker compose up -d --build
