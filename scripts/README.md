# Utility Scripts

This folder contains various automation and diagnostic scripts for managing both your local development environment and the Letta server.

You should generally run these scripts from the **project root directory** (e.g., `letta-doubao/`), not from inside the `scripts/` folder.

## Scripts Overview

### Database Resets
Wipes all existing Letta memory/agents inside the PostgreSQL volume and fully restarts the Docker containers for a clean slate. Supports passing an env file argument (defaults to `.env2`).

* **Windows (PowerShell):** `reset_database.ps1`
* **Linux / Ubuntu (Bash):** `reset_database.sh`

### Letta Configuration & Tools
* **`sync_tools.py`**: Connects to the running Letta server, pulls a list of *all* available tools, and generates `utils/letta_tools.py` for full IDE autocomplete and inline documentation. You should run this anytime a new tool is published.
* **`collect_diagnostics.sh`**: Collects Docker/Compose status, health checks, service logs, and connectivity probes into a timestamped diagnostics bundle. Designed for remote machine troubleshooting.

### Testing Scripts Location
All test runners were moved to the `tests/` directory to keep responsibilities clear:
* `tests/run_conversation_suite.py`
* `tests/test_provider_embedding_matrix.py`
* `tests/test_prompts.py`
* `tests/verify_agent.py`

---

## 🚀 Quick Execution Commands

**Reset the Letta Database (Windows - PowerShell):**
```powershell
.\scripts\reset_database.ps1
```

**Reset with a specific env file (Windows - PowerShell):**
```powershell
.\scripts\reset_database.ps1 .env3
```

**Reset the Letta Database (Ubuntu / Linux - Terminal):**
```bash
chmod +x scripts/reset_database.sh
./scripts/reset_database.sh
```

**Reset with a specific env file (Ubuntu / Linux - Terminal):**
```bash
chmod +x scripts/reset_database.sh
./scripts/reset_database.sh .env3
```

**Sync Letta Tools for autocomplete:**
```bash
uv run scripts/sync_tools.py
```

**Collect diagnostics bundle (Ubuntu/Linux):**
```bash
chmod +x scripts/collect_diagnostics.sh
./scripts/collect_diagnostics.sh .env3
```

The script prints and saves the output bundle path, for example:

- `diagnostics/letta_diag_YYYYMMDD_HHMMSS/`
- `diagnostics/letta_diag_YYYYMMDD_HHMMSS.tar.gz`

**Run Agent Integration / Verification Test:**
```bash
uv run tests/verify_agent.py
```

**Run Provider + Embedding Matrix Test (27B only):**
```bash
uv run tests/test_provider_embedding_matrix.py
```

**Run Provider + Embedding Matrix Test with custom handles:**
```bash
TEST_EMBEDDING_HANDLES="letta/letta-free,lmstudio_openai/text-embedding-qwen3-embedding-0.6b" uv run tests/test_provider_embedding_matrix.py
```

**Run Conversation Suite (all suite configs):**
```bash
uv run tests/run_conversation_suite.py
```

**Run Conversation Suite and force one embedding handle for all configs:**
```bash
uv run tests/run_conversation_suite.py --config tests/configs/suites --embedding letta/letta-free
```

**Run Conversation Suite for a specific config file:**
```bash
uv run tests/run_conversation_suite.py --config tests/configs/suites/qwen27_custom_v1.json
```

**Run Prompt Variant Comparison:**
```bash
uv run tests/test_prompts.py
```

**Start Letta with a specific env profile (example `.env3`):**
```bash
LETTA_ENV_FILE=.env3 docker compose --profile ui up -d
```
