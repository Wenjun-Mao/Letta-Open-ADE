#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

ENV_FILE="${1:-.env3}"
TS="$(date '+%Y%m%d_%H%M%S')"
OUT_ROOT="${PROJECT_ROOT}/diagnostics"
OUT_DIR="${OUT_ROOT}/letta_diag_${TS}"
MAIN_LOG="${OUT_DIR}/collector.log"

mkdir -p "${OUT_DIR}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "${MAIN_LOG}"
}

redact_stream() {
  sed -E \
    -e 's/(OPENAI_API_KEY=).*/\1***REDACTED***/' \
    -e 's/(ARK_API_KEY=).*/\1***REDACTED***/' \
    -e 's/(OPENAI_API_KEY:).*/\1 ***REDACTED***/' \
    -e 's/(ARK_API_KEY:).*/\1 ***REDACTED***/'
}

run_cmd() {
  local name="$1"
  shift
  local cmd="$*"
  local outfile="${OUT_DIR}/${name}.txt"

  log "RUN (${name}): ${cmd}"
  if bash -lc "${cmd}" >"${outfile}" 2>&1; then
    log "OK  (${name}) -> ${outfile}"
  else
    local rc=$?
    log "FAIL(${name}) exit=${rc} -> ${outfile}"
  fi
}

detect_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return
  fi

  log "ERROR: neither 'docker compose' nor 'docker-compose' is available"
  exit 1
}

COMPOSE_CMD="$(detect_compose_cmd)"

log "Project root: ${PROJECT_ROOT}"
log "Output dir: ${OUT_DIR}"
log "Compose command: ${COMPOSE_CMD}"
log "Env file hint: ${ENV_FILE}"

run_cmd "host_os" "uname -a; date; whoami; uptime"
run_cmd "host_release" "lsb_release -a 2>/dev/null || cat /etc/os-release"
run_cmd "docker_version" "docker version"
run_cmd "docker_info" "docker info"
run_cmd "docker_ps_all" "docker ps -a --no-trunc"
run_cmd "docker_networks" "docker network ls"
run_cmd "compose_version" "${COMPOSE_CMD} version"
run_cmd "compose_ps" "cd '${PROJECT_ROOT}' && ${COMPOSE_CMD} ps -a"

if [[ -f "${PROJECT_ROOT}/${ENV_FILE}" ]]; then
  log "Writing redacted env snapshot from ${ENV_FILE}"
  redact_stream <"${PROJECT_ROOT}/${ENV_FILE}" >"${OUT_DIR}/env_redacted.txt"
else
  log "WARN: env file not found at ${PROJECT_ROOT}/${ENV_FILE}"
fi

run_cmd "compose_config_redacted" "cd '${PROJECT_ROOT}' && ${COMPOSE_CMD} --env-file '${ENV_FILE}' config | sed -E 's/(OPENAI_API_KEY:).*/\\1 ***REDACTED***/; s/(ARK_API_KEY:).*/\\1 ***REDACTED***/'"

mapfile -t SERVICES < <(cd "${PROJECT_ROOT}" && ${COMPOSE_CMD} --env-file "${ENV_FILE}" config --services 2>/dev/null || true)
if [[ ${#SERVICES[@]} -eq 0 ]]; then
  SERVICES=(letta_server letta_db redis dev_ui)
fi

log "Services discovered: ${SERVICES[*]}"

for svc in "${SERVICES[@]}"; do
  run_cmd "compose_logs_${svc}" "cd '${PROJECT_ROOT}' && ${COMPOSE_CMD} logs --no-color --timestamps --tail=500 '${svc}'"

  cid="$(cd "${PROJECT_ROOT}" && ${COMPOSE_CMD} ps -q "${svc}" 2>/dev/null || true)"
  if [[ -n "${cid}" ]]; then
    run_cmd "inspect_${svc}_state" "docker inspect --format '{{json .State}}' '${cid}'"
    run_cmd "inspect_${svc}_healthcheck" "docker inspect --format '{{json .Config.Healthcheck}}' '${cid}'"
  fi
done

LETTA_CID="$(cd "${PROJECT_ROOT}" && ${COMPOSE_CMD} ps -q letta_server 2>/dev/null || true)"
if [[ -n "${LETTA_CID}" ]]; then
  run_cmd "probe_from_container_openapi" "docker exec '${LETTA_CID}' python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8283/openapi.json', timeout=5).read(); print('openapi_ok')\""
  run_cmd "letta_server_env_selected" "docker exec '${LETTA_CID}' /bin/sh -lc \"env | grep -E '^(OPENAI_API_BASE|OPENAI_BASE_URL|LMSTUDIO_BASE_URL|LETTA_DEFAULT_LLM_HANDLE|LETTA_DEFAULT_EMBEDDING_HANDLE|LETTA_MODEL_HANDLE|LETTA_REDIS_HOST|LETTA_REDIS_PORT|LETTA_DB_HOST|LETTA_PG_PORT|LETTA_API_PORT)='\""
fi

run_cmd "probe_host_openapi" "python3 -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8283/openapi.json', timeout=5).read(); print('host_openapi_ok')\""
run_cmd "probe_dns_ark" "getent hosts ark.cn-beijing.volces.com || true"
run_cmd "probe_https_ark" "python3 -c \"import os, urllib.request; url=os.getenv('OPENAI_API_BASE','https://ark.cn-beijing.volces.com/api/v3') + '/models'; print('probing', url); urllib.request.urlopen(url, timeout=8).read(1); print('https_reachable')\""

ARCHIVE="${OUT_DIR}.tar.gz"
run_cmd "archive_listing" "cd '${OUT_ROOT}' && ls -lah '$(basename "${OUT_DIR}")'"
tar -czf "${ARCHIVE}" -C "${OUT_ROOT}" "$(basename "${OUT_DIR}")"

log "Diagnostics complete"
log "Directory: ${OUT_DIR}"
log "Archive: ${ARCHIVE}"
log "Share the .tar.gz file for analysis"
