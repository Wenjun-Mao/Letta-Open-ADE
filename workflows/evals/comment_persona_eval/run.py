from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflows.evals.comment_persona_eval.workflow import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
