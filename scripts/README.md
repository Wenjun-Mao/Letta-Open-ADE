# Utility Scripts

This folder contains various automation and diagnostic scripts for managing both your local development environment and the Letta server.

You should generally run these scripts from the **project root directory** (e.g., `letta-doubao/`), not from inside the `scripts/` folder.

## Scripts Overview

### Database Resets
Wipes all existing Letta memory/agents inside the PostgreSQL volume and fully restarts the Docker containers for a clean slate. Uses `.env2` to reinitialize.

* **Windows (PowerShell):** `reset_database.ps1`
* **Linux / Ubuntu (Bash):** `reset_database.sh`

### Letta Configuration & Tools
* **`sync_tools.py`**: Connects to the running Letta server, pulls a list of *all* available tools, and generates `utils/letta_tools.py` for full IDE autocomplete and inline documentation. You should run this anytime a new tool is published.
* **`verify_agent.py`**: A diagnostic smoke-test script. Creates a test Chinese-speaking agent (Lin Xiao Tang) and pulls back its fully compiled internal `SystemMessage` format and attached blocks to verify DB formatting constraints.

---

## 🚀 Quick Execution Commands

**Reset the Letta Database (Windows - PowerShell):**
```powershell
.\scripts\reset_database.ps1
```

**Reset the Letta Database (Ubuntu / Linux - Terminal):**
```bash
chmod +x scripts/reset_database.sh
./scripts/reset_database.sh
```

**Sync Letta Tools for autocomplete:**
```bash
uv run scripts/sync_tools.py
```

**Run Agent Integration / Verification Test:**
```bash
uv run scripts/verify_agent.py
```
