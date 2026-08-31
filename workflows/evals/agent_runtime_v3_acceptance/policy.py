from __future__ import annotations

from pathlib import Path
from typing import Final

from ade_api.features.agent_runtime_v3.release_policy import (
    PRODUCTION_POLICY_INPUTS,
    fingerprint_policy_hashes,
    production_policy_hashes as _production_policy_hashes,
)


PROJECT_ROOT: Final = Path(__file__).resolve().parents[3]


def production_policy_hashes(project_root: Path = PROJECT_ROOT) -> dict[str, str]:
    return _production_policy_hashes(project_root)


__all__ = [
    "PRODUCTION_POLICY_INPUTS",
    "fingerprint_policy_hashes",
    "production_policy_hashes",
]
