#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
DATA_DIR_DEFAULT="/var/lib/aguai/data"
DB_PATH_DEFAULT="/app/data/stocks.db"

NO_RESTART=0
for arg in "$@"; do
  case "$arg" in
    --no-restart)
      NO_RESTART=1
      ;;
  esac
done

echo "[setup] root: ${ROOT_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[setup] .env not found, creating ${ENV_FILE}"
  touch "${ENV_FILE}"
fi

set_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    # GNU sed (Linux) in-place replace
    sed -i "s|^${key}=.*|${key}=${value}|g" "${ENV_FILE}"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}

get_env() {
  local key="$1"
  local value
  value="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n 1 | cut -d= -f2- || true)"
  echo "${value}"
}

gen_jwt() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  elif command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
  else
    date +%s%N
  fi
}

DATA_DIR="$(get_env DATA_DIR)"
if [[ -z "${DATA_DIR}" ]]; then
  DATA_DIR="${DATA_DIR_DEFAULT}"
  set_env DATA_DIR "${DATA_DIR}"
fi

DB_PATH="$(get_env DB_PATH)"
if [[ -z "${DB_PATH}" ]]; then
  DB_PATH="${DB_PATH_DEFAULT}"
  set_env DB_PATH "${DB_PATH}"
fi

JWT_SECRET="$(get_env JWT_SECRET_KEY)"
if [[ -z "${JWT_SECRET}" ]]; then
  JWT_SECRET="$(gen_jwt)"
  set_env JWT_SECRET_KEY "${JWT_SECRET}"
  echo "[setup] JWT_SECRET_KEY generated"
else
  echo "[setup] JWT_SECRET_KEY already set"
fi

echo "[setup] DATA_DIR=${DATA_DIR}"
echo "[setup] DB_PATH=${DB_PATH}"

mkdir -p "${DATA_DIR}"

if [[ -d "${ROOT_DIR}/data" ]]; then
  echo "[setup] syncing ./data -> ${DATA_DIR}"
  cp -a "${ROOT_DIR}/data/." "${DATA_DIR}/" || true
fi

echo "[setup] done"

if [[ "${NO_RESTART}" -eq 0 ]]; then
  if command -v docker >/dev/null 2>&1; then
    echo "[setup] rebuilding containers"
    docker compose up -d --build
  else
    echo "[setup] docker not found, skip restart"
  fi
else
  echo "[setup] skipped restart (--no-restart)"
fi
