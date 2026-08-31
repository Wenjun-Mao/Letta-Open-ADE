from __future__ import annotations

import hashlib


def template_content_sha256(content: str) -> str:
    """Return the stable identity of the exact template text."""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()
