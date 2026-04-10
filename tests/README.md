# Tests Layout

This directory uses a role-based structure:

- checks/: focused diagnostics and sanity checks
- runners/: config-driven or scenario-driven test runners
- shared/: constants shared by checks and runners
- configs/: test configurations and reusable conversation fixtures
- outputs/: generated artifacts from test runs

## Main Entry Points

- tests/runners/persona_guardrail_runner.py
  - Runs suite JSON configs from tests/configs/suites/
  - Writes per-run artifacts to tests/outputs/
- tests/runners/memory_update_runner.py
  - Runs fresh-agent rounds to validate memory update reliability
  - Validates expected-name persistence and memory mutation
- tests/checks/provider_embedding_matrix_check.py
  - Smoke checks dev_ui options/create and embedding combos
- tests/checks/prompt_strategy_check.py
  - Compares prompt strategy behavior on memory updates
- tests/checks/agent_bootstrap_check.py
  - Verifies bootstrap memory block descriptions and defaults

## Typical Commands

```bash
uv run tests/runners/persona_guardrail_runner.py --config tests/configs/suites --model lmstudio_openai/gemma-4-31b-it --embedding letta/letta-free
uv run tests/runners/memory_update_runner.py --rounds 10 --model lmstudio_openai/gemma-4-31b-it --embedding letta/letta-free
uv run tests/checks/provider_embedding_matrix_check.py
uv run tests/checks/prompt_strategy_check.py
uv run tests/checks/agent_bootstrap_check.py
```

Examples:
```bash
uv run python tests/runners/persona_guardrail_runner.py --config tests/configs/suites/lmstudio_custom_v2.json --model lmstudio_openai/gemma-4-31b-it --embedding letta/letta-free

uv run python tests/runners/memory_update_runner.py --rounds 10 --model lmstudio_openai/gemma-4-31b-it --embedding letta/letta-free --turn "你好，我叫张伟"

uv run python tests/runners/memory_update_runner.py --rounds 10 --model openai-proxy/doubao-seed-1-8-251228 --embedding letta/letta-free --turn "你好，我叫张伟"
```