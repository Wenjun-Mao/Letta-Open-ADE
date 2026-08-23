"""Legacy package for the Agent Studio human memory template.

Persona records now live in the SQLite-backed ADE persona library instead of
Python modules under this package.
"""

from __future__ import annotations

from .human_template import HUMAN_TEMPLATE

PERSONAS: dict[str, str] = {}

__all__ = ["HUMAN_TEMPLATE", "PERSONAS"]
