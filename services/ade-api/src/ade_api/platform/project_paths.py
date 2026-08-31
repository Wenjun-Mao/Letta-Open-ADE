from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(os.getenv("ADE_REPOSITORY_ROOT", Path.cwd())).resolve()


def resolve_project_path(value: str, *, project_root: Path = PROJECT_ROOT) -> Path:
    path = Path(str(value or "").strip())
    return path if path.is_absolute() else project_root / path
