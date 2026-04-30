# Utility Scripts

This folder contains repo-wide automation and diagnostic scripts for managing both your local development environment and the Letta server. Workflow bundles with their own config/input/output lifecycle live under `evals/`.

You should generally run these scripts from the **project root directory**, not from inside the `scripts/` folder.

## Scripts Overview

### Database Resets
Wipes all existing Letta memory/agents inside the PostgreSQL volume and fully restarts the Docker containers for a clean slate. Supports passing an env file argument (defaults to `.env`).

* **Windows (PowerShell):** `reset_database.ps1`
* **Linux / Ubuntu (Bash):** `reset_database.sh`

### Letta Configuration & Tools
* **`sync_tools.py`**: Connects to the running Letta server, pulls a list of *all* available tools, and regenerates `agent_platform_api/letta/tools.py` for IDE autocomplete and inline documentation. You should run this anytime a new tool is published.
* **`collect_diagnostics.sh`**: Collects Docker/Compose status, health checks, service logs, and connectivity probes into a timestamped diagnostics bundle. Designed for remote machine troubleshooting.
* **`seed_nltk_data.sh`**: Pre-downloads NLTK `punkt_tab` into `data/nltk_data` so Letta startup can use local NLTK data in restricted/offline networks.
* **`persona_library.py`**: Imports/exports SQLite persona records as JSONL or Markdown.

---

## 🚀 Quick Execution Commands

**Reset the Letta Database (Windows - PowerShell):**
```powershell
.\scripts\reset_database.ps1
```

**Reset with a specific env file (Windows - PowerShell):**
```powershell
.\scripts\reset_database.ps1 .env
```

**Reset the Letta Database (Ubuntu / Linux - Terminal):**
```bash
chmod +x scripts/reset_database.sh
./scripts/reset_database.sh
```

**Reset with a specific env file (Ubuntu / Linux - Terminal):**
```bash
chmod +x scripts/reset_database.sh
./scripts/reset_database.sh .env
```

**Sync Letta Tools for autocomplete:**
```bash
uv run scripts/sync_tools.py
```

**Collect diagnostics bundle (Ubuntu/Linux):**
```bash
chmod +x scripts/collect_diagnostics.sh
./scripts/collect_diagnostics.sh .env
```

**Pre-seed NLTK data for startup (Ubuntu/Linux):**
```bash
chmod +x scripts/seed_nltk_data.sh
./scripts/seed_nltk_data.sh
```

The script prints and saves the output bundle path, for example:

- `diagnostics/letta_diag_YYYYMMDD_HHMMSS/`
- `diagnostics/letta_diag_YYYYMMDD_HHMMSS.tar.gz`

**Run Agent Platform API E2E Check:**
```bash
uv run python tests/checks/platform_api_e2e_check.py
```

**Run ADE MVP Smoke E2E Check:**
```bash
uv run python tests/checks/ade_mvp_smoke_e2e_check.py
```

**Run full pytest coverage:**
```bash
uv run python -m pytest
```

**Import/export the SQLite persona library:**
```bash
uv run python scripts/persona_library.py --help
```

Provider probes and persona evaluation workflows live under `evals/`; see `evals/provider_model_probe/README.md` and `evals/comment_persona_eval/README.md`.

**Start Letta with a specific env profile (example `.env`):**
```bash
LETTA_ENV_FILE=.env docker compose --profile ui up -d
```
