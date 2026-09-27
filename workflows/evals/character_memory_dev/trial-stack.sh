#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TRIAL="$ROOT/workflows/evals/character_memory_dev"
ACTION="${1:-}"
ENV_FILE="${ADE_TRIAL_ENV_FILE:-}"

if [[ -z "$ENV_FILE" || ! -f "$ENV_FILE" ]]; then
  echo "Set ADE_TRIAL_ENV_FILE to the existing local provider/stack .env file." >&2
  exit 2
fi
if [[ "$ACTION" != "start" && "$ACTION" != "stop" && "$ACTION" != "status" ]]; then
  echo "Usage: ADE_TRIAL_ENV_FILE=/absolute/path/.env $0 start|stop|status" >&2
  exit 2
fi

export ADE_ENV_FILE="$ENV_FILE"
export ADE_API_PORT=18001
export ADE_WEB_PORT=13001
export ADE_API_BIND_HOST=127.0.0.1
export ADE_WEB_BIND_HOST=127.0.0.1
export ADE_SOURCE_REVISION="$(git -C "$ROOT" rev-parse HEAD)"
export ADE_SOURCE_FINGERPRINT="$(python3 "$ROOT/scripts/source_fingerprint.py" --root "$ROOT")"
if [[ -n "$(git -C "$ROOT" status --porcelain)" ]]; then
  export ADE_SOURCE_DIRTY=true
else
  export ADE_SOURCE_DIRTY=false
fi

compose=(docker compose --env-file "$ENV_FILE" -f "$ROOT/compose.yaml" -f "$TRIAL/compose.trial.yaml" -p ade-history-trial)
cd "$ROOT"
case "$ACTION" in
  start)
    mkdir -p "$TRIAL/.trial"
    LOCAL_SOURCES="${ADE_TRIAL_QWEN_SOURCES_FILE:-$(dirname "$ENV_FILE")/config/model-router/sources.local.json}"
    LOCAL_MANIFEST="${ADE_TRIAL_QWEN_MANIFEST_FILE:-$(dirname "$ENV_FILE")/config/model-router/deployment-manifest.json}"
    if [[ ! -f "$LOCAL_SOURCES" ]]; then
      echo "Trial requires the configured Qwen sources file: $LOCAL_SOURCES" >&2
      exit 2
    fi
    if [[ ! -f "$LOCAL_MANIFEST" ]]; then
      echo "Trial requires the tested Qwen deployment manifest: $LOCAL_MANIFEST" >&2
      exit 2
    fi
    mkdir -p "$TRIAL/.trial/router-config"
    cp -R "$ROOT/config/." "$TRIAL/.trial/router-config/"
    python3 - "$ROOT/config/model-router/sources.json" "$LOCAL_SOURCES" "$ROOT/config/model-router/deployment-manifest.json" "$LOCAL_MANIFEST" "$TRIAL/.trial/router-config/model-router" <<'PY'
import json
import sys
from pathlib import Path

checked_in, configured, candidate_manifest, tested_manifest, output_dir = map(Path, sys.argv[1:])
deepseek = next(item for item in json.loads(checked_in.read_text()) if item["id"] == "deepseek")
qwen = next(item for item in json.loads(configured.read_text()) if item["id"] == "dgx_embedding_sidecar")
sources_output = output_dir / "sources.trial.json"
sources_output.write_text(json.dumps([deepseek, qwen], indent=2) + "\n")
sources_output.chmod(0o600)
candidate = json.loads(candidate_manifest.read_text())
tested = json.loads(tested_manifest.read_text())
tested_qwen = next(item for item in tested["deployments"] if item["id"] == "dgx-qwen3-embedding-0_6b")
candidate["deployments"] = [
    tested_qwen if item["id"] == "dgx-qwen3-embedding-0_6b" else item
    for item in candidate["deployments"]
]
manifest_output = output_dir / "deployment-manifest.json"
manifest_output.write_text(json.dumps(candidate, indent=2) + "\n")
manifest_output.chmod(0o600)
PY
    if [[ ! -d "$TRIAL/.trial/content" ]]; then
      cp -R "$ROOT/content" "$TRIAL/.trial/content"
    fi
    "${compose[@]}" up -d --build
    ;;
  stop)
    "${compose[@]}" stop
    ;;
  status)
    "${compose[@]}" ps
    ;;
esac
