# Prompt Center

## Purpose

Prompt Center manages versioned system prompts and reusable chat/comment personas.
It does not run models or create agents.

## Ownership

- ADE Web: `apps/ade-web/src/features/prompt-center/`
- ADE API: `services/ade-api/src/ade_api/features/prompt_center/`
- Public API: `/api/v2/prompt-center/...`

## Request Flow

1. The Prompt Center UI calls prompt or persona routes composed by `api.py`.
2. `registry.py` stores prompts as Python content files and delegates personas to
   `personas/sqlite.py`.
3. `template_options.py` exposes active templates to the other ADE features.
4. The API returns normalized records; content changes are visible immediately.

## Dependencies And Boundaries

- Uses shared application dependencies, scenario defaults, and API metadata.
- Owns template validation, prompt file lifecycle, persona SQLite persistence, and
  prompt/persona revision helpers.
- Must not call Letta or model providers directly.

## Data And Content

- System prompts: `content/prompts/system/` with archived prompts below `archive/`.
- Persona seed: `content/personas/personas.jsonl`.
- Runtime personas and revision log: `data/runtime/` (ignored generated state).

## Tests

- Feature tests: `uv run python -m pytest services/ade-api/src/ade_api/features/prompt_center/tests -q`
- API behavior: `tests/test_update_api.py`

## Common Changes

| Change | Start here |
| --- | --- |
| Add a prompt endpoint | `prompts_api.py` and `contracts.py` |
| Add a persona endpoint | `personas_api.py` and `contracts.py` |
| Change prompt/persona persistence | `registry.py` or `personas/` |
| Change options seen by other labs | `template_options.py` |
