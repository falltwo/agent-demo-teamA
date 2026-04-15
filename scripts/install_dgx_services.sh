#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_USER="${SERVICE_USER:-$(id -un)}"
USER_HOME="${USER_HOME:-$HOME}"
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/.env}"
UV_ENV_FILE="${UV_ENV_FILE:-${USER_HOME}/.local/bin/env}"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-4173}"
START_NOW="${START_NOW:-1}"

API_TEMPLATE="${PROJECT_DIR}/deploy/systemd/contract-agent-api.service.template"
WEB_TEMPLATE="${PROJECT_DIR}/deploy/systemd/contract-agent-web.service.template"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

if [[ ! -f "${UV_ENV_FILE}" ]]; then
  echo "Missing uv env file: ${UV_ENV_FILE}" >&2
  exit 1
fi

render_unit() {
  local src="$1"
  local dst="$2"
  sed \
    -e "s|__SERVICE_USER__|${SERVICE_USER}|g" \
    -e "s|__PROJECT_DIR__|${PROJECT_DIR}|g" \
    -e "s|__WEB_DIR__|${PROJECT_DIR}/web|g" \
    -e "s|__USER_HOME__|${USER_HOME}|g" \
    -e "s|__ENV_FILE__|${ENV_FILE}|g" \
    -e "s|__UV_ENV_FILE__|${UV_ENV_FILE}|g" \
    -e "s|__API_PORT__|${API_PORT}|g" \
    -e "s|__WEB_PORT__|${WEB_PORT}|g" \
    "$src" > "$dst"
}

tmp_api="$(mktemp)"
tmp_web="$(mktemp)"
trap 'rm -f "$tmp_api" "$tmp_web"' EXIT

render_unit "${API_TEMPLATE}" "${tmp_api}"
render_unit "${WEB_TEMPLATE}" "${tmp_web}"

sudo -n install -m 644 "${tmp_api}" /etc/systemd/system/contract-agent-api.service
sudo -n install -m 644 "${tmp_web}" /etc/systemd/system/contract-agent-web.service
sudo -n systemctl daemon-reload
sudo -n systemctl enable contract-agent-api.service contract-agent-web.service

if [[ "${START_NOW}" == "1" ]]; then
  sudo -n systemctl restart contract-agent-api.service contract-agent-web.service
fi

echo "Installed:"
echo "  - contract-agent-api.service"
echo "  - contract-agent-web.service"
