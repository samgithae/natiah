#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/natiah}"
REPO_URL="${REPO_URL:-}"
BRANCH="${BRANCH:-main}"
ENV_FILE="${ENV_FILE:-${APP_DIR}/docker/.env.prod}"

if [[ -z "${REPO_URL}" ]]; then
  echo "Set REPO_URL, e.g.:"
  echo "  REPO_URL=https://github.com/YOUR_ORG/Natiah.git $0"
  exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo REPO_URL=... $0"
  exit 1
fi

mkdir -p "${APP_DIR}"

if [[ ! -d "${APP_DIR}/.git" ]]; then
  git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
else
  cd "${APP_DIR}"
  git fetch --all --prune
  git checkout "${BRANCH}"
  git pull --ff-only
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}"
  echo "Create it from: ${APP_DIR}/docker/.env.prod.example"
  exit 1
fi

cd "${APP_DIR}"

docker compose \
  --env-file "${ENV_FILE}" \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.prod.yml \
  up -d --build

docker compose \
  --env-file "${ENV_FILE}" \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.prod.yml \
  ps
