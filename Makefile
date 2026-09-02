.PHONY: setup up down status logs test check openapi smoke eval-chat-memory eval-comment-persona eval-agent-runtime-v3 probe-models agent-studio-migrate agent-studio-up agent-studio-development-up agent-studio-db-test agent-studio-lane-check agent-studio-policy-rebind agent-studio-qualification agent-studio-promotion-apply agent-studio-conformance agent-studio-rollback-rehearsal agent-studio-cutover-review agent-studio-release-gate agent-studio-release-up

SERVICE ?= ade-api
SOURCE ?= ark
ADE_SOURCE_REVISION ?= $(shell git rev-parse HEAD 2>/dev/null || echo unknown)
ADE_SOURCE_DIRTY ?= $(shell test -z "$$(git status --porcelain 2>/dev/null)" && echo false || echo true)
ADE_SOURCE_FINGERPRINT ?= $(shell python3 scripts/source_fingerprint.py 2>/dev/null || echo unknown)
AGENT_STUDIO_EVIDENCE_DIR ?= tests/outputs/agent-studio-cutover
AGENT_STUDIO_CONFORMANCE_RECEIPT ?= $(AGENT_STUDIO_EVIDENCE_DIR)/conformance.json
AGENT_STUDIO_ROLLBACK_RECEIPT ?= $(AGENT_STUDIO_EVIDENCE_DIR)/rollback.json
AGENT_STUDIO_QUALIFICATION_PROPOSAL ?=
AGENT_STUDIO_PARITY_ROOT ?=
AGENT_STUDIO_LEGACY_REVISION ?=
AGENT_STUDIO_REVIEWER ?=
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

agent-studio-migrate:
	docker compose run --rm --build ade-runtime-migrate

agent-studio-lane-check:
	uv run python -m pytest tests/test_codebase_guardrails.py -q -k agent_studio_compose_lane

agent-studio-policy-rebind:
	uv run python scripts/rebind_agent_runtime_policy.py --apply

agent-studio-qualification: eval-agent-runtime-v3

agent-studio-promotion-apply:
	@test -n "$(AGENT_STUDIO_QUALIFICATION_PROPOSAL)" || { echo "Set AGENT_STUDIO_QUALIFICATION_PROPOSAL" >&2; exit 2; }
	uv run python -m workflows.evals.agent_runtime_v3_acceptance.promote --proposal "$(AGENT_STUDIO_QUALIFICATION_PROPOSAL)" --apply

agent-studio-conformance:
	uv run python scripts/record_agent_studio_conformance.py --output "$(AGENT_STUDIO_CONFORMANCE_RECEIPT)"

agent-studio-rollback-rehearsal:
	@test -n "$(AGENT_STUDIO_LEGACY_REVISION)" || { echo "Set AGENT_STUDIO_LEGACY_REVISION" >&2; exit 2; }
	uv run python scripts/rehearse_agent_studio_rollback.py --legacy-revision "$(AGENT_STUDIO_LEGACY_REVISION)" --output "$(AGENT_STUDIO_ROLLBACK_RECEIPT)"

agent-studio-cutover-review:
	@test -n "$(AGENT_STUDIO_QUALIFICATION_PROPOSAL)" || { echo "Set AGENT_STUDIO_QUALIFICATION_PROPOSAL" >&2; exit 2; }
	@test -n "$(AGENT_STUDIO_PARITY_ROOT)" || { echo "Set AGENT_STUDIO_PARITY_ROOT" >&2; exit 2; }
	@test -n "$(AGENT_STUDIO_REVIEWER)" || { echo "Set AGENT_STUDIO_REVIEWER" >&2; exit 2; }
	uv run python scripts/review_agent_studio_cutover.py --qualification-proposal "$(AGENT_STUDIO_QUALIFICATION_PROPOSAL)" --parity-root "$(AGENT_STUDIO_PARITY_ROOT)" --conformance-receipt "$(AGENT_STUDIO_CONFORMANCE_RECEIPT)" --rollback-receipt "$(AGENT_STUDIO_ROLLBACK_RECEIPT)" --reviewer "$(AGENT_STUDIO_REVIEWER)" --apply

agent-studio-release-gate:
	uv run python scripts/check_agent_studio_release_gate.py

agent-studio-up: agent-studio-lane-check
	docker compose up -d --build

agent-studio-development-up: agent-studio-lane-check
	ADE_API_AGENT_RUNTIME_V3_MODE=development docker compose up -d --build

agent-studio-release-up: agent-studio-lane-check agent-studio-release-gate
	docker compose up -d --build

agent-studio-db-test: agent-studio-migrate
	docker compose --profile native-runtime-test run --rm --build --no-deps ade-runtime-db-test

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

eval-agent-runtime-v3: agent-studio-development-up
	docker compose exec ade-native-api python workflows/evals/agent_runtime_v3_acceptance/run.py --config workflows/evals/agent_runtime_v3_acceptance/config.toml --rounds 3

probe-models:
	docker compose exec model-router python workflows/evals/provider_model_probe/run.py --source-id $(SOURCE) --mode chat-probe --write
