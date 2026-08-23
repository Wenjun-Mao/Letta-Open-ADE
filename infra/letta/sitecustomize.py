"""Runtime patch for NLTK startup behavior in Letta.

Letta calls nltk.download("punkt_tab") during app startup. In restricted
networks that call can block readiness for a long time even when local NLTK
resources already exist.

This patch makes punkt_tab startup deterministic:
- return immediately when tokenizers/punkt_tab is already present locally
- optionally skip network download entirely when strict-local mode is enabled
- otherwise enforce a short socket timeout for the download attempt
"""

from __future__ import annotations

import os
import socket


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _patch_nltk_download() -> None:
    try:
        import nltk
    except Exception:
        return

    target_resource = "punkt_tab"
    target_path = "tokenizers/punkt_tab"
    strict_local = _to_bool(os.getenv("LETTA_NLTK_STRICT_LOCAL", "true"))

    try:
        timeout_seconds = float(os.getenv("LETTA_NLTK_DOWNLOAD_TIMEOUT_SECONDS", "5"))
    except ValueError:
        timeout_seconds = 5.0

    original_download = nltk.download

    def patched_download(info_or_id, *args, **kwargs):
        if str(info_or_id) != target_resource:
            return original_download(info_or_id, *args, **kwargs)

        try:
            nltk.data.find(target_path)
            return True
        except LookupError:
            if strict_local:
                return False

        previous_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout_seconds)
        try:
            return bool(original_download(info_or_id, *args, **kwargs))
        except Exception:
            return False
        finally:
            socket.setdefaulttimeout(previous_timeout)

    nltk.download = patched_download


_patch_nltk_download()
