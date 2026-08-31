#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

ENV_FILE="${1:-.env}"
TS="$(date '+%Y%m%d_%H%M%S')"
OUT_ROOT="${PROJECT_ROOT}/diagnostics"
OUT_DIR="${OUT_ROOT}/ade_diag_${TS}"
MAIN_LOG="${OUT_DIR}/collector.log"

mkdir -p "${OUT_DIR}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "${MAIN_LOG}"
}

redact_stream() {
  sed -E \
    -e 's#(://)[^/@[:space:]]+:[^/@[:space:]]+@#\1***:***@#g' \
    -e 's/([Aa]uthorization:[[:space:]]*[Bb]earer[[:space:]]+)[^[:space:]]+/\1***REDACTED***/g' \
    -e 's/^([A-Za-z_][A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|COOKIE|AUTH)[A-Za-z0-9_]*[=:][[:space:]]*).*/\1***REDACTED***/I' \
    -e "s/([\"'][A-Za-z_][A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|COOKIE|AUTH)[A-Za-z0-9_]*[\"']?[[:space:]]*:[[:space:]]*).*/\1***REDACTED***/I"
}

run_cmd() {
  local name="$1"
  shift
  local cmd="$*"
  local outfile="${OUT_DIR}/${name}.txt"

  log "RUN (${name}): ${cmd}"
  if bash -lc "${cmd}" 2>&1 | redact_stream >"${outfile}"; then
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

read_compose_project_name() {
  local env_path="${PROJECT_ROOT}/${ENV_FILE}"
  if [[ ! -f "${env_path}" ]]; then
    return
  fi

  grep -E '^[[:space:]]*COMPOSE_PROJECT_NAME=' "${env_path}" \
    | tail -n1 \
    | cut -d'=' -f2- \
    | tr -d '"' \
    | tr -d '\r' \
    | xargs
}

read_env_value() {
  local name="$1"
  local env_path="${PROJECT_ROOT}/${ENV_FILE}"
  if [[ ! -f "${env_path}" ]]; then
    return
  fi

  grep -E "^[[:space:]]*${name}=" "${env_path}" \
    | tail -n1 \
    | cut -d'=' -f2- \
    | tr -d '"' \
    | tr -d '\r' \
    | xargs
}

resolve_host_port() {
  local service="$1"
  local container_port="$2"
  local env_name="$3"
  local fallback="$4"
  local endpoint=""
  local port=""

  endpoint="$(cd "${PROJECT_ROOT}" && ${COMPOSE_CMD} --env-file "${ENV_FILE}" port "${service}" "${container_port}" 2>/dev/null | tail -n1 || true)"
  port="${endpoint##*:}"
  if [[ "${port}" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "${port}"
    return
  fi

  port="$(read_env_value "${env_name}" || true)"
  if [[ "${port}" =~ ^[0-9]+$ ]]; then
    printf '%s\n' "${port}"
  else
    printf '%s\n' "${fallback}"
  fi
}

get_service_cid() {
  local svc="$1"
  local cid=""

  cid="$(cd "${PROJECT_ROOT}" && ${COMPOSE_CMD} --env-file "${ENV_FILE}" ps -q "${svc}" 2>/dev/null || true)"
  if [[ -n "${cid}" ]]; then
    printf '%s\n' "${cid}"
    return
  fi

  if [[ -n "${COMPOSE_PROJECT_NAME_ENV}" ]]; then
    cid="$(docker ps -aq \
      --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME_ENV}" \
      --filter "label=com.docker.compose.service=${svc}" \
      | head -n1)"
  fi

  printf '%s\n' "${cid}"
}

COMPOSE_PROJECT_NAME_ENV="$(read_compose_project_name || true)"

log "Project root: ${PROJECT_ROOT}"
log "Output dir: ${OUT_DIR}"
log "Compose command: ${COMPOSE_CMD}"
log "Env file hint: ${ENV_FILE}"
if [[ -n "${COMPOSE_PROJECT_NAME_ENV}" ]]; then
  log "Compose project from env: ${COMPOSE_PROJECT_NAME_ENV}"
else
  log "Compose project from env: <not set>"
fi

run_cmd "host_os" "uname -a; date; whoami; uptime"
run_cmd "host_release" "if command -v sw_vers >/dev/null 2>&1; then sw_vers; elif command -v lsb_release >/dev/null 2>&1; then lsb_release -a; elif [[ -r /etc/os-release ]]; then cat /etc/os-release; else uname -a; fi"
run_cmd "docker_version" "docker version"
run_cmd "docker_info" "docker info"
run_cmd "docker_ps_all" "docker ps -a --no-trunc"
run_cmd "docker_networks" "docker network ls"
run_cmd "host_proxy_env" "env | grep -iE '^(http|https|no)_proxy=' || true"
run_cmd "compose_version" "${COMPOSE_CMD} version"
run_cmd "compose_ps" "cd '${PROJECT_ROOT}' && ${COMPOSE_CMD} --env-file '${ENV_FILE}' ps -a"

if [[ -f "${PROJECT_ROOT}/${ENV_FILE}" ]]; then
  log "Writing allowlisted environment summary from ${ENV_FILE}"
  grep -E '^(COMPOSE_PROJECT_NAME|LETTA_SERVER_IMAGE|LETTA_PG_|LETTA_REDIS_|LETTA_API_PORT|LETTA_DEBUG|ADE_WEB_BIND_HOST|ADE_WEB_PORT|ADE_API_BIND_HOST|ADE_API_PORT|MODEL_ROUTER_CACHE_TTL_SECONDS|MODEL_ROUTER_DISCOVERY_TIMEOUT_SECONDS|MODEL_ROUTER_REQUEST_TIMEOUT_SECONDS|MODEL_ROUTER_SOURCES_FILE|MODEL_ROUTER_MODEL_PROFILES_FILE|ADE_API_AUTH_ENABLED|ADE_API_MODEL_ROUTER_BASE_URL|ADE_API_RUNTIME_DATA_DIR|ADE_API_PERSONA_DB_PATH|ADE_API_PERSONA_SEED_JSONL_PATH|ADE_API_COMMENT_LAB_|ADE_API_LABEL_LAB_|ADE_API_AGENT_STUDIO_)=' \
    "${PROJECT_ROOT}/${ENV_FILE}" | redact_stream >"${OUT_DIR}/env_safe_summary.txt" || true
else
  log "WARN: env file not found at ${PROJECT_ROOT}/${ENV_FILE}"
fi

run_cmd "compose_services" "cd '${PROJECT_ROOT}' && ${COMPOSE_CMD} --env-file '${ENV_FILE}' config --services"
run_cmd "compose_images" "cd '${PROJECT_ROOT}' && ${COMPOSE_CMD} --env-file '${ENV_FILE}' config --images"

SERVICES=()
while IFS= read -r service; do
  [[ -n "${service}" ]] && SERVICES+=("${service}")
done < <(cd "${PROJECT_ROOT}" && ${COMPOSE_CMD} --env-file "${ENV_FILE}" config --services 2>/dev/null || true)
if [[ ${#SERVICES[@]} -eq 0 ]]; then
  SERVICES=(postgres redis model-router letta ade-api ade-web)
fi

log "Services discovered: ${SERVICES[*]}"

for svc in "${SERVICES[@]}"; do
  run_cmd "compose_logs_${svc}" "cd '${PROJECT_ROOT}' && ${COMPOSE_CMD} --env-file '${ENV_FILE}' logs --no-color --timestamps --tail=500 '${svc}'"

  cid="$(get_service_cid "${svc}")"
  if [[ -n "${cid}" ]]; then
    run_cmd "inspect_${svc}_state" "docker inspect --format '{{json .State}}' '${cid}'"
    run_cmd "inspect_${svc}_healthcheck" "docker inspect --format '{{json .Config.Healthcheck}}' '${cid}'"
    run_cmd "docker_logs_${svc}" "docker logs --timestamps --tail=500 '${cid}'"
  else
    log "WARN: unable to resolve container ID for service '${svc}'"
  fi
done

LETTA_CID="$(get_service_cid letta)"
if [[ -n "${LETTA_CID}" ]]; then
  run_cmd "probe_letta_from_container" "docker exec '${LETTA_CID}' python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8283/v1/health/', timeout=5).read(); print('letta_health_ok')\""
  run_cmd "letta_env_selected" "docker exec '${LETTA_CID}' /bin/sh -lc \"env | grep -E '^(OPENAI_API_BASE|OPENAI_BASE_URL|LETTA_DEFAULT_EMBEDDING_HANDLE|LETTA_MODEL_HANDLE|LETTA_REDIS_HOST|LETTA_REDIS_PORT|LETTA_DB_HOST|LETTA_PG_PORT|LETTA_API_PORT)='\""
  run_cmd "letta_processes" "docker exec '${LETTA_CID}' /bin/sh -lc 'ps -ef'"
  run_cmd "letta_listen_ports" "docker exec '${LETTA_CID}' /bin/sh -lc 'ss -ltnp 2>/dev/null || netstat -ltnp 2>/dev/null || true'"
fi

ADE_API_CID="$(get_service_cid ade-api)"
if [[ -n "${ADE_API_CID}" ]]; then
  run_cmd "ade_api_env_selected" "docker exec '${ADE_API_CID}' /bin/sh -lc \"env | grep -E '^(ADE_API_MODEL_ROUTER_BASE_URL|ADE_API_COMMENT_LAB_|ADE_API_LABEL_LAB_|ADE_API_AGENT_STUDIO_|LETTA_BASE_URL)=' || true\""
fi

MODEL_ROUTER_CID="$(get_service_cid model-router)"
if [[ -n "${MODEL_ROUTER_CID}" ]]; then
  run_cmd "model_router_env_selected" "docker exec '${MODEL_ROUTER_CID}' /bin/sh -lc \"env | grep -E '^(MODEL_ROUTER_SOURCES_FILE|MODEL_ROUTER_MODEL_PROFILES_FILE|MODEL_ROUTER_CACHE_TTL_SECONDS|MODEL_ROUTER_DISCOVERY_TIMEOUT_SECONDS|MODEL_ROUTER_REQUEST_TIMEOUT_SECONDS)='\""
  run_cmd "model_router_sources_file" "docker exec '${MODEL_ROUTER_CID}' /bin/sh -lc \"python -m json.tool \\\"\${MODEL_ROUTER_SOURCES_FILE:-config/model-router/sources.json}\\\"\""
  run_cmd "model_router_model_profiles_file" "docker exec '${MODEL_ROUTER_CID}' /bin/sh -lc \"python -m json.tool \\\"\${MODEL_ROUTER_MODEL_PROFILES_FILE:-config/model-router/model-profiles.json}\\\"\""
  run_cmd "probe_model_catalog_from_model_router" "docker exec '${MODEL_ROUTER_CID}' python -c \"import json, os, urllib.request; request=urllib.request.Request('http://127.0.0.1:8010/v1/router/model-catalog', headers={'Authorization': 'Bearer ' + os.environ['MODEL_ROUTER_API_KEY']}); payload=json.load(urllib.request.urlopen(request, timeout=10)); print(json.dumps({'generated_at': payload.get('generated_at'), 'source_count': len(payload.get('sources', [])), 'model_count': len(payload.get('items', []))}, indent=2))\""
fi

ADE_WEB_HOST_PORT="$(resolve_host_port ade-web 3000 ADE_WEB_PORT 3000)"
ADE_API_HOST_PORT="$(resolve_host_port ade-api 8000 ADE_API_PORT 8000)"
log "Resolved host ports: ade-web=${ADE_WEB_HOST_PORT}, ade-api=${ADE_API_HOST_PORT}"

run_cmd "probe_ade_web" "curl -fsS --max-time 10 -o /dev/null -w 'status=%{http_code}\\n' 'http://127.0.0.1:${ADE_WEB_HOST_PORT}/'"
run_cmd "probe_ade_api_health" "python3 -c \"import json,urllib.request; opener=urllib.request.build_opener(urllib.request.ProxyHandler({})); resp=opener.open('http://127.0.0.1:${ADE_API_HOST_PORT}/api/v2/health', timeout=10); print(json.dumps(json.load(resp), indent=2))\""
run_cmd "probe_ade_api_openapi" "curl -fsS -D '${OUT_DIR}/probe_ade_api_openapi_headers.txt' -o '${OUT_DIR}/probe_ade_api_openapi_body.json' 'http://127.0.0.1:${ADE_API_HOST_PORT}/openapi.json'"
run_cmd "probe_dns_ark" "python3 -c \"import socket; print(socket.getaddrinfo('ark.cn-beijing.volces.com', 443)[0][4][0])\""
run_cmd "model_catalog_report_summary" "python3 -c \"import json, pathlib; path=pathlib.Path('content/model-catalog/ark_chat_probe_report.json'); payload=json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {'missing': True}; summary={'path': str(path), 'source_id': payload.get('source_id'), 'checked_at': payload.get('checked_at'), 'probe_mode': payload.get('probe_mode'), 'raw_model_count': payload.get('raw_model_count'), 'usable_models': payload.get('usable_models', [])}; print(json.dumps(summary, indent=2, ensure_ascii=False))\""

ARCHIVE="${OUT_DIR}.tar.gz"
run_cmd "archive_listing" "cd '${OUT_ROOT}' && ls -lah '$(basename "${OUT_DIR}")'"
tar -czf "${ARCHIVE}" -C "${OUT_ROOT}" "$(basename "${OUT_DIR}")"

log "Diagnostics complete"
log "Directory: ${OUT_DIR}"
log "Archive: ${ARCHIVE}"
log "Review the archive contents before sharing the .tar.gz file for analysis"
