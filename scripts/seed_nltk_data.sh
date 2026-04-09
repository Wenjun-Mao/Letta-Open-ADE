#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${ROOT_DIR}/data/nltk_data"
IMAGE="${LETTA_IMAGE:-letta/letta:latest}"

mkdir -p "${TARGET_DIR}"

echo "[seed_nltk_data] target directory: ${TARGET_DIR}"
echo "[seed_nltk_data] image: ${IMAGE}"

docker run --rm \
  -v "${TARGET_DIR}:/root/nltk_data" \
  "${IMAGE}" \
  /app/.venv/bin/python - <<'PY'
import nltk
from nltk.data import find

try:
    find("tokenizers/punkt_tab")
    print("[seed_nltk_data] punkt_tab already present")
except LookupError:
    ok = nltk.download("punkt_tab", quiet=True)
    print(f"[seed_nltk_data] download_ok={ok}")
    if not ok:
        raise SystemExit("[seed_nltk_data] failed to download punkt_tab")
    print("[seed_nltk_data] punkt_tab downloaded")
PY

echo "[seed_nltk_data] done"
